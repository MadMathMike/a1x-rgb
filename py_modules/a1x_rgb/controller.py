"""Backend logic behind the Decky Plugin class (kept out of main.py so it can
be tested without Decky)."""

from __future__ import annotations

import asyncio
import logging
import platform
from typing import Callable

from . import __version__
from . import settings as store
from .device import LedDevice, detect_device
from .modes import normalize

NOT_FOUND = "AOKZOE A1X LED controller not found"


class Applier:
    """Runs a blocking apply function one call at a time, latest wins.

    While a call is running, further submissions replace each other; only the
    newest is applied next. Every submitter's await resolves when its
    settings (or newer settings that replaced them) have been applied, with
    None on success or the exception that occurred.
    """

    def __init__(self, fn: Callable[[dict], None]):
        self._fn = fn
        self._pending: dict | None = None
        self._waiters: list[asyncio.Future] = []
        self._task: asyncio.Task | None = None

    async def submit(self, settings: dict) -> Exception | None:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending = settings
        self._waiters.append(fut)
        if self._task is None or self._task.done():
            self._task = loop.create_task(self._run())
        return await fut

    async def _run(self) -> None:
        while self._pending is not None:
            current, self._pending = self._pending, None
            waiters, self._waiters = self._waiters, []
            err: Exception | None = None
            try:
                await asyncio.to_thread(self._fn, current)
            except Exception as e:  # reported to every waiter
                err = e
            for w in waiters:
                if not w.done():
                    w.set_result(err)


class Controller:
    def __init__(
        self,
        settings_path: str,
        detect: Callable[[], LedDevice | None] = detect_device,
        logger: logging.Logger | None = None,
    ):
        self.settings_path = settings_path
        self._detect = detect
        self.log = logger or logging.getLogger("a1x_rgb")
        self.device: LedDevice | None = None
        self.saved: dict = {}
        self.applier = Applier(self._apply)

    def start(self) -> None:
        """Load settings and look for the device. Never writes to the LEDs:
        the firmware keeps their state across suspend and reboot."""
        self.saved = store.load(self.settings_path)
        self._ensure_device()

    def _ensure_device(self) -> LedDevice | None:
        if self.device is None:
            self.device = self._detect()
            if self.device:
                self.log.info(f"Found {self.device.name} at {self.device.path}")
            else:
                self.log.info(NOT_FOUND)
        return self.device

    def state(self) -> dict:
        dev = self._ensure_device()
        return {
            "version": __version__,
            "python": platform.python_version(),
            "device": dev.info() if dev else None,
            "description": dev.description() if dev else None,
            "settings": normalize(dev.description(), self.saved) if dev else None,
        }

    async def set_settings(self, incoming: dict) -> dict:
        """Validate, save and apply. Returns {ok, error, settings}."""
        dev = self._ensure_device()
        if dev is None:
            return {"ok": False, "error": NOT_FOUND, "settings": None}
        if not isinstance(incoming, dict):
            return {"ok": False, "error": "settings must be an object", "settings": None}

        desc = dev.description()
        current = normalize(desc, self.saved)
        try:
            merged = normalize(desc, {**current, **incoming}, strict=True)
        except ValueError as e:
            return {"ok": False, "error": str(e), "settings": current}

        self.saved = merged
        try:
            store.save(self.settings_path, merged)
        except OSError as e:
            self.log.error(f"Could not save settings: {e}")

        err = await self.applier.submit(merged)
        if err is not None:
            self.log.error(f"Applying LED settings failed: {err}")
            return {"ok": False, "error": str(err), "settings": merged}
        return {"ok": True, "error": None, "settings": merged}

    def _apply(self, settings: dict) -> None:
        """Runs in a worker thread (via Applier)."""
        dev = self.device
        if dev is None:
            raise OSError(NOT_FOUND)
        try:
            dev.apply(settings)
        except OSError:
            # The hidraw node may have been renumbered; look again once.
            new = self._detect()
            if new is None or new.path == dev.path:
                raise
            self.log.info(f"Device moved to {new.path}, retrying")
            self.device = new
            new.apply(settings)
