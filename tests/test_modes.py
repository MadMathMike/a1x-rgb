import json
import unittest

import _util  # noqa: F401  (sets up sys.path)

from a1x_rgb.device import OXP_HID_V2_DESCRIPTION as DESC
from a1x_rgb.modes import defaults, normalize


class ModesTest(unittest.TestCase):
    def test_description_is_json_serialisable(self):
        self.assertEqual(json.loads(json.dumps(DESC)), DESC)

    def test_description_matches_hhd_modes(self):
        self.assertEqual([m["key"] for m in DESC["modes"]], ["off", "solid", "aok"])
        for m in DESC["modes"]:
            for c in m["controls"]:
                self.assertIn(c, DESC["controls"])
        self.assertEqual(len(DESC["controls"]["style"]["options"]), 10)

    def test_defaults(self):
        self.assertEqual(
            defaults(DESC),
            {
                "mode": "solid",
                "hue": 30,
                "saturation": 100,
                "brightness": 50,
                "style": "aok",
                "level": "medium",
            },
        )

    def test_empty_gives_defaults(self):
        self.assertEqual(normalize(DESC, {}), defaults(DESC))

    def test_keeps_other_modes_values(self):
        s = normalize(DESC, {"mode": "aok", "hue": 200, "style": "aurora"})
        self.assertEqual(s["mode"], "aok")
        self.assertEqual(s["hue"], 200)
        self.assertEqual(s["style"], "aurora")

    def test_sliders_are_clamped_and_rounded(self):
        s = normalize(DESC, {"hue": 400, "saturation": -5, "brightness": 49.6})
        self.assertEqual((s["hue"], s["saturation"], s["brightness"]), (360, 0, 50))

    def test_unknown_keys_dropped(self):
        self.assertNotIn("bogus", normalize(DESC, {"bogus": 1}))

    def test_strict_rejects_invalid(self):
        for bad in (
            {"mode": "rainbow"},
            {"style": "classic"},
            {"level": "max"},
            {"hue": "red"},
            {"hue": True},
            {"brightness": None},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                normalize(DESC, bad, strict=True)

    def test_lenient_falls_back_to_defaults(self):
        s = normalize(DESC, {"mode": "rainbow", "style": "classic", "hue": "red", "level": "low"})
        self.assertEqual(s["mode"], "solid")
        self.assertEqual(s["style"], "aok")
        self.assertEqual(s["hue"], 30)
        self.assertEqual(s["level"], "low")


if __name__ == "__main__":
    unittest.main()
