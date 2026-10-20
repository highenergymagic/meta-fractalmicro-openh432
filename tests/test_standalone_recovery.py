# SPDX-License-Identifier: MIT
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ui = module('recovery_ui', ROOT / 'recipes-core/openh432-recovery/files/recovery-ui.py')
provision = module('recovery_provision', ROOT / 'recipes-core/openh432-storage/files/storage-provision.py')


class RecoveryTests(unittest.TestCase):
    def test_image_includes_board_storage_policy(self):
        recipe = (ROOT / 'recipes-core/images/openh432-recovery-root.bb').read_text()
        self.assertIn('h432b-storage-policy', recipe)
        self.assertIn('test -s ${IMAGE_ROOTFS}/usr/lib/openh432/storage-controller', recipe)

    def test_incremental_build_removes_previous_output(self):
        recipe = (ROOT / 'recipes-core/images/openh432-recovery-image.bb').read_text()
        self.assertLess(recipe.index('rm -f ${B}/openh432-recovery.img'),
                        recipe.index('python3 ${UNPACKDIR}/make-boot-image.py'))

    def test_entry_never_executes_an_action(self):
        for request in ('menu', 'factory-reset', 'wipe-cache'):
            menu = ui.Menu(request)
            self.assertEqual(menu.label(), 'recovery menu')
            self.assertIsNone(menu.key(ui.KEYS[2]))
            if request != 'menu':
                self.assertIsNone(menu.key(ui.KEYS[2]))
                self.assertEqual(menu.label(), 'cancel')
                self.assertIsNone(menu.key(ui.KEYS[2]))
                self.assertFalse(menu.confirming)

    def test_explicit_confirmation_and_no_repeat(self):
        for request in ('factory-reset', 'wipe-cache'):
            menu = ui.Menu(request)
            menu.key(ui.KEYS[2])
            menu.key(ui.KEYS[2])
            menu.key(ui.KEYS[1])
            self.assertEqual(menu.key(ui.KEYS[2]), request)
            self.assertFalse(menu.yes)
            self.assertIsNone(menu.key(ui.KEYS[2]))
            self.assertEqual(menu.label(), 'cancel')

    def test_request_validation(self):
        self.assertEqual(ui.request_from_cmdline('quiet'), 'menu')
        self.assertEqual(ui.request_from_cmdline('openh432.recovery=wipe-cache'), 'wipe-cache')
        for line in ('openh432.recovery=install', 'openh432.recovery=',
                     'openh432.recovery=menu openh432.recovery=menu'):
            with self.assertRaises(ValueError):
                ui.request_from_cmdline(line)

    def test_frames_use_linux_dot_order(self):
        self.assertEqual(ui.frame('y')[0], 0x3d)
        self.assertEqual(ui.frame('l')[0], 0x07)
        for label in (*ui.LABELS, 'erase user data', 'erase cache',
                      'working please wait', 'failed no automatic retry'):
            self.assertEqual(len(ui.frame(label)), 32)
        for bad in ('x' * 33, 'A', '1', '\n'):
            with self.assertRaises(ValueError):
                ui.frame(bad)

    def test_failure_does_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch('builtins.open', return_value=open(Path(tmp) / 'log', 'ab')), \
                patch.object(ui.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'test')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                ui.perform('wipe-cache')
            self.assertEqual(run.call_count, 1)

    def test_cache_only_writes_partition_three(self):
        storage = Mock()
        device = '/dev/mmcblk0'
        parts = [dict(node=device + 'p' + str(i)) for i in range(1, 5)]
        storage.run.return_value = '{}'
        storage.validate_layout.return_value = parts
        with patch.object(provision, 'runtime', return_value=storage), \
                patch.object(provision, 'ensure_unmounted') as inactive, \
                patch.object(Path, 'is_block_device', return_value=True):
            provision.wipe_cache(device)
        inactive.assert_called_once_with(device)
        self.assertEqual(storage.run.call_args_list[-1].args,
                         ('mkfs.f2fs', '-f', '-l', 'cache', device + 'p3'))
        self.assertEqual(storage.run.call_count, 2)

    def test_invalid_cache_layout_does_not_format(self):
        storage = Mock()
        storage.run.return_value = '{}'
        storage.validate_layout.side_effect = ValueError('wrong layout')
        with patch.object(provision, 'runtime', return_value=storage), \
                patch.object(provision, 'ensure_unmounted'):
            with self.assertRaises(ValueError):
                provision.wipe_cache('/dev/mmcblk0')
        self.assertEqual(storage.run.call_count, 1)

    def test_mounted_device_does_not_format(self):
        storage = Mock()
        with patch.object(provision, 'runtime', return_value=storage), \
                patch.object(provision, 'ensure_unmounted', side_effect=ValueError('mounted')):
            with self.assertRaises(ValueError):
                provision.wipe_cache('/dev/mmcblk0')
        storage.run.assert_not_called()

    def test_missing_seed_prevents_factory_reset(self):
        storage = Mock()
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(provision, 'runtime', return_value=storage):
            with self.assertRaises(ValueError):
                provision.provision('/dev/mmcblk0', Path(tmp), reset=True)
        storage.run.assert_not_called()

    def test_init_has_no_disk_mount_or_automatic_erase(self):
        init = ROOT / 'recipes-core/openh432-recovery/files/recovery-init'
        subprocess.run(['sh', '-n', str(init)], check=True)
        text = init.read_text()
        for forbidden in ('mkfs', 'storage-provision', 'ubiupdatevol', 'sfdisk'):
            self.assertNotIn(forbidden, text)
        self.assertIn('while :; do sleep 3600; done', text)


if __name__ == '__main__':
    unittest.main()
