#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble provisioned persistent storage before starting the real init.

This program never partitions or formats storage. Incomplete storage enters
the caller's recovery path. Configuration is prepared only for new releases.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

GIB = 1024 ** 3
LABELS = ('systemext_A', 'systemext_B', 'cache', 'userdata')


def run(*args):
    return subprocess.run([str(a) for a in args], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()


def validate_layout(table):
    table = table['partitiontable']
    if table.get('label') != 'gpt' or table.get('sectorsize') != 512:
        raise ValueError('expected GPT with 512-byte sectors')
    parts = table['partitions']
    if len(parts) != 4:
        raise ValueError('expected exactly four partitions')
    next_start = 2048
    for index, entry in enumerate(parts):
        if entry.get('name') != LABELS[index] or entry['start'] != next_start:
            raise ValueError('unexpected partition label or boundary')
        size = entry['size']
        if index < 3 and size != (2, 2, 4)[index] * GIB // 512:
            raise ValueError('unexpected partition size')
        if index == 3 and size < GIB // 512:
            raise ValueError('userdata needs at least 1 GiB')
        next_start += size
    if next_start - 1 > table['lastlba']:
        raise ValueError('partition exceeds usable device capacity')
    return parts


def descriptor(path):
    fields = Path(path).read_text().split()
    if len(fields) != 6 or fields[0] != '1':
        raise ValueError('invalid verity descriptor')
    _, blocks, offset, digest, salt, size = fields
    if not all(re.fullmatch('[0-9]{1,10}', n) for n in (blocks, offset, size)):
        raise ValueError('invalid verity geometry')
    blocks, offset, size = map(int, (blocks, offset, size))
    if not (0 < blocks == offset and blocks * 4096 < size <= 2 * GIB and size % 4096 == 0):
        raise ValueError('verity bounds invalid')
    if not all(re.fullmatch('[0-9a-f]{64}', n) for n in (digest, salt)):
        raise ValueError('invalid verity digest')
    return blocks, digest, salt


def internal_device():
    # Board policy is supplied by the hardware layer, not block numbering.
    controller = Path('/usr/lib/openh432/storage-controller').read_text().strip()
    if not re.fullmatch(r'[0-9a-f]+\.mmc', controller):
        raise ValueError('invalid storage controller policy')
    matches = []
    for node in Path('/sys/class/block').glob('mmcblk[0-9]*'):
        if (node / 'partition').exists():
            continue
        if controller in (node / 'device').resolve().parts:
            matches.append('/dev/' + node.name)
    if len(matches) != 1:
        raise ValueError('internal storage absent or ambiguous')
    return matches[0]


def durable_text(path, text):
    path = Path(path)
    temporary = path.with_name(path.name + '.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def deployment_module():
    # Installed executable has no .py suffix.
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader('configuration', str(Path(__file__).with_name('config-deployment')))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def activate(identity, slot):
    if os.geteuid() != 0 or not re.fullmatch('[0-9a-f]{64}', identity) or slot not in ('A', 'B'):
        raise ValueError('root, exact systembase digest and slot are required')
    # Must run before switch_root/systemd, never against a live session.
    if Path('/run/systemd/system').exists():
        raise ValueError('persistent activation requires the initramfs handoff')
    device = internal_device()
    parts = validate_layout(json.loads(run('sfdisk', '--json', device)))
    for index, part in enumerate(parts, 1):
        if part['node'] != device + 'p' + str(index):
            raise ValueError('partition node does not belong to internal device')
    cache, userdata = parts[2]['node'], parts[3]['node']
    for block, expected in ((cache, 'f2fs'), (userdata, 'btrfs')):
        if run('blkid', '-p', '-s', 'TYPE', '-o', 'value', block) != expected:
            raise ValueError('persistent filesystem type mismatch')
    store = Path('/.openh432/userdata')
    extension = Path('/.openh432/systemext')
    for directory in (store, extension, Path('/cache')):
        directory.mkdir(parents=True, exist_ok=True)
    run('mount', '-t', 'btrfs', '-o', 'subvolid=5,nodev,nosuid', userdata, store)
    # A durable provisioning marker prevents interpreting arbitrary user data
    # as an initialized installation. It is not a request to repair or erase it.
    if (store / 'layout-version').read_text() != '1\n':
        raise ValueError('userdata provisioning incomplete')
    for name in ('var', 'home', 'root', 'data', 'identity', 'deployments'):
        directory = store / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('missing or unsafe shared state directory: ' + name)
    block = parts[0 if slot == 'A' else 1]['node']
    blocks, digest, salt = descriptor('/usr/lib/openh432/systemext.verity')
    run('dmsetup', '--noudevsync', 'create', 'systemext', '--readonly', '--table',
        f'0 {blocks * 8} verity 1 {block} {block} 4096 4096 {blocks} {blocks} sha256 {digest} {salt}')
    run('dmsetup', 'mknodes', 'systemext')
    run('mount', '-t', 'erofs', '-o', 'ro,nodev,nosuid', '/dev/mapper/systemext', extension)
    if not (extension / 'usr').is_dir() or (extension / 'usr').is_symlink():
        raise ValueError('system extension has no real usr directory')
    # Bind the original usr to a stable path before covering /usr. This is a
    # read-only union, not a writable overlay or a replacement usr filesystem.
    base_usr = Path('/.openh432/base-usr')
    base_usr.mkdir(exist_ok=True)
    run('mount', '--bind', '/usr', base_usr)
    run('mount', '-t', 'overlay', '-o', f'ro,lowerdir={extension}/usr:{base_usr}', 'overlay', '/usr')
    module = deployment_module()
    destination = store / 'deployments' / identity
    if not destination.exists():
        previous = None
        last = store / 'last-good'
        if last.exists():
            old = last.read_text().strip()
            if not re.fullmatch('[0-9a-f]{64}', old):
                raise ValueError('invalid previous deployment identity')
            previous = store / 'deployments' / old
        # No userspace writers exist yet. A completed previous release stays
        # unchanged; conflicts leave this boot unacknowledged for fallback.
        module.prepare(Path('/.openh432/lower/etc'), destination, previous)
    if destination.is_symlink():
        raise ValueError('unsafe deployment path')
    metadata = json.loads((destination / 'deployment.json').read_text())
    if metadata.get('version') != 1 or metadata.get('complete') is not True:
        raise ValueError('configuration deployment incomplete')
    if (destination / 'etc').is_symlink() or not (destination / 'etc').is_dir():
        raise ValueError('unsafe configuration tree')
    run('mount', '--bind', destination / 'etc', '/etc')
    for name in ('var', 'home', 'root', 'data'):
        Path('/' + name).mkdir(exist_ok=True)
        run('mount', '--bind', store / name, '/' + name)
    run('mount', '-t', 'f2fs', '-o', 'nodev,nosuid', cache, '/cache')
    machine_id = store / 'identity/machine-id'
    if machine_id.is_symlink() or not re.fullmatch('[0-9a-f]{32}\n', machine_id.read_text()):
        raise ValueError('persistent machine identity missing or invalid')
    target = Path('/etc/machine-id')
    if target.is_symlink():
        raise ValueError('machine-id mount point must be a regular file')
    target.touch(exist_ok=True)
    run('mount', '--bind', machine_id, target)
    durable_text('/run/openh432-deployment', identity + '\n')


def check_health():
    marker = Path('/run/openh432-deployment')
    if not marker.exists():
        return  # Existing volatile installations have no deployment to commit.
    identity = marker.read_text().strip()
    if not re.fullmatch('[0-9a-f]{64}', identity):
        raise ValueError('invalid active deployment identity')
    expected = Path('/.openh432/userdata/deployments') / identity / 'etc'
    if not os.path.samefile('/etc', expected):
        raise ValueError('active configuration is not the selected deployment')
    status = run('dmsetup', 'status', 'systemext').split()
    if len(status) != 4 or status[2:] != ['verity', 'V']:
        raise ValueError('system extension is not a valid verity mapping')
    blocks, digest, salt = descriptor('/usr/lib/openh432/systemext.verity')
    table = run('dmsetup', 'table', 'systemext').split()
    if (len(table) != 13 or table[:4] != ['0', str(blocks * 8), 'verity', '1'] or
            table[6:8] != ['4096', '4096'] or
            table[8:13] != [str(blocks), str(blocks), 'sha256', digest, salt]):
        raise ValueError('system extension integrity contract differs')
    return identity


def mark_good():
    identity = check_health()
    if identity is None:
        return
    durable_text('/.openh432/userdata/last-good', identity + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    activation = commands.add_parser('activate')
    activation.add_argument('identity')
    activation.add_argument('slot', choices=('A', 'B'))
    commands.add_parser('mark-good')
    commands.add_parser('check-health')
    args = parser.parse_args()
    try:
        if args.command == 'activate':
            activate(args.identity, args.slot)
        elif args.command == 'check-health':
            check_health()
        else:
            mark_good()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Persistent storage failed: {error}\n')


if __name__ == '__main__':
    main()
