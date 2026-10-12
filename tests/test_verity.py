# SPDX-License-Identifier: MIT
"""Verity image, handoff and dependency contracts; pinned-tool vectors run at build."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "recipes-core/images"
HANDOFF = ROOT / "recipes-core/openh432-root-handoff"
spec = importlib.util.spec_from_file_location("verity", IMAGES / "files/make-verity-image.py")
verity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verity)


class Verity(unittest.TestCase):
    def test_kernel_descriptor_depends_on_completed_root_not_reverse(self):
        early = (IMAGES / "openh432-early-b.bb").read_text()
        root = (IMAGES / "openh432-systembase-b.bb").read_text()
        self.assertIn('do_rootfs[depends] += "openh432-systembase-b:do_image_complete"', early)
        self.assertIn("/etc/openh432/systembase.verity", early)
        self.assertIn("cryptsetup-native:do_populate_sysroot", root)
        self.assertNotIn("openh432-early-b:", root)

    def test_empty_oversized_and_overlapping_inputs_fail_before_tool(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output, meta = (root / n for n in ("source", "out", "meta"))
            source.touch()
            with self.assertRaises(ValueError):
                verity.build(source, output, meta, "/no/tool")
            source.write_bytes(b"payload")
            with self.assertRaises(ValueError):
                verity.build(source, output, meta, "/no/tool", capacity=1)
            with self.assertRaises(ValueError):
                verity.build(source, source, meta, "/no/tool")

    def test_handoff_never_mounts_raw_root(self):
        init = (HANDOFF / "files/init").read_text()
        self.assertIn('openh432-verity-open "$volume" "$block" || fail', init)
        self.assertIn("mount -t squashfs -o ro /dev/mapper/systembase", init)
        self.assertNotIn('mount -t squashfs -o ro "$block"', init)
        helper = (HANDOFF / "files/verity-open").read_text()
        subprocess.run(["sh", "-n", str(HANDOFF / "files/verity-open")], check=True)
        self.assertIn("--noudevsync", helper)
        self.assertIn("--readonly", helper)
        self.assertNotIn("ignore_corruption", helper)
        self.assertNotIn("restart_on_corruption", helper)

    def test_invalid_descriptors_never_invoke_dmsetup(self):
        helper = (HANDOFF / "files/verity-open").read_text()
        valid_hash = "a" * 64
        descriptors = ("", "2 1 1 " + valid_hash + " " + valid_hash + " 8192",
                      "1 0 0 " + valid_hash + " " + valid_hash + " 8192",
                      "1 1 2 " + valid_hash + " " + valid_hash + " 8192",
                      "1 9999999999 9999999999 a b 4096",
                      "1 1 1 bad bad 8192", "$(touch /tmp/never) 1 1 a b 8192",
                      "1 1 1 " + valid_hash + " " + valid_hash + " 8192 extra")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            metadata = root / "metadata"
            test = helper.replace("/etc/openh432/systembase.verity", str(metadata))
            test = test.replace("set -eu", "set -eu\ndmsetup() { echo UNEXPECTED; }")
            for data in descriptors:
                with self.subTest(data=data):
                    metadata.write_text(data + "\n")
                    result = subprocess.run(["sh", "-c", test, "test", "ubi0_3", "/dev/test"],
                                            capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("UNEXPECTED", result.stdout)

    def test_health_requires_valid_mapping_on_selected_slot(self):
        health = (ROOT / "recipes-core/openh432-boot-success/files/mark-good").read_text()
        self.assertIn('device="/dev/mapper/systembase"', health)
        self.assertIn('dmsetup status systembase', health)
        self.assertIn('$4 == "V"', health)
        self.assertIn('/slaves/ubiblock0_$root', health)

    def test_mapper_node_is_explicitly_created_without_udev(self):
        helper = (HANDOFF / "files/verity-open").read_text()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "metadata").write_text("1 1 1 " + "a" * 64 + " " + "b" * 64 + " 8192\n")
            (root / "bytes").write_text("8192\n")
            (root / "device").touch()
            script = helper.replace("/etc/openh432/systembase.verity", str(root / "metadata"))
            script = script.replace("/sys/class/ubi/$volume/data_bytes", str(root / "bytes"))
            script = script.replace("/dev/mapper/systembase", str(root / "mapper"))
            script = script.replace("-b ", "-f ")
            script = script.replace("set -eu", """set -eu
dmsetup() {
    printf '%s\\n' "$*"
    if [ "$1" = mknodes ]; then touch """ + str(root / "mapper") + """; fi
}
""")
            result = subprocess.run(["sh", "-c", script, "test", "ubi0_3", str(root / "device")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines()[-1], "mknodes systembase")
