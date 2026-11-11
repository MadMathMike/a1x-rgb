import unittest

from _util import load_hhd_functions

from a1x_rgb.color import hsb_to_rgb


class HsbToRgbTest(unittest.TestCase):
    def test_known_values(self):
        cases = {
            (0, 100, 100): (255, 0, 0),
            (120, 100, 100): (0, 255, 0),
            (240, 100, 100): (0, 0, 255),
            (0, 0, 100): (255, 255, 255),
            (0, 0, 0): (0, 0, 0),
            (360, 100, 100): (255, 0, 4),  # clamped to 359, as in HHD
            (30, 100, 50): (127, 63, 0),  # HHD's default colour
        }
        for args, expected in cases.items():
            with self.subTest(args=args):
                self.assertEqual(hsb_to_rgb(*args), expected)

    def test_matches_hhd(self):
        hhd = load_hhd_functions("utils.py", ["hsb_to_rgb"])
        if hhd is None:
            self.skipTest("HHD source not available")
        for h in range(0, 361, 5):
            for s in range(0, 101, 10):
                for v in range(0, 101, 10):
                    self.assertEqual(
                        list(hsb_to_rgb(h, s, v)),
                        hhd["hsb_to_rgb"](h, s, v),
                        f"h={h} s={s} v={v}",
                    )


if __name__ == "__main__":
    unittest.main()
