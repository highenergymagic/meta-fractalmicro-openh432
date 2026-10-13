# SPDX-License-Identifier: MIT
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = (Path(__file__).resolve().parents[1] /
          'recipes-connectivity/openh432-maintenance-ssh/files/prepare-host-key.py')
spec = importlib.util.spec_from_file_location('host_key', SOURCE)
host_key = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host_key)


class HostKeyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.calls = []
        # Native container tests are unprivileged; exercise real mode/type
        # checks while substituting only the fixture owner's uid.
        original = Path.lstat

        def lstat(path):
            values = list(original(path))
            values[4] = 0
            return os.stat_result(values)

        self.patch = patch.object(Path, 'lstat', lstat)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def keygen(self, args, **kwargs):
        self.calls.append(args)
        path = Path(args[-1])
        if '-t' in args:
            path.write_bytes(b'test-key')
            path.chmod(0o600)
        elif path.read_bytes() != b'test-key':
            raise subprocess.CalledProcessError(1, args)

    def prepare(self):
        with patch.object(subprocess, 'run', self.keygen):
            host_key.prepare(self.root, '/keygen')

    def test_generate_once_and_reuse(self):
        self.prepare()
        inode = (self.root / 'host_ed25519').stat().st_ino
        self.prepare()
        self.assertEqual(inode, (self.root / 'host_ed25519').stat().st_ino)
        self.assertEqual(sum('-t' in command for command in self.calls), 1)
        self.assertEqual((self.root / 'host_ed25519').stat().st_mode & 0o777, 0o600)

    def test_invalid_existing_key_never_rotates(self):
        key = self.root / 'host_ed25519'
        key.write_bytes(b'broken')
        key.chmod(0o600)
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare()
        self.assertEqual(key.read_bytes(), b'broken')
        self.assertFalse(any('-t' in command for command in self.calls))

    def test_symlink_and_insecure_key_refused(self):
        key = self.root / 'host_ed25519'
        key.symlink_to('missing')
        with self.assertRaises(ValueError):
            self.prepare()
        key.unlink()
        key.write_bytes(b'test-key')
        key.chmod(0o644)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_generation_failure_does_not_publish(self):
        with patch.object(subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'keygen')):
            with self.assertRaises(subprocess.CalledProcessError):
                host_key.prepare(self.root, '/keygen')
        self.assertFalse((self.root / 'host_ed25519').exists())
        self.assertFalse(list(self.root.glob('.host-key-*')))

    def test_directory_permissions_and_lock_symlink_refused(self):
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):
            self.prepare()
        self.root.chmod(0o700)
        (self.root / '.host-key.lock').symlink_to('missing')
        with self.assertRaises(OSError):
            self.prepare()
