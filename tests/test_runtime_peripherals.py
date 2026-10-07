# SPDX-License-Identifier: MIT
"""Default-image integration without automatic hardware exercises."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimePeripherals(unittest.TestCase):
    def test_vibration_command_in_systembase(self):
        recipe = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn(" h432b-vibrator-test", recipe)

    def test_no_automatic_vibration(self):
        for directory in ("recipes-core", "recipes-connectivity", "recipes-support"):
            for path in (ROOT / directory).rglob("*"):
                if path.is_file() and path.suffix in (".service", ".sh"):
                    self.assertNotIn("h432b-vibrator-test", path.read_text(),
                                     str(path))


if __name__ == "__main__":
    unittest.main()
