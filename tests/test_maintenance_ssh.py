# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "recipes-connectivity/openh432-maintenance-ssh"
class MaintenanceSshTests(unittest.TestCase):
    def test_key_only_opt_in(self):
        service = (BASE / "files/FMRemoteAccess.service").read_text()
        self.assertIn("ConditionFileNotEmpty=/root/.ssh/authorized_keys", service)
        self.assertIn(" -s -j -k ", service)
        self.assertIn("-t ed25519", service)
        self.assertIn("RuntimeDirectoryMode=0700", service)
        self.assertNotIn("telnet", service)
    def test_pinned_component_no_shared_keys(self):
        recipe = (BASE / "openh432-maintenance-ssh_2025.89.bb").read_text()
        self.assertIn("require recipes-core/dropbear/dropbear_2025.89.bb", recipe)
        self.assertIn('PACKAGECONFIG = ""', recipe)
        self.assertNotIn("ssh-ed25519 ", recipe)
        self.assertIn("--mtime=@", recipe)
        self.assertIn('SYSTEMD_AUTO_ENABLE = "enable"', recipe)
if __name__ == "__main__":
    unittest.main()
