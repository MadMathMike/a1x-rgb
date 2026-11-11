import asyncio
import json
import logging
import os
import tempfile
import threading
import unittest

import _util  # noqa: F401  (sets up sys.path)

from a1x_rgb.controller import NOT_FOUND, Applier, Controller
from a1x_rgb.device import OxpHidV2Device
from a1x_rgb.modes import defaults


class FakeDevice(OxpHidV2Device):
    """Records applied settings instead of writing to hardware."""

    def __init__(self, path="/dev/hidraw0", fail=0):
        super().__init__(path, "Fake A1X")
        self.applied = []
        self.fail = fail

    def apply(self, settings):
        if self.fail:
            self.fail -= 1
            raise OSError("write failed")
        self.applied.append(dict(settings))


class ApplierTest(unittest.TestCase):
    def test_latest_wins_while_busy(self):
        calls = []
        release = threading.Event()
        started = threading.Event()

        def fn(s):
            calls.append(s["n"])
            if s["n"] == 1:
                started.set()
                release.wait(2)

        async def run():
            app = Applier(fn)
            first = asyncio.create_task(app.submit({"n": 1}))
            await asyncio.to_thread(started.wait, 2)
            # Submitted while #1 is still being applied:
            rest = [asyncio.create_task(app.submit({"n": n})) for n in (2, 3, 4)]
            await asyncio.sleep(0)
            release.set()
            return await asyncio.gather(first, *rest)

        results = asyncio.run(run())
        self.assertEqual(calls, [1, 4])
        self.assertEqual(results, [None] * 4)

    def test_errors_are_returned(self):
        def fn(s):
            raise OSError("boom")

        async def run():
            return await Applier(fn).submit({})

        err = asyncio.run(run())
        self.assertIsInstance(err, OSError)


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "settings.json")
        self.dev = FakeDevice()

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, detect=None):
        quiet = logging.getLogger("a1x_rgb.test")
        quiet.disabled = True  # expected errors would clutter test output
        c = Controller(self.path, detect=detect or (lambda: self.dev), logger=quiet)
        c.start()
        return c

    def test_start_never_writes(self):
        with open(self.path, "w") as f:
            json.dump({"mode": "off"}, f)
        c = self.make()
        self.assertEqual(self.dev.applied, [])
        self.assertEqual(c.state()["settings"]["mode"], "off")

    def test_state(self):
        st = self.make().state()
        self.assertEqual(st["device"], {"name": "Fake A1X", "path": "/dev/hidraw0"})
        self.assertEqual(st["settings"], defaults(st["description"]))
        self.assertIn("version", st)
        self.assertIn("python", st)
        json.dumps(st)  # must be serialisable for Decky

    def test_state_without_device(self):
        st = self.make(detect=lambda: None).state()
        self.assertIsNone(st["device"])
        self.assertIsNone(st["settings"])

    def test_device_found_later(self):
        found = []
        c = self.make(detect=lambda: found[0] if found else None)
        self.assertIsNone(c.state()["device"])
        found.append(self.dev)
        self.assertIsNotNone(c.state()["device"])

    def test_set_settings_partial_update_saves_and_applies(self):
        c = self.make()
        r = asyncio.run(c.set_settings({"mode": "aok", "style": "neon"}))
        self.assertTrue(r["ok"])
        self.assertEqual(r["settings"]["style"], "neon")
        self.assertEqual(r["settings"]["hue"], 30)  # untouched default kept
        self.assertEqual(self.dev.applied, [r["settings"]])
        with open(self.path) as f:
            self.assertEqual(json.load(f), r["settings"])

        r2 = asyncio.run(c.set_settings({"level": "low"}))
        self.assertEqual(r2["settings"]["style"], "neon")  # merged with saved
        self.assertEqual(r2["settings"]["level"], "low")

    def test_set_settings_invalid(self):
        c = self.make()
        for bad in ({"mode": "rainbow"}, {"hue": "x"}, ["not", "a", "dict"]):
            with self.subTest(bad=bad):
                r = asyncio.run(c.set_settings(bad))
                self.assertFalse(r["ok"])
                self.assertTrue(r["error"])
        self.assertEqual(self.dev.applied, [])
        self.assertFalse(os.path.exists(self.path))

    def test_set_settings_without_device(self):
        c = self.make(detect=lambda: None)
        r = asyncio.run(c.set_settings({"mode": "off"}))
        self.assertEqual((r["ok"], r["error"]), (False, NOT_FOUND))

    def test_write_failure_is_reported_but_settings_saved(self):
        self.dev.fail = 2  # fails, then the re-detected (same) device isn't retried
        c = self.make()
        r = asyncio.run(c.set_settings({"mode": "off"}))
        self.assertFalse(r["ok"])
        self.assertIn("write failed", r["error"])
        self.assertEqual(c.state()["settings"]["mode"], "off")

    def test_retries_when_node_moves(self):
        old = FakeDevice("/dev/hidraw0", fail=1)
        new = FakeDevice("/dev/hidraw3")
        devices = [old, new]
        c = self.make(detect=lambda: devices.pop(0) if devices else new)
        r = asyncio.run(c.set_settings({"mode": "off"}))
        self.assertTrue(r["ok"])
        self.assertEqual(c.device.path, "/dev/hidraw3")
        self.assertEqual(len(new.applied), 1)


if __name__ == "__main__":
    unittest.main()
