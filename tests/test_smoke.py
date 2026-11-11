import json
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "py_modules"))

import a1x_rgb  # noqa: E402


class SmokeTest(unittest.TestCase):
    def test_package_imports(self):
        self.assertRegex(a1x_rgb.__version__, r"^\d+\.\d+\.\d+$")

    def test_versions_match(self):
        # Decky shows package.json's version; the backend reports __version__.
        with open(os.path.join(ROOT, "package.json")) as f:
            self.assertEqual(json.load(f)["version"], a1x_rgb.__version__)


if __name__ == "__main__":
    unittest.main()
