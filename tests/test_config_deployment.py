# SPDX-License-Identifier: MIT
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "recipes-core/openh432-storage/files/config-deployment.py"
spec = importlib.util.spec_from_file_location("deployment", SOURCE)
deployment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deployment)


class ConfigurationDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.defaults = self.root / "factory"
        self.defaults.mkdir()
        (self.defaults / "service.conf").write_text("vendor=1\n")
        (self.defaults / "subdir").mkdir()
        (self.defaults / "subdir/setting").write_text("old\n")
        (self.defaults / "link").symlink_to("/usr/lib/vendor.conf")
        self.old = self.root / "old"
        deployment.prepare(self.defaults, self.old)
        self.new = self.root / "new"

    def test_initial_copy_and_permissions(self):
        self.assertEqual(deployment.inventory(self.defaults), deployment.inventory(self.old / "etc"))
        self.assertEqual((self.old / "etc").stat().st_mode & 0o777, 0o755)
        self.assertTrue(json.loads((self.old / "deployment.json").read_text())["complete"])

    def test_untouched_receives_new_defaults(self):
        (self.defaults / "service.conf").write_text("vendor=2\n")
        deployment.prepare(self.defaults, self.new, self.old)
        self.assertEqual((self.new / "etc/service.conf").read_text(), "vendor=2\n")
        self.assertEqual((self.old / "etc/service.conf").read_text(), "vendor=1\n")

    def test_local_change_survives(self):
        (self.old / "etc/service.conf").write_text("local=yes\n")
        deployment.prepare(self.defaults, self.new, self.old)
        self.assertEqual((self.new / "etc/service.conf").read_text(), "local=yes\n")

    def test_conflict_does_not_publish_or_touch_old(self):
        (self.old / "etc/service.conf").write_text("secret-local\n")
        (self.defaults / "service.conf").write_text("vendor=2\n")
        with self.assertRaises(deployment.Conflict) as caught:
            deployment.prepare(self.defaults, self.new, self.old)
        self.assertNotIn("secret-local", str(caught.exception))
        self.assertFalse(self.new.exists())
        self.assertEqual((self.old / "etc/service.conf").read_text(), "secret-local\n")

    def test_matching_edits_are_not_conflict(self):
        for root in (self.old / "etc", self.defaults):
            (root / "service.conf").write_text("same\n")
        deployment.prepare(self.defaults, self.new, self.old)

    def test_local_delete_and_add(self):
        (self.old / "etc/service.conf").unlink()
        (self.old / "etc/local.conf").write_text("local")
        deployment.prepare(self.defaults, self.new, self.old)
        self.assertFalse((self.new / "etc/service.conf").exists())
        self.assertEqual((self.new / "etc/local.conf").read_text(), "local")

    def test_vendor_removal_of_unmodified_file(self):
        (self.defaults / "service.conf").unlink()
        deployment.prepare(self.defaults, self.new, self.old)
        self.assertFalse((self.new / "etc/service.conf").exists())

    def test_deleted_directory_new_child_conflicts(self):
        (self.old / "etc/subdir/setting").unlink()
        (self.old / "etc/subdir").rmdir()
        (self.defaults / "subdir/new").write_text("new")
        with self.assertRaises(deployment.Conflict):
            deployment.prepare(self.defaults, self.new, self.old)

    def test_permission_conflict(self):
        (self.old / "etc/service.conf").chmod(0o600)
        (self.defaults / "service.conf").chmod(0o640)
        with self.assertRaises(deployment.Conflict):
            deployment.prepare(self.defaults, self.new, self.old)

    def test_symlinks_copied_not_followed(self):
        deployment.prepare(self.defaults, self.new, self.old)
        self.assertEqual(os.readlink(self.new / "etc/link"), "/usr/lib/vendor.conf")

    def test_tampered_baseline_rejected(self):
        (self.old / "defaults/service.conf").write_text("changed")
        with self.assertRaisesRegex(ValueError, "baseline changed"):
            deployment.prepare(self.defaults, self.new, self.old)

    def test_incomplete_previous_rejected(self):
        (self.old / "deployment.json").write_text('{"version":1,"complete":false}')
        with self.assertRaisesRegex(ValueError, "incomplete"):
            deployment.prepare(self.defaults, self.new, self.old)

    def test_existing_destination_rejected(self):
        with self.assertRaisesRegex(ValueError, "overwrite"):
            deployment.prepare(self.defaults, self.old)

    def test_symlink_destination_rejected(self):
        self.new.symlink_to(self.root / "missing")
        with self.assertRaises(ValueError):
            deployment.prepare(self.defaults, self.new)

    def test_special_object_rejected(self):
        os.mkfifo(self.defaults / "fifo")
        with self.assertRaises(ValueError):
            deployment.prepare(self.defaults, self.new)

    def test_app_data_is_outside_reconciliation(self):
        data = self.root / "data/data/org.fractalmicro.reader/files/instance/settings.db"
        data.parent.mkdir(parents=True)
        data.write_bytes(b"unrelated application state")
        deployment.prepare(self.defaults, self.new, self.old)
        self.assertEqual(data.read_bytes(), b"unrelated application state")


if __name__ == "__main__":
    unittest.main()
