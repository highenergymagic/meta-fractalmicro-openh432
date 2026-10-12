# SPDX-License-Identifier: MIT
"""Audio completion fences never gate root handoff or release live mounts."""
import fcntl
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / 'recipes-core/openh432-root-handoff/files'
SOUNDS = ROOT / 'recipes-core/openh432-system-sounds/files'


class EarlyAudio(unittest.TestCase):
    def test_shell_syntax_and_worker_ownership(self):
        for path in (HANDOFF / 'start-early-sound', SOUNDS / 'finish-early-sound'):
            subprocess.run(['sh', '-n', str(path)], check=True)
        start = (HANDOFF / 'start-early-sound').read_text()
        self.assertLess(start.index('flock -x 9'), start.index('chroot "$root"'))
        self.assertIn('3>&- 4>&- &', start)
        self.assertIn('/usr/lib/*.so*', start)
        self.assertNotIn('wait ', start)

    def test_only_audio_consumers_require_completion(self):
        for path in (SOUNDS / 'FMBootSound.service',
                     ROOT / 'recipes-accessibility/openh432-speech/files/FMSpeech.service'):
            unit = path.read_text()
            self.assertIn('Requires=FMEarlySound.service', unit)
            self.assertIn('After=FMEarlySound.service', unit)
        unit = (SOUNDS / 'FMEarlySound.service').read_text()
        self.assertNotIn('WantedBy=', unit)
        self.assertIn('TimeoutStartSec=35s', unit)
        self.assertIn('ConditionPathExists=!/run/openh432-startup-sound.done', unit)
        self.assertNotIn('ExecStart=/usr/libexec/openh432-finish', unit)
        self.assertIn('Wants=FMEarlySoundCleanup.service', unit)
        cleanup = (SOUNDS / 'FMEarlySoundCleanup.service').read_text()
        self.assertIn('After=FMEarlySound.service FMAccessibility.target', cleanup)

    def test_cleanup_waits_for_worker_and_unmounts_before_removal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            capsule = root / 'capsule'
            capsule.mkdir()
            for name in ('dev', 'proc', 'run'):
                (capsule / name).mkdir()
            lock = root / 'lock'
            script = (SOUNDS / 'finish-early-sound').read_text()
            script = script.replace('/run/openh432-early-sound.root', str(capsule))
            script = script.replace('/run/openh432-early-sound.lock', str(lock))
            script = script.replace('set -eu', '''set -eu
mountpoint() { return 0; }
umount() { echo "unmount $1"; }
''')
            with lock.open('w') as held:
                fcntl.flock(held, fcntl.LOCK_EX)
                process = subprocess.Popen(['sh', '-c', script], stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True)
                try:
                    time.sleep(0.05)
                    self.assertIsNone(process.poll())
                    self.assertTrue(capsule.is_dir())
                finally:
                    fcntl.flock(held, fcntl.LOCK_UN)
                out, err = process.communicate(timeout=3)
            self.assertEqual(process.returncode, 0, err)
            self.assertEqual(out.splitlines(), [f'unmount {capsule}/{n}' for n in ('run', 'proc', 'dev')])
            self.assertFalse(capsule.exists())

    def test_failed_unmount_does_not_remove_capsule(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            capsule = root / 'capsule'
            capsule.mkdir()
            (capsule / 'keep').touch()
            script = (SOUNDS / 'finish-early-sound').read_text()
            script = script.replace('/run/openh432-early-sound.root', str(capsule))
            script = script.replace('/run/openh432-early-sound.lock', str(root / 'lock'))
            script = script.replace('set -eu', 'set -eu\nmountpoint() { return 0; }\numount() { return 1; }')
            result = subprocess.run(['sh', '-c', script], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((capsule / 'keep').exists())
