import unittest

from _util import load_hhd_functions

from a1x_rgb import oxp_hid_v2 as p


def pad(*prefix: int) -> bytes:
    return bytes(prefix) + bytes(64 - len(prefix))


class PacketTest(unittest.TestCase):
    def test_all_packets_are_64_bytes(self):
        packets = [
            p.gen_brightness(True, "low"),
            p.gen_solid(1, 2, 3),
            *(p.gen_effect(s) for s in p.STYLES),
        ]
        for pkt in packets:
            self.assertEqual(len(pkt), 64)

    def test_brightness(self):
        self.assertEqual(p.gen_brightness(True, "low"), pad(7, 0xFF, 0xFD, 1, 5, 1))
        self.assertEqual(p.gen_brightness(True, "medium"), pad(7, 0xFF, 0xFD, 1, 5, 3))
        self.assertEqual(p.gen_brightness(True, "high"), pad(7, 0xFF, 0xFD, 1, 5, 4))
        self.assertEqual(p.gen_brightness(False, "high"), pad(7, 0xFF, 0xFD, 0, 5, 4))

    def test_solid(self):
        pkt = p.gen_solid(0x11, 0x22, 0x33)
        self.assertEqual(pkt[:3], bytes([7, 0xFF, 0xFE]))
        self.assertEqual(pkt[3:63], bytes([0x11, 0x22, 0x33] * 20))
        self.assertEqual(pkt[63], 0)

    def test_effect_codes(self):
        expected = {
            "aok": 0x0E,
            "monster_woke": 0x0D,
            "flowing": 0x03,
            "sunset": 0x0B,
            "neon": 0x05,
            "dreamy": 0x07,
            "cyberpunk": 0x09,
            "colorful": 0x0C,
            "aurora": 0x01,
            "sun": 0x08,
        }
        self.assertEqual(set(p.STYLES), set(expected))
        for style, code in expected.items():
            with self.subTest(style=style):
                self.assertEqual(p.gen_effect(style), pad(7, 0xFF, code))

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            p.gen_brightness(True, "max")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            p.gen_effect("classic")
        with self.assertRaises(ValueError):
            p.gen_solid(256, 0, 0)
        with self.assertRaises(ValueError):
            p.gen_solid(-1, 0, 0)

    def test_sequences(self):
        self.assertEqual(p.sequence_off(), [p.gen_brightness(False, "high")])
        self.assertEqual(
            p.sequence_solid(1, 2, 3),
            [p.gen_brightness(True, "high"), p.gen_solid(1, 2, 3)],
        )
        self.assertEqual(
            p.sequence_effect("aurora", "low"),
            [p.gen_brightness(True, "low"), p.gen_effect("aurora")],
        )


class MatchesHhdTest(unittest.TestCase):
    """Byte-for-byte comparison against HHD's own packet builders."""

    @classmethod
    def setUpClass(cls):
        cls.hhd = load_hhd_functions(
            "device/oxp/hid_v2.py",
            ["gen_cmd", "gen_rgb_mode", "gen_brightness", "gen_rgb_solid"],
        )

    def setUp(self):
        if self.hhd is None:
            self.skipTest("HHD source not available")

    def test_brightness(self):
        for enabled in (True, False):
            for level in ("low", "medium", "high"):
                with self.subTest(enabled=enabled, level=level):
                    self.assertEqual(
                        p.gen_brightness(enabled, level),  # type: ignore[arg-type]
                        self.hhd["gen_brightness"](enabled, level),
                    )

    def test_solid(self):
        for rgb in [(0, 0, 0), (255, 255, 255), (0xB7, 0x30, 0x00), (1, 128, 254)]:
            with self.subTest(rgb=rgb):
                self.assertEqual(p.gen_solid(*rgb), self.hhd["gen_rgb_solid"](*rgb))

    def test_effects(self):
        for style in p.STYLES:
            with self.subTest(style=style):
                self.assertEqual(p.gen_effect(style), self.hhd["gen_rgb_mode"](style))


if __name__ == "__main__":
    unittest.main()
