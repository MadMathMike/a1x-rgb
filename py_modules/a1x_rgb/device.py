"""LED device abstraction and detection."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod

from . import oxp_hid_v2 as v2
from .color import hsb_to_rgb
from .modes import choice, slider

DMI_PRODUCT = "/sys/class/dmi/id/product_name"


class LedDevice(ABC):
    """A device whose LEDs can be set from a settings dict."""

    name: str
    path: str

    @abstractmethod
    def description(self) -> dict:
        """Modes and controls (see modes.py)."""

    @abstractmethod
    def commands(self, settings: dict) -> list[bytes]:
        """Packets to send for normalized settings."""

    @abstractmethod
    def apply(self, settings: dict) -> None:
        """Send settings to the device (blocking). Raises OSError on failure."""

    def info(self) -> dict:
        return {"name": self.name, "path": self.path}


# Modes HHD offers for the A1X (RGB_MODES_STICKS_AOK). Defaults match HHD's
# capabilities.yml, except the AOKZOE style default (see oxp_hid_v2.STYLES).
OXP_HID_V2_DESCRIPTION = {
    "default_mode": "solid",
    "modes": [
        {"key": "off", "label": "Off", "controls": []},
        {"key": "solid", "label": "Solid", "controls": ["hue", "saturation", "brightness"]},
        {"key": "aok", "label": "AOKZOE", "controls": ["style", "level"]},
    ],
    "controls": {
        "hue": slider("Hue", 0, 360, 5, 30, "°"),
        "saturation": slider("Saturation", 0, 100, 10, 100, "%"),
        "brightness": slider("Brightness", 0, 100, 10, 50, "%"),
        "style": choice(
            "Style", [(k, label) for k, (label, _) in v2.STYLES.items()], "aok"
        ),
        "level": choice(
            "Brightness", [("low", "Low"), ("medium", "Medium"), ("high", "High")], "medium"
        ),
    },
}


class OxpHidV2Device(LedDevice):
    """OneXPlayer / AOKZOE LED controller on the "HID v2" vendor interface."""

    def __init__(self, path: str, name: str = "OneXPlayer/AOKZOE LEDs"):
        self.path = path
        self.name = name
        self._next_write = 0.0

    def description(self) -> dict:
        return OXP_HID_V2_DESCRIPTION

    def commands(self, settings: dict) -> list[bytes]:
        mode = settings["mode"]
        if mode == "off":
            return v2.sequence_off()
        if mode == "solid":
            rgb = hsb_to_rgb(settings["hue"], settings["saturation"], settings["brightness"])
            return v2.sequence_solid(*rgb)
        if mode == "aok":
            return v2.sequence_effect(settings["style"], settings["level"])
        raise ValueError(f"unknown mode: {mode!r}")

    def apply(self, settings: dict) -> None:
        packets = self.commands(settings)
        # Open per apply: the fd can't go stale across suspend or re-enumeration.
        fd = os.open(self.path, os.O_WRONLY)
        try:
            for pkt in packets:
                # Keep WRITE_DELAY between *all* writes, including across
                # back-to-back applies.
                wait = self._next_write - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                written = os.write(fd, pkt)
                self._next_write = time.monotonic() + v2.WRITE_DELAY
                if written != len(pkt):
                    raise OSError(f"short write to {self.path}: {written}/{len(pkt)}")
        finally:
            os.close(fd)


def _product_name(dmi_path: str) -> str | None:
    try:
        with open(dmi_path) as f:
            return f.read().strip() or None
    except OSError:
        return None


def detect_device(
    sysfs_root: str | None = None,
    dev_root: str = "/dev",
    dmi_path: str = DMI_PRODUCT,
) -> LedDevice | None:
    """Return the first supported LED device found, or None."""
    kwargs = {"dev_root": dev_root}
    if sysfs_root is not None:
        kwargs["sysfs_root"] = sysfs_root
    path = v2.find_device(**kwargs)
    if path:
        product = _product_name(dmi_path)
        return OxpHidV2Device(path, product or "OneXPlayer/AOKZOE LEDs")
    return None
