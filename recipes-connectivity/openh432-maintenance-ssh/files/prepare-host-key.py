#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create a device-local host key once; never silently replace an existing key."""
import fcntl
import os
from pathlib import Path
import stat
import subprocess
import tempfile


def private_file(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
            stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
        raise ValueError('host-key file must be root-owned, private and regular')


def validate(path, keygen):
    private_file(path)
    subprocess.run([str(keygen), '-y', '-f', str(path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def prepare(directory, keygen):
    directory = Path(directory)
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or
            stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError('StateDirectory must be a root-owned private directory')
    key = directory / 'host_ed25519'
    lock = directory / '.host-key.lock'
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        private_file(lock)
        fcntl.flock(fd, fcntl.LOCK_EX)
        if os.path.lexists(key):
            validate(key, keygen)
            return
        with tempfile.TemporaryDirectory(prefix='.host-key-', dir=directory) as temporary:
            candidate = Path(temporary) / 'key'
            subprocess.run([str(keygen), '-t', 'ed25519', '-f', str(candidate)],
                           check=True, stdout=subprocess.DEVNULL)
            validate(candidate, keygen)
            with candidate.open('rb') as stream:
                os.fsync(stream.fileno())
            # Writers are serialized by the private lock. Publish only a
            # complete, validated, durable key into the trusted directory.
            os.replace(candidate, key)
            sync_directory(directory)
        sync_directory(directory)
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        prepare('/var/lib/openh432-ssh', Path(__file__).with_name('dropbearkey'))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'SSH host-key preparation failed: {error}') from error
