# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class HardwareTestImage(unittest.TestCase):
    def test_sound_optin_is_explicit_image(self):
        text = (ROOT / "recipes-core/images/openh432-hardware-test.bb").read_text()
        self.assertIn("require openh432-ram-dev.bb", text)
        for name in ("kde3-sounds", "openh432-system-sounds", "openh432-sound-test-policy"):
            self.assertIn(name, text)
        default = (ROOT / "recipes-core/images/openh432-ram-dev.bb").read_text()
        self.assertNotIn("kde3-sounds", default)

    def test_flag_and_both_units(self):
        text = (ROOT / "recipes-core/openh432-sound-test-policy/openh432-sound-test-policy_1.0.bb").read_text()
        for value in ("system-sounds.enabled", "FMBootSound.service", "FMShutdownSound.service"):
            self.assertIn(value, text)

if __name__ == "__main__":
    unittest.main()
