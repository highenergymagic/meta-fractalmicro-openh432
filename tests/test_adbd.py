# SPDX-License-Identifier: MIT
import importlib.util
import base64
import hashlib
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "recipes-connectivity/openh432-adbd"
FILES = RECIPE / "files"
spec = importlib.util.spec_from_file_location("adbd_port", FILES / "port-linux.py")
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)
spec = importlib.util.spec_from_file_location("adb_keys", FILES / "adb-keys.py")
keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keys)
spec = importlib.util.spec_from_file_location("adb_usb", FILES / "adb-usb.py")
usb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usb)


class AdbdPortTests(unittest.TestCase):
    def test_tls_comparison_rejects_errors_and_key_setup_failures(self):
        # Compile the transformed condition with API-result stubs. This tests
        # the C++ truth/error semantics, not merely a source-string contract.
        compiler = os.environ.get("POWER_NATIVE_CC")
        if not compiler:
            self.skipTest("Run scripts/test-layers.py for pinned compiler vectors")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comparison.c"
            path.write_text('''        EVP_PKEY_set1_RSA(known_evp.get(), key);
        if (EVP_PKEY_cmp(known_evp.get(), evp_pkey.get())) {''')
            port.harden_tls_key_comparison(path)
            condition = path.read_text().strip().removeprefix("if (").removesuffix(") {")
            condition = condition.replace("known_evp.get()", "known_evp").replace("evp_pkey.get()", "1")
            path.write_text('''static int setup, comparison, calls;
static int EVP_PKEY_set1_RSA(int a, int b) { return setup; }
static int EVP_PKEY_cmp(int a, int b) { calls++; return comparison; }
int main(void) {
  int key = 1;
  for (int known_evp = 0; known_evp <= 1; known_evp++)
    for (setup = 0; setup <= 1; setup++)
      for (comparison = -2; comparison <= 1; comparison++) {
        calls = 0;
        int accepted = (''' + condition + ''');
        if (accepted != (known_evp && setup == 1 && comparison == 1)) return 1;
        if ((!known_evp || !setup) && calls) return 2;
      }
  return 0;
}
''')
            executable = Path(tmp) / "comparison"
            subprocess.run([compiler, str(path), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)

    def test_factory_serial_validation(self):
        with patch.object(Path, "read_bytes", return_value=b"H432B-123\0"):
            self.assertEqual(usb.serial_number(), "H432B-123")
        for value in (b"", b"a/b", b"a\nb", b"x" * 129, b"\xff"):
            with self.subTest(value=value), patch.object(Path, "read_bytes", return_value=value):
                with self.assertRaises(ValueError):
                    usb.serial_number()

    def test_existing_handoff_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            gadget = Path(tmp) / "gadget"
            gadget.mkdir()
            with patch.object(usb, "GADGET", gadget), patch.object(usb, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "already exists"):
                    usb.start()
                run.assert_not_called()

    def test_usb_failure_restores_previous_console(self):
        source = (FILES / "adb-usb.py").read_text()
        self.assertIn("except Exception:\n        clean(restore=True)", source)
        self.assertLess(source.index("'FMAdb.service')", source.index('def start')),
                        source.index("bind_when_ready(controllers[0].name)", source.index('def start')))
        self.assertIn("time.monotonic() + 10", source)
        self.assertIn("USB controller belongs to another gadget", source)

    def test_functionfs_registration_is_not_required_before_instance_creation(self):
        source = (FILES / "adb-usb.py").read_text()
        self.assertNotIn("Path('/proc/filesystems')", source)
        self.assertIn("FFS.parent.chmod(0o755)", source)

    def test_refresh_does_not_enable_disabled_usb(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(usb, "GADGET", Path(tmp) / "absent"), patch.object(usb, "run") as run:
                usb.refresh()
                run.assert_not_called()

    def test_key_changes_coordinate_functionfs_rebind(self):
        source = (FILES / "adb-keys.py").read_text()
        self.assertIn('["/usr/sbin/fm-adb-usb", "refresh"]', source)
        self.assertNotIn('"try-restart"', source)

    def test_all_aosp_components_are_commit_pinned(self):
        recipe = (RECIPE / "openh432-adbd_16.0.0.bb").read_text()
        names = set(re.findall(r";name=(\w+);", recipe))
        revisions = dict(re.findall(r'SRCREV_(\w+) = "([0-9a-f]{40})"', recipe))
        self.assertEqual(names, set(revisions))
        self.assertEqual(len(names), 6)
        self.assertNotIn("AUTOREV", recipe)

    def test_no_global_android_recovery_or_auth_bypass(self):
        cmake = (FILES / "CMakeLists.txt").read_text()
        self.assertEqual(cmake.count("COMPILE_DEFINITIONS __ANDROID_RECOVERY__"), 1)
        self.assertIn("set_source_files_properties(adb/daemon/jdwp_service.cpp", cmake)
        source = (FILES / "port-linux.py").read_text()
        self.assertNotIn("auth_required = false", source)
        self.assertIn("refusing TCP fallback", source)
        self.assertIn("getuid() == 0 || geteuid() == 0", source)
        self.assertIn('false /* don\'t follow symlinks */', source)

    def test_source_transform_rejects_missing_or_duplicate_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source"
            for text in ("missing", "anchor anchor"):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    port.replace(path, "anchor", "replacement")
                self.assertEqual(path.read_text(), text)

    def test_source_transform_preserves_surrounding_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source"
            path.write_text("before anchor after")
            port.replace(path, "anchor", "replacement")
            self.assertEqual(path.read_text(), "before replacement after")

    def test_auth_socket_requires_exact_systemd_descriptor(self):
        source = (FILES / "linux-platform.cpp").read_text()
        for guard in ("sd_listen_fds(0) != 1", "SOCK_SEQPACKET, 1",
                      '"/run/openh432-adb/auth"', "errno = EINVAL"):
            self.assertIn(guard, source)

    def test_service_is_unprivileged_and_not_enabled_by_packaging(self):
        service = (FILES / "FMAdb.service").read_text()
        for guard in ("User=openh432-adb", "NoNewPrivileges=yes",
                      "CapabilityBoundingSet=\n", "ConditionPathExists=/dev/usb-ffs/adb/ep0"):
            self.assertIn(guard, service)
        recipe = (RECIPE / "openh432-adbd_16.0.0.bb").read_text()
        self.assertIn('SYSTEMD_AUTO_ENABLE = "disable"', recipe)
        self.assertNotIn("[Install]", service)
        socket = (FILES / "FMAdbAuth.socket").read_text()
        self.assertIn("SocketMode=0600", socket)
        self.assertIn("SocketUser=root", socket)

    def test_trust_store_is_not_daemon_writable(self):
        tmpfiles = (FILES / "openh432-adbd.conf").read_text()
        self.assertIn("0750 root openh432-adb", tmpfiles)
        self.assertIn("adb_keys 0640 root openh432-adb", tmpfiles)


class AdbKeyTests(unittest.TestCase):
    def setUp(self):
        # Synthetic format vector, not a credential or private RSA key.
        modulus = (1 << 2048) - 159
        self.raw = (struct.pack("<II", 64, (-pow(modulus, -1, 1 << 32)) % (1 << 32))
                    + modulus.to_bytes(256, "little")
                    + pow(2, 4096, modulus).to_bytes(256, "little")
                    + struct.pack("<I", 65537))
        self.key = base64.b64encode(self.raw).decode()

    def test_comment_is_not_part_of_trusted_identity(self):
        self.assertEqual(keys.canonical_key(self.key + " arbitrary comment"), self.key)
        self.assertEqual(keys.canonical_key(self.key.encode()), self.key)
        digest = base64.b64encode(hashlib.sha256(self.raw).digest()).decode().rstrip("=")
        self.assertEqual(keys.fingerprint(self.key), "SHA256:" + digest)

    def test_corrupt_fields_are_rejected(self):
        for offset in (0, 4, 8, 263, 264, 520):
            corrupted = bytearray(self.raw)
            corrupted[offset] ^= 1
            with self.assertRaises(ValueError):
                keys.canonical_key(base64.b64encode(corrupted))
        for invalid in ("", "%%%", "AAAA", "x" * 4097):
            with self.assertRaises(ValueError):
                keys.canonical_key(invalid)

    def test_store_deduplicates_and_rejects_malformed_content(self):
        self.assertEqual(keys.decode_store((self.key + "\n" + self.key).encode()), [self.key])
        self.assertEqual(keys.decode_store(b""), [])
        with self.assertRaises(ValueError):
            keys.decode_store((self.key + "\ninvalid").encode())
        with self.assertRaises(ValueError):
            keys.decode_store(b"\n" * (keys.MAX_STORE + 1))

    def test_permissions_ownership_type_and_links(self):
        good = dict(st_uid=0, st_gid=123, st_mode=stat.S_IFREG | 0o640, st_nlink=1)
        keys.check_metadata(SimpleNamespace(**good), 123)
        for field, value in (("st_uid", 1000), ("st_gid", 1000), ("st_nlink", 2),
                             ("st_mode", stat.S_IFREG | 0o660),
                             ("st_mode", stat.S_IFREG | 0o644),
                             ("st_mode", stat.S_IFLNK | 0o640)):
            with self.assertRaises(ValueError):
                keys.check_metadata(SimpleNamespace(**(good | {field: value})), 123)

    def test_atomic_replacement_and_failure_preserves_prior_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adb_keys"
            path.write_text("previous\n")
            directory = os.open(tmp, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with patch.object(keys.os, "fchown"), patch.object(keys.os, "replace", side_effect=OSError):
                    with self.assertRaises(OSError):
                        keys.write_keys(directory, os.getgid(), [self.key])
                self.assertEqual(path.read_text(), "previous\n")
                self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["adb_keys"])
                with patch.object(keys.os, "fchown"):
                    keys.write_keys(directory, os.getgid(), [self.key])
                self.assertEqual(path.read_text(), self.key + "\n")
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
            finally:
                os.close(directory)

    def test_symlink_is_not_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "other").write_text(self.key)
            (Path(tmp) / "adb_keys").symlink_to("other")
            directory = os.open(tmp, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(OSError):
                    keys.read_keys(directory, os.getgid())
            finally:
                os.close(directory)


if __name__ == "__main__":
    unittest.main()
