# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "recipes-core/openh432-local-console"

class LocalConsolePolicy(unittest.TestCase):
    def test_only_standard_nand_image_selects_policy(self):
        self.assertIn(" openh432-local-console", (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text())
        self.assertNotIn("openh432-local-console", (ROOT / "recipes-core/images/openh432-base-image.inc").read_text())

    def test_stable_unprivileged_locked_account(self):
        recipe = (POLICY / "openh432-local-console_1.0.bb").read_text()
        for required in ("--uid 1000", "--gid 1000 user", "--gid user",
                         "--home-dir /home/user", "--password '!'", "--shell /bin/sh"):
            self.assertIn(required, recipe)
        self.assertNotIn("--groups", recipe)
        self.assertNotIn("sudo", recipe)

    def test_autologin_is_tty1_only(self):
        recipe = (POLICY / "openh432-local-console_1.0.bb").read_text()
        self.assertIn("/getty@tty1.service.d", recipe)
        self.assertNotIn("/getty@.service.d", recipe)
        dropin = (POLICY / "files/autologin.conf").read_text()
        self.assertIn("ExecStart=\nExecStart=-/usr/sbin/agetty --autologin user", dropin)
        self.assertNotIn("--autologin root", dropin)

    def test_ssh_still_disables_password_login(self):
        service = (ROOT / "recipes-connectivity/openh432-maintenance-ssh/files/FMRemoteAccess.service").read_text()
        self.assertIn(" -s ", service)
        self.assertIn("ConditionFileNotEmpty=/root/.ssh/authorized_keys", service)

if __name__ == "__main__":
    unittest.main()
