# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "recipes-accessibility/openh432-braille"
class BraillePolicy(unittest.TestCase):
    def test_normal_systembase_includes_braille(self):
        self.assertIn(" openh432-braille", (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text())
    def test_standard_service_enabled(self):
        self.assertIn('SYSTEMD_AUTO_ENABLE:${PN} = "enable"', (RECIPE / "openh432-braille_1.0.bb").read_text())
    def test_no_network_api_or_generic_secret(self):
        conf = (RECIPE / "files/brltty.conf").read_text()
        self.assertIn("Host=:0,Auth=user:root", conf)
        self.assertNotIn("Auth=none", conf)
        self.assertNotIn("0.0.0.0", conf)
    def test_service_owns_private_runtime_directory(self):
        service = (RECIPE / "files/FMBraille.service").read_text()
        self.assertIn("RuntimeDirectoryMode=0700", service)
        self.assertIn("ConditionPathExists=/dev/h432b-braille", service)
        self.assertIn("/usr/bin/brltty -n -e -f /etc/brltty.conf", service)
