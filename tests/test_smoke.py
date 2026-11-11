import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "py_modules"))

import a1x_rgb  # noqa: E402


class SmokeTest(unittest.TestCase):
    def test_package_imports(self):
        self.assertRegex(a1x_rgb.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
