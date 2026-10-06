# SPDX-License-Identifier: MIT
"""RAM-image content and reproducibility contracts; no target hardware access."""
from pathlib import Path
import re
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "recipes-core/images/openh432-ram-dev.bb"
REQUIRED = ("init", "usr/lib/os-release", "usr/bin/systemd-analyze", "usr/bin/systemd-run",
            "usr/bin/systemd-repart", "usr/bin/systemd-sysext",
            "usr/lib/systemd/systemd-networkd", "usr/lib/libseccomp.so.2",
            "usr/lib/libacl.so.1", "usr/lib/libzstd.so.1")


class RamImage(unittest.TestCase):
    def test_explicit_tools_without_recommendations(self):
        text = RECIPE.read_text()
        packages = re.search(r'IMAGE_INSTALL = "([^"]+)"', text).group(1).split()
        for package in ("os-release", "systemd-networkd", "systemd-analyze", "systemd-extra-utils",
                        "libseccomp", "libacl", "libzstd"):
            self.assertIn(package, packages)
        self.assertIn('NO_RECOMMENDATIONS = "1"', text)

    def test_kernel_compatible_deterministic_compression(self):
        text = RECIPE.read_text()
        for setting in ('IMAGE_FSTYPES = "cpio.xz squashfs-xz"', 'XZ_INTEGRITY_CHECK = "crc32"',
                        'XZ_THREADS = "1"', 'XZ_MEMLIMIT = "128MiB"'):
            self.assertIn(setting, text)
        self.assertIn("16 * 1024 * 1024", text)
        self.assertIn("'/*.cpio.xz'", text)

    def test_pinned_image_metadata(self):
        text = RECIPE.read_text()
        self.assertIn('REPRODUCIBLE_TIMESTAMP_ROOTFS = "${SOURCE_DATE_EPOCH}"', text)
        self.assertIn('IMAGE_VERSION_SUFFIX = "-${SOURCE_DATE_EPOCH}"', text)

    def finalize(self, root):
        hook = re.search(r"python finalize_ram_root\(\) \{\n(.*?)\n\}",
                         RECIPE.read_text(), re.S).group(1)

        class Data:
            def getVar(self, key):
                assert key == "IMAGE_ROOTFS"
                return str(root)

        class BitBake:
            @staticmethod
            def fatal(message):
                raise RuntimeError(message)

        exec(textwrap.dedent(hook), {"d": Data(), "bb": BitBake()})

    def fixture(self, root):
        (root / "etc").mkdir()
        for relative in REQUIRED:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n")

    def test_final_root_is_volatile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            (root / "etc/fstab").write_text("/dev/test /data ext4 defaults 0 0\n")
            (root / "etc/machine-id").write_text("not-a-release-identity\n")
            self.finalize(root)
            self.assertEqual((root / "etc/machine-id").read_text(), "")
            self.assertTrue((root / "etc/fstab").read_text().startswith("#"))
            self.assertNotIn("/dev/", (root / "etc/fstab").read_text())

    def test_rejects_initrd_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            (root / "etc/initrd-release").touch()
            with self.assertRaisesRegex(RuntimeError, "switch-root"):
                self.finalize(root)

    def test_rejects_missing_component(self):
        for required in REQUIRED:
            with self.subTest(required=required), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.fixture(root)
                (root / required).unlink()
                with self.assertRaisesRegex(RuntimeError, "Missing RAM development"):
                    self.finalize(root)


if __name__ == "__main__":
    unittest.main()
