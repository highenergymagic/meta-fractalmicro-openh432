# SPDX-License-Identifier: MIT
import copy
import errno
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'recipes-core/openh432-storage/files/storage-runtime.py'
spec = importlib.util.spec_from_file_location('storage_runtime', SOURCE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def layout():
    start = 2048
    parts = []
    for label, size in zip(runtime.LABELS, (4194304, 4194304, 8388608, 8386527)):
        parts.append(dict(name=label, start=start, size=size))
        start += size
    return dict(partitiontable=dict(label='gpt', sectorsize=512,
                                   lastlba=start - 1, partitions=parts))


class StorageRuntimeTests(unittest.TestCase):
    def test_mount_label_is_copied_from_vendor_only_when_needed(self):
        label = b'system_u:object_r:etc_t:s0'
        for actual in (label, b'system_u:object_r:unlabeled_t:s0'):
            with patch.object(runtime.os, 'getxattr', side_effect=[label, actual]), \
                    patch.object(runtime.os, 'setxattr') as setter:
                runtime.restore_mount_label('/vendor/etc', '/deployment/etc')
                if actual == label:
                    setter.assert_not_called()
                else:
                    setter.assert_called_once_with('/deployment/etc', 'security.selinux',
                                                   label, follow_symlinks=False)

    def test_mount_label_absent_and_errors(self):
        missing = OSError(errno.ENODATA, 'no label')
        with patch.object(runtime.os, 'getxattr', side_effect=missing), \
                patch.object(runtime.os, 'setxattr') as setter:
            runtime.restore_mount_label('/vendor/etc', '/deployment/etc')
            setter.assert_not_called()
        with patch.object(runtime.os, 'getxattr', side_effect=[b'etc_label', missing]), \
                patch.object(runtime.os, 'setxattr') as setter:
            runtime.restore_mount_label('/vendor/etc', '/deployment/etc')
            setter.assert_called_once()
        with patch.object(runtime.os, 'getxattr', side_effect=PermissionError()):
            with self.assertRaises(PermissionError):
                runtime.restore_mount_label('/vendor/etc', '/deployment/etc')

    def test_existing_deployment_skips_migration_import(self):
        source = SOURCE.read_text()
        self.assertIn('if not destination.exists():\n        module = deployment_module()', source)
        self.assertNotIn('\nimport importlib.util\n', source)

    def test_machine_identity_is_readable_without_changing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'machine-id'
            value = 'b' * 32 + '\n'
            path.write_text(value)
            path.chmod(0o600)
            runtime.prepare_machine_id(path)
            self.assertEqual(path.read_text(), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o444)
            with patch.object(runtime.os, 'fchmod') as chmod:
                runtime.prepare_machine_id(path)
                chmod.assert_not_called()

    def test_invalid_identity_is_not_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'machine-id'
            for value in ('', 'b' * 32, 'B' * 32 + '\n', 'b' * 32 + '\nextra'):
                path.write_text(value)
                path.chmod(0o600)
                with self.assertRaises(ValueError):
                    runtime.prepare_machine_id(path)
                self.assertEqual(path.read_text(), value)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_machine_identity_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target'
            target.write_text('b' * 32 + '\n')
            target.chmod(0o600)
            link = Path(directory) / 'machine-id'
            link.symlink_to(target)
            with self.assertRaises(OSError):
                runtime.prepare_machine_id(link)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_persistent_identity_is_not_committed_as_transient(self):
        dropin = SOURCE.with_name('persistent-machine-id.conf').read_text()
        self.assertIn('ConditionPathExists=!/run/openh432-deployment', dropin)

    def test_health_sandbox_allows_marker_but_not_state_writes(self):
        dropin = SOURCE.with_name('persistent-boot-health.conf').read_text()
        self.assertIn('ReadWritePaths=-/.openh432/userdata', dropin)
        protected = next(line for line in dropin.splitlines()
                         if line.startswith('ReadOnlyPaths=')).split('=', 1)[1].split()
        self.assertEqual(set(protected), {
            '-/.openh432/userdata/' + name for name in
            ('var', 'home', 'root', 'data', 'identity', 'deployments')})
        recipe = SOURCE.parent.parent / 'openh432-storage_1.0.bb'
        for name in ('persistent-machine-id.conf', 'persistent-boot-health.conf'):
            self.assertIn('file://' + name, recipe.read_text())
            self.assertIn('${UNPACKDIR}/' + name, recipe.read_text())

    def test_unhealthy_deployment_is_not_committed(self):
        with patch.object(runtime, 'check_health', side_effect=ValueError('invalid')), \
                patch.object(runtime, 'durable_text') as write:
            with self.assertRaises(ValueError):
                runtime.mark_good()
            write.assert_not_called()

    def test_healthy_deployment_commit(self):
        identity = 'a' * 64
        with patch.object(runtime, 'check_health', return_value=identity), \
                patch.object(runtime, 'durable_text') as write:
            runtime.mark_good()
            write.assert_called_once_with('/.openh432/userdata/last-good', identity + '\n')

    def test_volatile_deployment_not_committed(self):
        with patch.object(runtime, 'check_health', return_value=None), \
                patch.object(runtime, 'durable_text') as write:
            runtime.mark_good()
            write.assert_not_called()

    def test_storage_health_precedes_boot_acknowledgement(self):
        root = SOURCE.parents[3]
        candidates = list(root.glob('recipes-*/**/mark-good'))
        self.assertEqual(len(candidates), 1)
        script = candidates[0].read_text()
        self.assertLess(script.index('storage-runtime check-health'),
                        script.index('h432b-bootstate-check --mark-good'))

    def test_valid_layout(self):
        self.assertEqual(len(runtime.validate_layout(layout())), 4)

    def test_invalid_labels_sizes_boundaries(self):
        for key, value in (('name', 'systemext_B'), ('size', 100), ('start', 4096)):
            with self.subTest(key=key):
                table = layout()
                table['partitiontable']['partitions'][0][key] = value
                with self.assertRaises(ValueError):
                    runtime.validate_layout(table)

    def test_small_userdata(self):
        table = layout()
        table['partitiontable']['partitions'][3]['size'] = 100
        with self.assertRaises(ValueError):
            runtime.validate_layout(table)

    def test_wrong_table_sector_or_count(self):
        for key, value in (('label', 'dos'), ('sectorsize', 4096), ('lastlba', 100), ('partitions', [])):
            with self.subTest(key=key):
                table = layout()
                table['partitiontable'][key] = value
                with self.assertRaises(ValueError):
                    runtime.validate_layout(table)

    def test_descriptor_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'verity'
            path.write_text('1 2 2 ' + 'a' * 64 + ' ' + 'b' * 64 + ' 12288\n')
            self.assertEqual(runtime.descriptor(path), (2, 'a' * 64, 'b' * 64))
            for content in ('', '1 -1 -1 a b 100',
                            '1 2 3 ' + 'a' * 64 + ' ' + 'b' * 64 + ' 12288',
                            '1 2 2 ' + 'A' * 64 + ' ' + 'b' * 64 + ' 12288'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    runtime.descriptor(path)

    def test_durable_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'last-good'
            runtime.durable_text(path, 'a' * 64 + '\n')
            self.assertEqual(path.read_text(), 'a' * 64 + '\n')
            self.assertFalse(path.with_name('last-good.new').exists())

    def test_existing_machine_rejected(self):
        with self.assertRaises(ValueError):
            runtime.activate('not-a-digest', 'A')


if __name__ == '__main__':
    unittest.main()
