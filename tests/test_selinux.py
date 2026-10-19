# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SELinuxContract(unittest.TestCase):
    def test_policy_is_immutable_and_kernel_compatible(self):
        recipe = (ROOT / 'recipes-security/refpolicy/refpolicy-targeted_git.bbappend').read_text()
        self.assertIn('OPENH432_POLICY_VERSION = "33"', recipe)
        self.assertIn('ln -s ../usr/share/openh432/selinux', recipe)
        self.assertIn('POLICY_UNK_PERMS = "deny"', recipe)
        self.assertIn('("permissive", "enforcing")', recipe)
        self.assertIn('${STAGING_DIR_NATIVE}${base_sbindir_native}/setfiles', recipe)
        self.assertIn("-name 'file_contexts*.bin' -type f -delete", recipe)
        self.assertIn('fakeroot python do_label_identity()', recipe)
        self.assertIn('before do_package do_populate_sysroot', recipe)

    def test_labels_are_required_at_build_time(self):
        recipe = (ROOT / 'classes-recipe/openh432-selinux-image.bbclass').read_text()
        self.assertIn('setfiles -m -r', recipe)
        self.assertIn('security.selinux', recipe)
        self.assertIn('bbfatal', recipe)
        for image in ('openh432-systembase-b.bb', 'openh432-systemext.bb'):
            self.assertIn('inherit openh432-selinux-image',
                          (ROOT / 'recipes-core/images' / image).read_text())

    def test_audit_evidence_is_bounded_not_disabled(self):
        config = (ROOT / 'recipes-security/audit/files/openh432-auditd.conf').read_text()
        for setting in ('write_logs = yes', 'log_format = RAW', 'num_logs = 3',
                        'max_log_file = 8', 'max_log_file_action = ROTATE',
                        'priority_boost = 0', 'log_group = root'):
            self.assertIn(setting, config)
        recipe = (ROOT / 'recipes-security/audit/audit_%.bbappend').read_text()
        self.assertIn('install -m 0600', recipe)
        image = (ROOT / 'recipes-core/images/openh432-systembase-b.bb').read_text()
        self.assertIn('openh432-selinux-state auditd', image)

    def test_persistent_labels_are_versioned(self):
        script = (ROOT / 'recipes-security/openh432-selinux-state/files/label-state').read_text()
        self.assertIn('test -s "$input"', script)
        self.assertIn('selinux-label-version', script)
        self.assertIn('read -r version < "$policy/label-version"', script)
        self.assertNotIn('sha256sum', script)
        self.assertIn('chcon --reference=/.openh432/lower /\n', script)
        self.assertNotIn('restorecon -F /\n', script)
        self.assertLess(script.index('chcon --reference=/.openh432/lower /\n'),
                        script.index('if [ -f "$marker" ]'))
        self.assertIn('restorecon -RF /etc /var /home /root /data /cache', script)
        self.assertNotIn('restorecon -RF /\n', script)
        unit = (ROOT / 'recipes-security/openh432-selinux-state/files/FMSELinuxState.service').read_text()
        self.assertIn('ProtectSystem=yes\n', unit)
        self.assertNotIn('ProtectSystem=full', unit)


if __name__ == '__main__':
    unittest.main()
