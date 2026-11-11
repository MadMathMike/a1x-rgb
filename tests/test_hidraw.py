from __future__ import annotations

import os
import tempfile
import unittest

import _util  # noqa: F401  (sets up sys.path)

from a1x_rgb import oxp_hid_v2
from a1x_rgb.hidraw import find_hidraw, parse_hid_id, top_level_usages

# Vendor collection: Usage Page 0xFF01 (3-byte item), Usage 0x01.
VENDOR_DESC = bytes.fromhex(
    "06 01 FF 09 01 A1 01 15 00 26 FF 00 75 08 95 40 09 01 81 02 09 01 91 02 C0"
)
# Keyboard: Usage Page 0x01 (Generic Desktop), Usage 0x06.
KEYBOARD_DESC = bytes.fromhex("05 01 09 06 A1 01 05 07 19 E0 29 E7 81 02 C0")
# Vendor page 0xFF00 usage 0x01 (the A1X's *other* vendor interface family).
OTHER_VENDOR_DESC = bytes.fromhex("06 00 FF 09 01 A1 01 09 01 81 02 C0")

# First 32 bytes of the real descriptors of the two 1A2C:B001 hidraw nodes on
# an AOKZOE A1X (captured 2026-11-11). Truncated, as `od | head -2` printed.
A1X_LED_DESC = bytes.fromhex(
    "06 01 ff 09 01 a1 01 09 02 75 08 95 40 15 00 26"
    "ff 00 81 02 09 03 75 08 95 40 15 00 26 ff 00 91"
)
A1X_MOUSE_DESC = bytes.fromhex(
    "05 01 09 02 a1 01 05 09 19 01 29 08 15 00 25 01"
    "95 08 75 01 81 02 05 01 09 01 a1 00 09 30 09 31"
)


def uevent(vid: int, pid: int) -> str:
    return (
        "DRIVER=hid-generic\n"
        f"HID_ID=0003:{vid:08X}:{pid:08X}\n"
        "HID_NAME=Test Device\n"
    )


class ParseTest(unittest.TestCase):
    def test_parse_hid_id(self):
        self.assertEqual(
            parse_hid_id(uevent(0x1A2C, 0xB001)), (0x0003, 0x1A2C, 0xB001)
        )
        self.assertIsNone(parse_hid_id("DRIVER=foo\n"))

    def test_top_level_usages(self):
        self.assertEqual(top_level_usages(VENDOR_DESC), [(0xFF01, 0x01)])
        self.assertEqual(top_level_usages(KEYBOARD_DESC), [(0x01, 0x06)])

    def test_multiple_and_nested_collections(self):
        desc = bytes.fromhex(
            "05 01 09 02 A1 01 09 01 A1 00 C0 C0"  # mouse with nested physical
            "06 01 FF 09 01 A1 01 C0"  # vendor
        )
        self.assertEqual(top_level_usages(desc), [(0x01, 0x02), (0xFF01, 0x01)])

    def test_extended_usage(self):
        # 4-byte usage includes its page: 0xFF01_0001
        desc = bytes.fromhex("0B 01 00 01 FF A1 01 C0")
        self.assertEqual(top_level_usages(desc), [(0xFF01, 0x01)])

    def test_truncated_descriptor(self):
        self.assertEqual(top_level_usages(bytes.fromhex("06 01")), [])


class FindTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name: str, vid: int, pid: int, desc: bytes | None):
        d = os.path.join(self.root, name, "device")
        os.makedirs(d)
        with open(os.path.join(d, "uevent"), "w") as f:
            f.write(uevent(vid, pid))
        if desc is not None:
            with open(os.path.join(d, "report_descriptor"), "wb") as f:
                f.write(desc)

    def test_finds_led_interface(self):
        self.add("hidraw0", 0x1A2C, 0xB001, KEYBOARD_DESC)
        self.add("hidraw1", 0x1A86, 0xFE00, OTHER_VENDOR_DESC)
        self.add("hidraw2", 0x1A2C, 0xB001, OTHER_VENDOR_DESC)
        self.add("hidraw3", 0x1A2C, 0xB001, VENDOR_DESC)
        self.add("hidraw4", 0x045E, 0x028E, VENDOR_DESC)
        self.assertEqual(
            oxp_hid_v2.find_device(sysfs_root=self.root), "/dev/hidraw3"
        )

    def test_real_a1x_descriptors(self):
        self.assertEqual(top_level_usages(A1X_LED_DESC), [(0xFF01, 0x01)])
        self.assertEqual(top_level_usages(A1X_MOUSE_DESC), [(0x01, 0x02)])
        # Same layout as the device: LED interface on hidraw0, mouse on hidraw2.
        self.add("hidraw0", 0x1A2C, 0xB001, A1X_LED_DESC)
        self.add("hidraw1", 0x0001, 0x0001, KEYBOARD_DESC)
        self.add("hidraw2", 0x1A2C, 0xB001, A1X_MOUSE_DESC)
        self.assertEqual(
            oxp_hid_v2.find_device(sysfs_root=self.root), "/dev/hidraw0"
        )

    def test_not_found(self):
        self.add("hidraw0", 0x1A2C, 0xB001, KEYBOARD_DESC)
        self.assertIsNone(oxp_hid_v2.find_device(sysfs_root=self.root))

    def test_missing_files_are_skipped(self):
        os.makedirs(os.path.join(self.root, "hidraw0"))  # no device/ dir
        self.add("hidraw1", 0x1A2C, 0xB001, None)  # no report_descriptor
        self.add("hidraw2", 0x1A2C, 0xB001, VENDOR_DESC)
        self.assertEqual(
            oxp_hid_v2.find_device(sysfs_root=self.root), "/dev/hidraw2"
        )

    def test_vid_pid_only(self):
        self.add("hidraw0", 0x1A2C, 0xB001, None)
        self.assertEqual(
            find_hidraw(0x1A2C, 0xB001, sysfs_root=self.root), ["/dev/hidraw0"]
        )

    def test_missing_sysfs_root(self):
        self.assertEqual(
            find_hidraw(1, 2, sysfs_root=os.path.join(self.root, "nope")), []
        )


if __name__ == "__main__":
    unittest.main()
