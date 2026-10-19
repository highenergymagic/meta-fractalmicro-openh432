#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Privileged administration of ADB public keys; never imports private keys."""
import argparse
import base64
import binascii
import fcntl
import grp
import hashlib
import os
from pathlib import Path
import secrets
import stat
import struct
import subprocess

STORE = Path("/var/lib/openh432-adb")
MAX_KEYS = 128
MAX_STORE = 128 * 1024


def canonical_key(line):
    """Validate Android's 2048-bit RSA wire key, dropping untrusted comments."""
    fields = line.split()
    if not fields or len(line) > 4096:
        raise ValueError("Expected one Android ADB public key")
    try:
        raw = base64.b64decode(fields[0], validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Invalid public-key encoding") from error
    if len(raw) != 524:
        raise ValueError("Expected a 2048-bit Android ADB public key")
    words, inverse = struct.unpack_from("<II", raw)
    modulus = int.from_bytes(raw[8:264], "little")
    rr = int.from_bytes(raw[264:520], "little")
    exponent = struct.unpack_from("<I", raw, 520)[0]
    if words != 64 or modulus.bit_length() != 2048 or modulus % 2 != 1:
        raise ValueError("Invalid RSA modulus")
    if exponent not in (3, 65537):
        raise ValueError("Unsupported RSA exponent")
    if inverse != (-pow(modulus, -1, 1 << 32)) % (1 << 32):
        raise ValueError("Invalid RSA Montgomery inverse")
    if rr != pow(2, 4096, modulus):
        raise ValueError("Invalid RSA Montgomery residue")
    return base64.b64encode(raw).decode("ascii")


def fingerprint(key):
    return "SHA256:" + base64.b64encode(hashlib.sha256(base64.b64decode(key)).digest()).decode().rstrip("=")


def decode_store(data):
    if len(data) > MAX_STORE:
        raise ValueError("Trust store is too large")
    keys = []
    for line in data.splitlines():
        if line.strip():
            key = canonical_key(line)
            if key not in keys:
                keys.append(key)
    if len(keys) > MAX_KEYS:
        raise ValueError("Too many authorized hosts")
    return keys


def check_metadata(info, gid, directory=False):
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != 0 or info.st_gid != gid:
        raise ValueError("Trust store must be root-owned with the ADB group")
    forbidden = 0o027 if directory else 0o137
    if info.st_mode & forbidden or (not directory and info.st_nlink != 1):
        raise ValueError("Unsafe trust-store permissions or hard links")


def read_keys(directory, gid):
    fd = os.open("adb_keys", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    try:
        check_metadata(os.fstat(fd), gid)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return decode_store(stream.read(MAX_STORE + 1))
    finally:
        os.close(fd)


def write_keys(directory, gid, keys):
    if len(keys) > MAX_KEYS:
        raise ValueError("Too many authorized hosts")
    data = "".join(key + "\n" for key in keys).encode("ascii")
    name = ".keys-" + secrets.token_hex(12)
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=directory)
    try:
        os.fchown(fd, 0, gid)
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        os.replace(name, "adb_keys", src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(fd)
        try:
            os.unlink(name, dir_fd=directory)
        except FileNotFoundError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    sub.add_parser("clear")
    sub.add_parser("add").add_argument("public_key", type=Path)
    sub.add_parser("fingerprint").add_argument("public_key", type=Path)
    sub.add_parser("remove").add_argument("fingerprint")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.exit(1, "Host-key administration requires root\n")
    directory = None
    try:
        if args.command == "fingerprint":
            with args.public_key.open("rb") as stream:
                data = stream.read(4097)
            if len(data.splitlines()) != 1:
                raise ValueError("Supply exactly one public key")
            print(fingerprint(canonical_key(data)))
            return
        gid = grp.getgrnam("openh432-adb").gr_gid
        directory = os.open(STORE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        check_metadata(os.fstat(directory), gid, directory=True)
        fcntl.flock(directory, fcntl.LOCK_EX)
        keys = read_keys(directory, gid)
        if args.command == "list":
            for key in keys:
                print(fingerprint(key))
            return
        if args.command == "add":
            with args.public_key.open("rb") as stream:
                data = stream.read(4097)
            if len(data.splitlines()) != 1:
                raise ValueError("Supply exactly one public key")
            key = canonical_key(data)
            if key not in keys:
                keys.append(key)
        elif args.command == "remove":
            filtered = [key for key in keys if fingerprint(key) != args.fingerprint]
            if len(filtered) == len(keys):
                raise ValueError("Unknown host fingerprint")
            keys = filtered
        else:
            keys = []
        write_keys(directory, gid, keys)
        # Revoke existing sessions as well as future authentication. This does
        # not start a disabled daemon or enable debugging.
        try:
            subprocess.run(["/usr/sbin/fm-adb-usb", "refresh"], check=True, timeout=90)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ValueError("Keys were saved, but existing ADB sessions could not be restarted") from error
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"ADB trust-store operation failed: {error}\n")
    finally:
        if directory is not None:
            os.close(directory)


if __name__ == "__main__":
    main()
