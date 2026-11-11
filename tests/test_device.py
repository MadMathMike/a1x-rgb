import os
import tempfile
import time
import unittest
from unittest import mock

import _util  # noqa: F401  (sets up sys.path)
from test_hidraw import A1X_LED_DESC, A1X_MOUSE_DESC, uevent

from a1x_rgb import oxp_hid_v2 as v2
from a1x_rgb.color import hsb_to_rgb
from a1x_rgb.device import OxpHidV2Device, detect_device
from a1x_rgb.modes import defaults, normalize

DESC = OxpHidV2Device("/dev/null").description()


class CommandsTest(unittest.TestCase):
    def setUp(self):
        self.dev = OxpHidV2Device("/dev/null")

    def test_off(self):
        s = normalize(DESC, {"mode": "off"})
        self.assertEqual(self.dev.commands(s), v2.sequence_off())

    def test_solid(self):
        s = normalize(DESC, {"mode": "solid", "hue": 240, "saturation": 50, "brightness": 80})
        self.assertEqual(
            self.dev.commands(s), v2.sequence_solid(*hsb_to_rgb(240, 50, 80))
        )

    def test_effect(self):
        s = normalize(DESC, {"mode": "aok", "style": "sunset", "level": "high"})
        self.assertEqual(self.dev.commands(s), v2.sequence_effect("sunset", "high"))

    def test_every_style_and_level(self):
        for style in v2.STYLES:
            for level in v2.LEVELS:
                s = normalize(DESC, {"mode": "aok", "style": style, "level": level}, strict=True)
                self.assertEqual(len(self.dev.commands(s)), 2)


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "hidraw0")
        open(self.path, "wb").close()
        self.dev = OxpHidV2Device(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self) -> bytes:
        with open(self.path, "rb") as f:
            return f.read()

    def test_writes_packets_in_order(self):
        s = normalize(DESC, {"mode": "aok", "style": "aurora", "level": "low"})
        self.dev.apply(s)
        self.assertEqual(self.read(), b"".join(v2.sequence_effect("aurora", "low")))

    def test_write_delay_between_packets_and_applies(self):
        s = defaults(DESC)  # solid: 2 packets
        with mock.patch.object(v2, "WRITE_DELAY", 0.03):
            start = time.monotonic()
            self.dev.apply(s)
            self.dev.apply(s)  # back-to-back: also spaced
            elapsed = time.monotonic() - start
        # 4 packets -> at least 3 gaps
        self.assertGreaterEqual(elapsed, 0.09 - 0.005)
        # Each apply reopens the node; with a regular file that means the
        # second apply overwrites the first (a hidraw node just gets 4 writes).
        self.assertEqual(self.read(), b"".join(self.dev.commands(s)))

    def test_missing_node_raises(self):
        dev = OxpHidV2Device(os.path.join(self.tmp.name, "nope"))
        with self.assertRaises(OSError):
            dev.apply(defaults(DESC))


class DetectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "sys")
        self.dmi = os.path.join(self.tmp.name, "product_name")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name, desc):
        d = os.path.join(self.root, name, "device")
        os.makedirs(d)
        with open(os.path.join(d, "uevent"), "w") as f:
            f.write(uevent(0x1A2C, 0xB001))
        with open(os.path.join(d, "report_descriptor"), "wb") as f:
            f.write(desc)

    def test_detects_a1x(self):
        self.add("hidraw0", A1X_LED_DESC)
        self.add("hidraw2", A1X_MOUSE_DESC)
        with open(self.dmi, "w") as f:
            f.write("AOKZOE A1X\n")
        dev = detect_device(sysfs_root=self.root, dmi_path=self.dmi)
        self.assertIsNotNone(dev)
        self.assertEqual(dev.info(), {"name": "AOKZOE A1X", "path": "/dev/hidraw0"})

    def test_name_fallback_without_dmi(self):
        self.add("hidraw0", A1X_LED_DESC)
        dev = detect_device(sysfs_root=self.root, dmi_path=self.dmi)
        self.assertEqual(dev.name, "OneXPlayer/AOKZOE LEDs")

    def test_not_found(self):
        self.add("hidraw2", A1X_MOUSE_DESC)
        self.assertIsNone(detect_device(sysfs_root=self.root, dmi_path=self.dmi))


if __name__ == "__main__":
    unittest.main()
