# SPDX-License-Identifier: MIT
import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest

PATH = Path(__file__).resolve().parents[1] / "recipes-core/images/files/make-boot-image.py"
spec = importlib.util.spec_from_file_location("boot_image", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BootImage(unittest.TestCase):
    def setUp(self):
        self.kernel = bytearray(48)
        self.kernel[36:40] = b"\x18\x28\x6f\x01"
        self.dtb = struct.pack(">II", 0xd00dfeed, 40) + bytes(32)

    def test_layout_and_determinism(self):
        a = module.image(self.kernel, b"ramdisk", self.dtb)
        self.assertEqual(a, module.image(self.kernel, b"ramdisk", self.dtb))
        self.assertEqual(len(a), 8192)
        self.assertEqual(a[:8], b"ANDROID!")
        self.assertEqual(struct.unpack_from("<I", a, 40)[0], 2)
        self.assertEqual(struct.unpack_from("<I", a, 1644)[0], 1660)
        self.assertEqual(a[2048:2096], self.kernel)
        self.assertEqual(a[4096:4103], b"ramdisk")
        self.assertEqual(a[6144:6184], self.dtb)
        sha = hashlib.sha1()
        for p in (self.kernel, b"ramdisk", b"", b"", self.dtb):
            sha.update(p)
            sha.update(struct.pack("<I", len(p)))
        self.assertEqual(a[576:596], sha.digest())

    def test_rejects_bad_headers(self):
        with self.assertRaises(ValueError):
            module.image(bytes(48), b"x", self.dtb)
        with self.assertRaises(ValueError):
            module.image(self.kernel, b"x", bytes(40))
        with self.assertRaises(ValueError):
            module.image(self.kernel, b"", self.dtb)

    def test_rejects_oversize_and_truncated_dtb(self):
        with self.assertRaises(ValueError):
            module.image(self.kernel, bytes((16 << 20) + 1), self.dtb)
        with self.assertRaises(ValueError):
            module.image(self.kernel, b"x", struct.pack(">II", 0xd00dfeed, 41) + bytes(32))


if __name__ == "__main__":
    unittest.main()
