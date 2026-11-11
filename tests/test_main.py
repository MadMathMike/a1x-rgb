"""Load main.py with a stand-in `decky` module, as Decky Loader would."""

import asyncio
import importlib.util
import logging
import os
import sys
import tempfile
import types
import unittest

from _util import ROOT


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        decky = types.ModuleType("decky")
        decky.DECKY_PLUGIN_SETTINGS_DIR = self.tmp.name
        decky.logger = logging.getLogger("decky-test")
        sys.modules["decky"] = decky

        spec = importlib.util.spec_from_file_location(
            "a1x_rgb_main", os.path.join(ROOT, "main.py")
        )
        self.main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.main)

    def tearDown(self):
        sys.modules.pop("decky", None)
        self.tmp.cleanup()

    def test_lifecycle_and_callables(self):
        async def run():
            p = self.main.Plugin()
            # A frontend call that arrives before _main() must still work.
            state = await p.get_state()
            await p._main()
            await p._unload()
            return state

        state = asyncio.run(run())
        # No A1X on the test machine (normally): device may be None.
        self.assertIn("device", state)
        self.assertIn("version", state)


if __name__ == "__main__":
    unittest.main()
