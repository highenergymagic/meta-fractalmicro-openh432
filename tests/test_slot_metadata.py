# SPDX-License-Identifier: MIT
import importlib.util
import lzma
from pathlib import Path
import unittest

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


if __name__ == '__main__':
    unittest.main()
