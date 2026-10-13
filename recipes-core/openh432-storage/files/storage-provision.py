#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Explicit internal-MMC provisioning/reset. Never used during normal boot."""
import argparse
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import uuid


def runtime():
    loader = SourceFileLoader('storage', str(Path(__file__).with_name('storage-runtime')))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def ensure_unmounted(device):
    result = json.loads(subprocess.check_output(
        ['lsblk', '--json', '--output', 'NAME,MOUNTPOINTS', device], text=True))
    def check(entry):
        if any(entry.get('mountpoints') or []):
            raise ValueError('device or child is mounted')
        for child in entry.get('children', []):
            check(child)
    for entry in result['blockdevices']:
        check(entry)
    # Device-mapper users may not be mounted. Reject any holders as well.
    for node in Path('/sys/class/block').glob(Path(device).name + '*'):
        if list((node / 'holders').iterdir()):
            raise ValueError('device has active holders')


def initialize_userdata(device, factory):
    runtime_module = runtime()
    mountpoint = Path(tempfile.mkdtemp(prefix='openh432-provision-', dir='/run'))
    mounted = False
    try:
        runtime_module.run('mount', '-t', 'btrfs', '-o', 'subvolid=5,nodev,nosuid', device, mountpoint)
        mounted = True
        for name in ('var', 'home', 'root', 'data', 'identity', 'deployments'):
            destination = mountpoint / name
            runtime_module.run('btrfs', 'subvolume', 'create', destination)
            if name in ('var', 'home', 'root') and (factory / name).is_dir():
                # Preserve numeric ownership, modes and symlinks in factory data.
                runtime_module.run('cp', '-a', str(factory / name) + '/.', destination)
        (mountpoint / 'identity').chmod(0o700)
        (mountpoint / 'deployments').chmod(0o700)
        (mountpoint / 'root').chmod(0o700)
        (mountpoint / 'data/data').mkdir(mode=0o755)
        runtime_module.durable_text(mountpoint / 'identity/machine-id', uuid.uuid4().hex + '\n')
        # Mark provisioned only after every subvolume and seed file is durable.
        runtime_module.run('sync', '-f', mountpoint)
        runtime_module.durable_text(mountpoint / 'layout-version', '1\n')
    finally:
        if mounted:
            runtime_module.run('umount', mountpoint)
        mountpoint.rmdir()


def provision(device, factory, extension=None, reset=False):
    storage = runtime()
    ensure_unmounted(device)
    if reset:
        parts = storage.validate_layout(json.loads(storage.run('sfdisk', '--json', device)))
    else:
        if extension is None or not extension.is_file():
            raise ValueError('system extension image required')
        blocks, digest, salt = storage.descriptor(factory / 'usr/lib/openh432/systemext.verity')
        # Validate payload before destroying anything. The descriptor belongs
        # to the independently verified factory root, not the supplied payload.
        storage.run('veritysetup', 'verify', '--no-superblock', '--format=1',
            '--hash=sha256', '--data-block-size=4096', '--hash-block-size=4096',
            f'--data-blocks={blocks}', f'--hash-offset={blocks * 4096}',
            f'--salt={salt}', extension, extension, digest)
        if extension.stat().st_size > 2 * storage.GIB:
            raise ValueError('extension exceeds partition capacity')
        if int(storage.run('blockdev', '--getsize64', device)) < 10 * storage.GIB:
            raise ValueError('internal storage is too small')
        table = ('label: gpt\nunit: sectors\n'
                 'start=2048,size=4194304,type=L,name=systemext_A\n'
                 'size=4194304,type=L,name=systemext_B\n'
                 'size=8388608,type=L,name=cache\n'
                 'type=L,name=userdata\n')
        subprocess.run(['sfdisk', '--wipe', 'always', '--wipe-partitions', 'always', device],
                       input=table, text=True, check=True)
        parts = storage.validate_layout(json.loads(storage.run('sfdisk', '--json', device)))
    expected = [device + 'p' + str(i) for i in range(1, 5)]
    if [p['node'] for p in parts] != expected:
        raise ValueError('unexpected partition devices')
    deadline = time.monotonic() + 10
    while not all(Path(p).is_block_device() for p in expected):
        if time.monotonic() >= deadline:
            raise ValueError('partition devices did not appear')
        time.sleep(0.1)
    if not reset:
        for partition in expected[:2]:
            with extension.open('rb') as incoming, open(partition, 'wb', buffering=0) as output:
                shutil.copyfileobj(incoming, output, 1024 * 1024)
                os.fsync(output.fileno())
            storage.run('veritysetup', 'verify', '--no-superblock', '--format=1',
                '--hash=sha256', '--data-block-size=4096', '--hash-block-size=4096',
                f'--data-blocks={blocks}', f'--hash-offset={blocks * 4096}',
                f'--salt={salt}', partition, partition, digest)
    storage.run('mkfs.f2fs', '-f', '-l', 'cache', expected[2])
    storage.run('mkfs.btrfs', '-f', '-L', 'userdata', expected[3])
    initialize_userdata(expected[3], factory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('install', 'factory-reset'))
    parser.add_argument('--factory-root', type=Path, required=True)
    parser.add_argument('--extension', type=Path)
    parser.add_argument('--confirm-erase-internal-mmc', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0 or not args.confirm_erase_internal_mmc:
        parser.error('requires root and --confirm-erase-internal-mmc')
    if Path('/run/systemd/system').exists():
        parser.error('requires initramfs recovery, not a running system')
    if not args.factory_root.is_absolute() or args.factory_root.is_symlink():
        parser.error('factory root must be an absolute real directory')
    try:
        provision(runtime().internal_device(), args.factory_root,
                  args.extension, args.operation == 'factory-reset')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Storage operation failed; remain in recovery: {error}\n')


if __name__ == '__main__':
    main()
