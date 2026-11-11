from __future__ import annotations

import os

import decky

from a1x_rgb import __version__
from a1x_rgb.controller import Controller


class Plugin:
    controller: Controller | None = None

    def _ctl(self) -> Controller:
        # Created lazily so a frontend call that races _main() still works.
        if self.controller is None:
            self.controller = Controller(
                os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "settings.json"),
                logger=decky.logger,
            )
            self.controller.start()
        return self.controller

    async def get_state(self) -> dict:
        return self._ctl().state()

    async def set_settings(self, settings: dict) -> dict:
        return await self._ctl().set_settings(settings)

    async def _main(self):
        self._ctl()
        decky.logger.info(f"A1X RGB {__version__} loaded")

    async def _unload(self):
        # LEDs keep their last state; nothing to clean up.
        decky.logger.info("A1X RGB unloaded")

    async def _uninstall(self):
        decky.logger.info("A1X RGB uninstalled")
