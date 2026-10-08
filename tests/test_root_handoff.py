# SPDX-License-Identifier: MIT
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "recipes-core/openh432-root-handoff/files/init"

class RootHandoff(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(["sh", "-n", str(INIT)], check=True)

    def test_no_write_or_implicit_fallback(self):
        text = INIT.read_text()
        for word in ("ubiformat", "ubiupdatevol", "ubimkvol", "flash_erase", "nandwrite"):
            self.assertNotIn(word, text)
        self.assertIn('case "$slot" in a|b)', text)
        self.assertIn('"systembase_$slot"', text)
        self.assertIn("linux-ubi", text)
        self.assertNotIn('fail "writable NAND profile"', text)
        self.assertIn("linux-reserved", text)
        for size in ("4194304", "531628032", "131072", "2048"):
            self.assertIn(size, text)
        for field in ("type", "corrupted", "upd_marker", "data_bytes"):
            self.assertIn('/' + field, text)
        self.assertIn('fail "slot mismatch"', text)

    def test_handoff_and_backing_mounts(self):
        text = INIT.read_text()
        self.assertLess(text.index("mount -t squashfs -o ro"), text.index("mount -t overlay"))
        self.assertLess(text.index("mount --move /lower"), text.index("exec switch_root"))
        self.assertIn("size=64m", text)
        self.assertIn("exec switch_root /newroot /sbin/init", text)
        for fs in ("dev", "proc", "sys", "run"):
            self.assertIn(f"mount --move /{fs} /newroot/{fs}", text)

    def test_nand_sound_timeout_is_bounded(self):
        policy = (ROOT / "recipes-core/openh432-sound-test-policy/openh432-nand-sound-policy_1.0.bb").read_text()
        self.assertIn("TimeoutStartSec=60s", policy)
        self.assertIn("TimeoutStopSec=10s", policy)
        self.assertIn("TimeoutStopSec=30s", policy)

    def test_images_are_separated_and_bounded(self):
        images = ROOT / "recipes-core/images"
        early = (images / "openh432-early-b.bb").read_text()
        base = (images / "openh432-systembase-b.bb").read_text()
        bundle = (images / "openh432-nand-b.bb").read_text()
        self.assertNotIn("systemd", early)
        self.assertIn("openh432-system-sounds-player", early)
        self.assertIn("kde3-sounds-startup", early)
        self.assertIn("openh432-root-handoff", early)
        self.assertIn("kde3-sounds", base)
        self.assertIn("openh432-wired-policy", base)
        self.assertIn('IMAGE_FSTYPES = "squashfs"', base)
        self.assertIn('EXTRA_IMAGECMD:squashfs = "-comp gzip -noappend -processors 1"', base)
        self.assertIn("16760832", bundle)
        self.assertIn("linux-h432b-runtime:do_deploy", bundle)
        self.assertIn("openh432-early-b-h432b.rootfs.cpio.xz", bundle)
        self.assertNotIn("openh432-ram-dev-h432b.rootfs.cpio.xz", bundle)

if __name__ == "__main__":
    unittest.main()
