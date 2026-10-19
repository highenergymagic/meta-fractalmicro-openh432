# SPDX-License-Identifier: MIT
"""Exercise label-state control flow without changing host SELinux labels."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'recipes-security/openh432-selinux-state/files/label-state'


class LabelState(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.policy = self.root / 'policy'
        self.state = self.root / 'state'
        self.state.mkdir()
        self.version = 'a' * 64
        for name in ('contexts/files/file_contexts',
                     'contexts/files/file_contexts.subs_dist', 'policy/policy.33'):
            path = self.policy / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('test fixture\n')
        (self.policy / 'label-version').write_text(self.version + '\n')
        self.marker = self.state / 'selinux-label-version'
        self.log = self.root / 'calls'
        binaries = self.root / 'bin'
        binaries.mkdir()
        for name in ('chcon', 'restorecon', 'sync'):
            command = binaries / name
            command.write_text('#!/bin/sh\n'
                               'printf "%s %s\\n" "${0##*/}" "$*" >> "$CALL_LOG"\n'
                               'if [ "${0##*/}" = chcon ] && [ "${FAIL_CHCON:-0}" = 1 ]; '
                               'then exit 1; fi\n')
            command.chmod(0o755)
        script = SCRIPT.read_text()
        replacements = {
            'test -e /sys/fs/selinux/enforce': 'true',
            'policy=/usr/share/openh432/selinux/targeted':
                'policy=' + shlex.quote(str(self.policy)),
            'directory=/var/lib/openh432':
                'directory=' + shlex.quote(str(self.state)),
        }
        for old, new in replacements.items():
            self.assertEqual(script.count(old), 1)
            script = script.replace(old, new)
        self.script = self.root / 'label-state'
        self.script.write_text(script)
        self.environment = {**os.environ, 'PATH': str(binaries) + ':' + os.environ['PATH'],
                            'CALL_LOG': str(self.log)}

    def run_script(self, **environment):
        return subprocess.run(['/bin/sh', str(self.script)],
                              env={**self.environment, **environment},
                              capture_output=True, text=True)

    def test_current_policy_labels_root_without_tree_walk(self):
        self.marker.write_text(self.version + '\n')
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text().splitlines(),
                         ['chcon --reference=/.openh432/lower /'])

    def test_changed_policy_still_relabels_persistent_state(self):
        self.marker.write_text('b' * 64 + '\n')
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertEqual(calls[0], 'chcon --reference=/.openh432/lower /')
        self.assertIn('restorecon -RF /etc /var /home /root /data /cache', calls)
        self.assertEqual(self.marker.read_text(), self.version + '\n')

    def test_root_label_failure_preserves_old_marker(self):
        old = 'b' * 64 + '\n'
        self.marker.write_text(old)
        self.assertNotEqual(self.run_script(FAIL_CHCON='1').returncode, 0)
        self.assertEqual(self.marker.read_text(), old)
        self.assertEqual(self.log.read_text().splitlines(),
                         ['chcon --reference=/.openh432/lower /'])


if __name__ == '__main__':
    unittest.main()
