#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic Android-v2 envelope for the H432B RAM boot contract.

This is Linux packaging, not an Android userland requirement. No USB access.
Format reference: AOSP system/tools/mkbootimg/include/bootimg/bootimg.h.
CRC32/SHA1 here identify transfers; they are not authentication/signatures.
"""
import argparse
import hashlib
import lzma
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zlib

PAGE = 2048
LIMIT = 32 << 20


def image_descriptors(ramdisk):
    """Read the required base and optional extension from the XZ/newc handoff."""
    decoder = lzma.LZMADecompressor(memlimit=128 << 20)
    archive = decoder.decompress(ramdisk, max_length=64 << 20)
    if not decoder.eof or decoder.unused_data:
        raise ValueError("Unbounded or trailing initramfs stream")
    offset, descriptors = 0, {}
    while offset + 110 <= len(archive):
        header = archive[offset:offset + 110]
        if header[:6] != b'070701':
            raise ValueError("Expected newc initramfs")
        mode, size, names = (int(header[a:b], 16) for a, b in
                             ((14, 22), (54, 62), (94, 102)))
        if not 1 <= names <= len(archive) - offset - 110:
            raise ValueError("Invalid archive name length")
        name = archive[offset + 110:offset + 110 + names]
        if name[-1:] != b'\0' or b'\0' in name[:-1]:
            raise ValueError("Invalid archive name")
        name = name[:-1].removeprefix(b'./')
        offset += (110 + names + 3) & ~3
        end = offset + ((size + 3) & ~3)
        if end > len(archive):
            raise ValueError("Truncated archive entry")
        if name == b'TRAILER!!!':
            if size or 'systembase' not in descriptors or any(archive[end:]):
                raise ValueError("Missing descriptor or trailing archive data")
            return descriptors
        if name in (b'etc/openh432/systembase.verity', b'etc/openh432/systemext.verity'):
            kind = name.rsplit(b'/', 1)[1].split(b'.')[0].decode('ascii')
            if kind in descriptors or mode & 0o170000 != 0o100000:
                raise ValueError("Duplicate or non-regular root descriptor")
            descriptor = archive[offset:offset + size]
            if not re.fullmatch(rb'1 [0-9]{1,6} [0-9]{1,6} [0-9a-f]{64} [0-9a-f]{64} [0-9]{1,10}\n', descriptor):
                raise ValueError("Invalid root descriptor")
            _, blocks, start, _, _, total = descriptor.split()
            limit = (200 << 20) if kind == 'systembase' else (2 << 30)
            if not 2 <= int(blocks) <= limit // 4096 or blocks != start or not 0 < int(total) <= limit:
                raise ValueError("Root descriptor geometry out of bounds")
            descriptors[kind] = descriptor
        offset = end
    raise ValueError("Missing archive trailer")


def root_descriptor(ramdisk):
    return image_descriptors(ramdisk)['systembase']


def slot_metadata(dtb, ramdisk, fdtput='fdtput'):
    """Bind each required slot image to its descriptor before activation."""
    descriptors = image_descriptors(ramdisk)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'board.dtb'
        path.write_bytes(dtb)
        for kind, descriptor in sorted(descriptors.items()):
            subprocess.run([fdtput, '-t', 's', str(path), '/chosen',
                            f'fractalmicro,{kind}-verity-v1', descriptor.decode('ascii')], check=True)
        return path.read_bytes()


def image(kernel, ramdisk, dtb):
    if not 48 <= len(kernel) <= 32 << 20:
        raise ValueError("kernel size outside RAM slot")
    if kernel[36:40] != b"\x18\x28\x6f\x01":
        raise ValueError("not an ARM zImage")
    if not 1 <= len(ramdisk) <= 16 << 20:
        raise ValueError("ramdisk size outside RAM slot")
    if not 40 <= len(dtb) <= 1 << 20 or dtb[:4] != b"\xd0\x0d\xfe\xed":
        raise ValueError("not a bounded DTB")
    if not 40 <= struct.unpack_from(">I", dtb, 4)[0] <= len(dtb):
        raise ValueError("DTB total size out of bounds")
    padded = lambda data: data + bytes(-len(data) % PAGE)
    total = PAGE + sum(len(padded(x)) for x in (kernel, ramdisk, dtb))
    if total > LIMIT:
        raise ValueError("combined image exceeds fastboot download buffer")
    header = bytearray(PAGE)
    header[:8] = b"ANDROID!"
    struct.pack_into("<10I", header, 8, len(kernel), 0x42000000,
                     len(ramdisk), 0x44400000, 0, 0, 0, PAGE, 2, 0)
    header[48:53] = b"h432b"
    sha = hashlib.sha1()
    for payload in (kernel, ramdisk, b"", b"", dtb):
        sha.update(payload)
        sha.update(struct.pack("<I", len(payload)))
    header[576:596] = sha.digest()
    struct.pack_into("<IQIIQ", header, 1632, 0, 0, 1660, len(dtb), 0x44000000)
    return bytes(header) + b"".join(padded(x) for x in (kernel, ramdisk, dtb))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("kernel", "ramdisk", "dtb", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument('--slot-metadata', action='store_true')
    parser.add_argument('--fdtput', default='fdtput')
    args = parser.parse_args()
    # Exclusive creation avoids accidentally replacing an earlier artifact.
    ramdisk, dtb = args.ramdisk.read_bytes(), args.dtb.read_bytes()
    if args.slot_metadata:
        dtb = slot_metadata(dtb, ramdisk, args.fdtput)
    data = image(args.kernel.read_bytes(), ramdisk, dtb)
    with args.output.open("xb") as stream:
        stream.write(data)
    print(f"{len(data)} bytes CRC32={zlib.crc32(data):08x} "
          f"SHA256={hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
