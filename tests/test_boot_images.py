# SPDX-License-Identifier: MIT
"""Runtime and recovery share the kernel but have different root contracts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "recipes-core/images"


class BootImages(unittest.TestCase):
    def test_shared_envelope_has_no_kernel_or_root_dependency(self):
        common = (IMAGES / "openh432-boot-image.inc").read_text()
        self.assertIn("inherit deploy", common)
        self.assertIn('S = "${UNPACKDIR}"', common)
        self.assertNotIn("do_compile[depends]", common)

    def test_recovery_is_standalone_and_uses_runtime_kernel(self):
        recipe = (IMAGES / "openh432-fastboot-ram.bb").read_text()
        self.assertIn("require openh432-boot-image.inc", recipe)
        self.assertIn("linux-h432b-runtime:do_deploy", recipe)
        self.assertIn("/kernel-runtime/zImage", recipe)
        self.assertIn("s5pv210-hims-u2-runtime.dtb", recipe)
        self.assertIn("openh432-ram-dev:do_image_complete", recipe)
        self.assertIn("openh432-ram-boot.img", recipe)
        self.assertNotIn("openh432-early-b", recipe)

    def test_nand_uses_minimal_handoff_not_recovery_root(self):
        recipe = (IMAGES / "openh432-nand-b.bb").read_text()
        self.assertIn("require openh432-boot-image.inc", recipe)
        self.assertIn("linux-h432b-runtime:do_deploy", recipe)
        self.assertIn("openh432-early-b:do_image_complete", recipe)
        self.assertNotIn("openh432-ram-dev", recipe)
        self.assertFalse((IMAGES / "openh432-reboot-test.bb").exists())

    def test_root_compositions_share_metadata_not_a_test_image(self):
        for name in ("openh432-systembase-b", "openh432-ram-dev"):
            self.assertIn("require openh432-base-image.inc",
                          (IMAGES / (name + ".bb")).read_text())


if __name__ == "__main__":
    unittest.main()
