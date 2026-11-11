import os
import tempfile
import unittest

import _util  # noqa: F401  (sets up sys.path)

from a1x_rgb import settings as store


class SettingsStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "sub", "settings.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file(self):
        self.assertEqual(store.load(self.path), {})

    def test_roundtrip_creates_directory(self):
        store.save(self.path, {"mode": "off", "hue": 10})
        self.assertEqual(store.load(self.path), {"mode": "off", "hue": 10})
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_corrupt_or_wrong_type(self):
        os.makedirs(os.path.dirname(self.path))
        for content in ("{not json", "[1, 2]", ""):
            with self.subTest(content=content):
                with open(self.path, "w") as f:
                    f.write(content)
                self.assertEqual(store.load(self.path), {})


if __name__ == "__main__":
    unittest.main()
