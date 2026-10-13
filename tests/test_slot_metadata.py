# SPDX-License-Identifier: MIT
import importlib.util
import lzma
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'recipes-core/images/files/make-boot-image.py'
spec = importlib.util.spec_from_file_location('boot_metadata', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SlotMetadata(unittest.TestCase):
    descriptor = b'1 2 2 ' + b'a' * 64 + b' ' + b'b' * 64 + b' 12288\n'

    @staticmethod
    def member(name, data, mode=0o100644):
        name = name.encode() + b'\0'
        fields = [0, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0]
        head = b'070701' + ''.join(f'{n:08x}' for n in fields).encode() + name
        return head + bytes(-len(head) % 4) + data + bytes(-len(data) % 4)

    def test_extract_exact_descriptor(self):
        entry = self.member('./etc/openh432/systembase.verity', self.descriptor)
        data = entry + self.member('TRAILER!!!', b'') + bytes(512)
        self.assertEqual(module.root_descriptor(lzma.compress(data)), self.descriptor)

    def test_reject_duplicate_symlink_missing_and_truncated(self):
        name = 'etc/openh432/systembase.verity'
        entry = self.member(name, self.descriptor)
        trailer = self.member('TRAILER!!!', b'')
        for archive in (entry + entry + trailer, trailer, entry,
                        entry + trailer + entry + trailer,
                        self.member(name, self.descriptor, 0o120777) + trailer,
                        entry + trailer[:-1], self.member(name, b'garbage') + trailer):
            with self.assertRaises(ValueError):
                module.root_descriptor(lzma.compress(archive))

    def test_reject_trailing_compressed_stream(self):
        data = self.member('etc/openh432/systembase.verity', self.descriptor)
        data += self.member('TRAILER!!!', b'')
        with self.assertRaises(ValueError):
            module.root_descriptor(lzma.compress(data) + b'junk')

    def test_optional_extension_and_dtb_properties(self):
        base = self.member('etc/openh432/systembase.verity', self.descriptor)
        ext = self.member('etc/openh432/systemext.verity', self.descriptor)
        trailer = self.member('TRAILER!!!', b'')
        data = lzma.compress(base + ext + trailer)
        self.assertEqual(module.image_descriptors(data),
                         dict(systembase=self.descriptor, systemext=self.descriptor))
        with patch.object(module.subprocess, 'run') as run:
            module.slot_metadata(b'dtb', data)
        self.assertEqual([call.args[0][-2] for call in run.call_args_list],
                         ['fractalmicro,systembase-verity-v1', 'fractalmicro,systemext-verity-v1'])
        for bad in (ext + ext, self.member('etc/openh432/systemext.verity', b'bad'),
                    self.member('etc/openh432/systemext.verity', self.descriptor, 0o120777)):
            with self.assertRaises(ValueError):
                module.image_descriptors(lzma.compress(base + bad + trailer))

    def test_extension_has_separate_capacity_limit(self):
        big = self.descriptor.replace(b'1 2 2', b'1 520000 520000').replace(b'12288', b'2147483648')
        trailer = self.member('TRAILER!!!', b'')
        base = self.member('etc/openh432/systembase.verity', self.descriptor)
        ext = self.member('etc/openh432/systemext.verity', big)
        self.assertEqual(module.image_descriptors(lzma.compress(base + ext + trailer))['systemext'], big)
        with self.assertRaises(ValueError):
            module.image_descriptors(lzma.compress(self.member('etc/openh432/systembase.verity', big) + trailer))


if __name__ == '__main__':
    unittest.main()
