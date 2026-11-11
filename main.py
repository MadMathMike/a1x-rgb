import decky

from a1x_rgb import __version__


class Plugin:
    # Called from the frontend. Device detection and settings arrive in
    # milestone 3; for now this only proves the frontend <-> backend wiring.
    async def get_state(self) -> dict:
        return {"version": __version__, "device": None}

    async def _main(self):
        decky.logger.info(f"A1X RGB {__version__} loaded")

    async def _unload(self):
        # LEDs keep their last state; nothing to clean up.
        decky.logger.info("A1X RGB unloaded")

    async def _uninstall(self):
        decky.logger.info("A1X RGB uninstalled")
