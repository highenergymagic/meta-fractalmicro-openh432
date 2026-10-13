#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Append a deterministic dm-verity v1 SHA-256 tree to a filesystem image."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BLOCK = 4096
LIMIT = 200 * 1024 * 1024


def run(tool, *args, check=True):
    result = subprocess.run([str(tool), *map(str, args)], check=False,
                            capture_output=True, text=True,
                            env=dict(os.environ, LC_ALL="C"))
    if check and result.returncode:
        raise RuntimeError(f"veritysetup failed ({result.returncode}):\n"
                           + result.stdout + result.stderr)
    return result


def verify(tool, image, blocks, root, salt, check=True):
    return run(tool, "verify", "--no-superblock", "--format=1", "--hash=sha256",
               "--data-block-size=4096", "--hash-block-size=4096",
               f"--data-blocks={blocks}", f"--hash-offset={blocks * BLOCK}",
               f"--salt={salt}", image, image, root, check=check)


def build(source, output, descriptor, tool, capacity=LIMIT):
    source, output, descriptor = map(Path, (source, output, descriptor))
    size = source.stat().st_size
    if not 0 < capacity <= 2 * 1024 * 1024 * 1024:
        raise ValueError("Invalid image capacity")
    if not 0 < size <= capacity:
        raise ValueError("Systembase is empty or exceeds volume capacity")
    if len({p.resolve() for p in (source, output, descriptor)}) != 3:
        raise ValueError("Input, output and descriptor must be different files")
    # Even an empty extension needs an explicit hash-tree block. A one-block
    # payload otherwise produces no tree, unlike the normal mount contract.
    blocks = max(2, (size + BLOCK - 1) // BLOCK)
    # Deterministic, image-specific salt; neither UUIDs nor random host state
    # enter the format. The root hash is integrity metadata, not a signature.
    with source.open("rb") as stream:
        salt = hashlib.file_digest(stream, "sha256").hexdigest()
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        data, tree = Path(directory) / "data", Path(directory) / "hashes"
        shutil.copyfile(source, data)
        with data.open("ab") as stream:
            stream.write(bytes(blocks * BLOCK - size))
        result = run(tool, "format", "--no-superblock", "--format=1",
                     "--hash=sha256", "--data-block-size=4096",
                     "--hash-block-size=4096", f"--salt={salt}", data, tree)
        match = re.search(r"^Root hash:\s*([0-9a-f]{64})\s*$", result.stdout, re.M)
        if not match:
            raise ValueError("veritysetup did not report a SHA-256 root hash")
        root = match[1]
        total = data.stat().st_size + tree.stat().st_size
        if total > capacity:
            raise ValueError("Systembase plus hash tree exceeds volume capacity")
        with data.open("ab") as stream, tree.open("rb") as hashes:
            shutil.copyfileobj(hashes, stream)
        verify(tool, data, blocks, root, salt)
        # Publish only after a complete userspace verification of the tree.
        os.replace(data, output)
        descriptor.write_text(f"1 {blocks} {blocks} {root} {salt} {total}\n", encoding="ascii")
    return blocks, root, salt


def self_test(tool):
    """Exercise the pinned verifier without loop devices or kernel access."""
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        source, output, meta = (base / n for n in ("source", "image", "metadata"))
        # Multiple hash levels, with a non-aligned source tail.
        source.write_bytes(bytes(range(256)) * (129 * 16) + b"tail")
        values = build(source, output, meta, tool)
        first, metadata = output.read_bytes(), meta.read_bytes()
        build(source, output, meta, tool)
        assert output.read_bytes() == first and meta.read_bytes() == metadata
        for offset in (0, BLOCK * 128, values[0] * BLOCK):
            damaged = bytearray(first)
            damaged[offset] ^= 1
            output.write_bytes(damaged)
            assert verify(tool, output, *values, check=False).returncode != 0
        output.write_bytes(first)
        bad_root = ("0" if values[1][0] != "0" else "1") + values[1][1:]
        assert verify(tool, output, values[0], bad_root, values[2], check=False).returncode != 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("descriptor", type=Path)
    parser.add_argument("--veritysetup", default="veritysetup")
    parser.add_argument("--capacity", type=int, default=LIMIT)
    args = parser.parse_args()
    self_test(args.veritysetup)
    build(args.source, args.output, args.descriptor, args.veritysetup, args.capacity)


if __name__ == "__main__":
    main()
