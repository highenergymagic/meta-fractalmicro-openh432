# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RebootImageContract(unittest.TestCase):
    def test_isolated_components(self):
        recipe = (ROOT / "recipes-core/images/openh432-reboot-test.bb").read_text()
        self.assertIn("linux-h432b-reboot-test:do_deploy", recipe)
        self.assertIn("/kernel-reboot-test/zImage", recipe)
        self.assertIn("s5pv210-hims-u2-reboot-test.dtb", recipe)
        self.assertIn('S = "${UNPACKDIR}"', recipe)

    def test_separate_output(self):
        recipe = (ROOT / "recipes-core/images/openh432-reboot-test.bb").read_text()
        self.assertIn("openh432-reboot-test.img", recipe)
        self.assertNotIn("rm -f ${B}/openh432-ram-boot.img", recipe)

    def test_default_unmodified(self):
        recipe = (ROOT / "recipes-core/images/openh432-fastboot-ram.bb").read_text()
        self.assertNotIn("reboot-test", recipe)
        self.assertIn("linux-h432b:do_deploy", recipe)

if __name__ == "__main__":
    unittest.main()
