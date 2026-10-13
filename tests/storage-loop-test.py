#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Root-required integration test. Creates its OWN disposable sparse disk.

No arbitrary device argument is accepted. Only the loop device allocated from
the newly created fixture is passed to provisioning/reset code. Test artifacts
remain on disk after completion; only mounts and the owned loop are released.
Host filesystem-tool versions are qualification inputs, not reproducible build
inputs. The regular BSP build never runs this test or accesses loop devices.
"""
import argparse
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root; only a newly created disposable image is accepted')
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    layer = Path(__file__).resolve().parents[1]
    base = Path(tempfile.mkdtemp(prefix='openh432-storage-test-', dir='/var/tmp')).resolve()
    print('Fixture:', base, flush=True)
    tools = base / 'tools'
    tools.mkdir()
    for name in ('config-deployment', 'storage-runtime', 'storage-provision'):
        shutil.copyfile(layer / 'recipes-core/openh432-storage/files' / (name + '.py'), tools / name)
    provision = load('provision_test', tools / 'storage-provision')
    storage = provision.runtime()
    config = storage.deployment_module()
    formatter = load('verity_formatter', layer / 'recipes-core/images/files/make-verity-image.py')
    factory = base / 'factory'
    for name in ('etc', 'usr/lib/openh432', 'var/lib', 'home/user', 'root'):
        (factory / name).mkdir(parents=True, exist_ok=True)
    (factory / 'etc/test.conf').write_text('vendor=1\n')
    tree = base / 'extension-tree'
    (tree / 'usr/lib/extension-release.d').mkdir(parents=True)
    (tree / 'usr/lib/extension-release.d/extension-release.openh432').write_text('ID=openh432\nSYSEXT_LEVEL=1\n')
    storage.run('mkfs.erofs', '-T', '0', '-U', '6e351382-ae8c-4a19-98de-8dfbb2f03d52', base / 'extension.erofs', tree)
    extension = base / 'extension.img'
    formatter.build(base / 'extension.erofs', extension,
                    factory / 'usr/lib/openh432/systemext.verity', 'veritysetup', 2 * storage.GIB)
    image = base / 'disk.img'
    with image.open('xb') as stream:
        stream.truncate(12 * storage.GIB)
    loop = storage.run('losetup', '--find', '--show', '--partscan', image)
    if not loop.startswith('/dev/loop'):
        raise RuntimeError('unexpected loop allocation')
    mountpoint = base / 'mounted'
    mountpoint.mkdir()
    mounted = False
    try:
        backing = storage.run('losetup', '--noheadings', '--output', 'BACK-FILE', loop)
        if Path(backing).resolve() != image:
            raise RuntimeError('loop backing file mismatch')
        provision.provision(loop, factory, extension)
        table = json.loads(storage.run('sfdisk', '--json', loop))
        storage.validate_layout(table)
        expected_hash = hashlib.sha256(extension.read_bytes()).hexdigest()
        def check_extensions():
            for number in (1, 2):
                with open(loop + 'p' + str(number), 'rb') as stream:
                    assert hashlib.sha256(stream.read(extension.stat().st_size)).hexdigest() == expected_hash
        check_extensions()
        storage.run('mount', '-t', 'btrfs', '-o', 'subvolid=5', loop + 'p4', mountpoint)
        mounted = True
        assert (mountpoint / 'layout-version').read_text() == '1\n'
        old_identity = (mountpoint / 'identity/machine-id').read_text()
        data = mountpoint / 'data/data/org.fractalmicro.reader/files/instance/settings.db'
        data.parent.mkdir(parents=True)
        data.write_bytes(b'application-owned state')
        old = mountpoint / 'deployments' / ('a' * 64)
        new = mountpoint / 'deployments' / ('b' * 64)
        config.prepare(factory / 'etc', old)
        (old / 'etc/local.conf').write_text('local=1\n')
        (factory / 'etc/test.conf').write_text('vendor=2\n')
        config.prepare(factory / 'etc', new, old)
        assert (new / 'etc/test.conf').read_text() == 'vendor=2\n'
        assert (new / 'etc/local.conf').read_text() == 'local=1\n'
        # Rollback selects the old tree; application state is not restored.
        assert (old / 'etc/test.conf').read_text() == 'vendor=1\n'
        assert data.read_bytes() == b'application-owned state'
        assert (mountpoint / 'identity/machine-id').read_text() == old_identity
        # A conflicting update cannot publish a candidate.
        (old / 'etc/test.conf').write_text('local=2\n')
        rejected = mountpoint / 'deployments' / ('c' * 64)
        try:
            config.prepare(factory / 'etc', rejected, old)
        except config.Conflict:
            pass
        else:
            raise AssertionError('conflicting configuration accepted')
        assert not rejected.exists()
        # Simulate failure before publication: no destination becomes eligible.
        real_materialize = config.materialize
        def interrupted(*args):
            real_materialize(*args)
            raise OSError('simulated interrupted staging')
        config.materialize = interrupted
        try:
            config.prepare(factory / 'etc', rejected)
        except OSError:
            pass
        finally:
            config.materialize = real_materialize
        assert not rejected.exists()
        storage.run('umount', mountpoint)
        mounted = False
        provision.provision(loop, factory, reset=True)
        check_extensions()
        assert json.loads(storage.run('sfdisk', '--json', loop)) == table
        storage.run('mount', '-t', 'btrfs', '-o', 'subvolid=5', loop + 'p4', mountpoint)
        mounted = True
        assert not data.exists() and not old.exists() and not new.exists()
        assert (mountpoint / 'layout-version').read_text() == '1\n'
        assert (mountpoint / 'identity/machine-id').read_text() != old_identity
        print('PASS: provisioning, configuration update/conflict/interruption, rollback data isolation, factory reset preserves extensions/GPT', flush=True)
    finally:
        if mounted:
            storage.run('umount', mountpoint)
        storage.run('losetup', '--detach', loop)
        print('Retained fixture:', base, flush=True)


if __name__ == '__main__':
    main()
