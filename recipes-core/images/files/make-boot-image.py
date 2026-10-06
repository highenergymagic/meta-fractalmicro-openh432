#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deterministic Android-v2 envelope for the H432B RAM boot contract.

This is Linux packaging, not an Android userland requirement. No USB access.
Format reference: AOSP system/tools/mkbootimg/include/bootimg/bootimg.h.
CRC32/SHA1 here identify transfers; they are not authentication/signatures.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import zlib

PAGE = 2048
LIMIT = 32 << 20


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
    args = parser.parse_args()
    # Exclusive creation avoids accidentally replacing an earlier artifact.
    data = image(args.kernel.read_bytes(), args.ramdisk.read_bytes(),
                 args.dtb.read_bytes())
    with args.output.open("xb") as stream:
        stream.write(data)
    print(f"{len(data)} bytes CRC32={zlib.crc32(data):08x} "
          f"SHA256={hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
