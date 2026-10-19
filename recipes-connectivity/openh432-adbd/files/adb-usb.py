#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Explicit development USB handoff; never enables debugging at boot."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pwd
import subprocess
import time

GADGET = Path('/sys/kernel/config/usb_gadget/openh432-adb')
FFS = Path('/dev/usb-ffs/adb')
SERIAL = Path('/sys/bus/gadget/drivers/g_serial')
STATE = Path('/run/openh432-adb-usb')


def run(*args, check=True):
    return subprocess.run(args, check=check, timeout=20, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def put(path, value):
    path.write_text(str(value) + '\n')


def bind_when_ready(controller):
    deadline = time.monotonic() + 10
    while not (FFS / 'ep1').exists() or not (FFS / 'ep2').exists():
        if time.monotonic() >= deadline:
            raise RuntimeError('adbd did not publish FunctionFS endpoints')
        time.sleep(0.05)
    put(GADGET / 'UDC', controller)


def refresh():
    """Revoke live sessions and reconnect only an explicitly enabled gadget."""
    if not GADGET.exists() or not (STATE / 'previous.json').exists():
        return
    if run('systemctl', 'is-active', '--quiet', 'FMAdb.service', check=False).returncode:
        return
    controllers = list(Path('/sys/class/udc').iterdir())
    if len(controllers) != 1:
        raise RuntimeError('Expected exactly one USB device controller')
    try:
        if (GADGET / 'UDC').read_text().strip():
            put(GADGET / 'UDC', '')
        run('systemctl', 'stop', 'FMAdb.service')
        run('systemctl', 'start', 'FMAdb.service')
        bind_when_ready(controllers[0].name)
        run('systemctl', 'start', 'FMAdbApproval.service')
    except Exception:
        # Fail closed: a trust change must never leave an old session alive.
        run('systemctl', 'stop', 'FMAdb.service', check=False)
        raise


def serial_number():
    raw = Path('/sys/firmware/devicetree/base/serial-number').read_bytes()
    value = raw.rstrip(b'\0').decode('ascii')
    if not value or len(value) > 128 or not all(c.isalnum() or c in '-_.' for c in value):
        raise ValueError('Missing or invalid factory serial number')
    return value


def clean(restore):
    if (GADGET / 'UDC').exists() and (GADGET / 'UDC').read_text().strip():
        put(GADGET / 'UDC', '')
    run('systemctl', 'stop', 'FMAdbApproval.service', 'FMAdb.service', 'FMAdbAuth.socket')
    if FFS.is_mount():
        run('umount', str(FFS))
    link = GADGET / 'configs/c.1/ffs.adb'
    if link.is_symlink():
        link.unlink()
    for relative in ('configs/c.1/strings/0x409', 'configs/c.1',
                     'functions/ffs.adb', 'strings/0x409'):
        path = GADGET / relative
        if path.exists():
            path.rmdir()
    if GADGET.exists():
        GADGET.rmdir()
    if restore:
        record = json.loads((STATE / 'previous.json').read_text())
        name = record['serial_device']
        if name:
            if '/' in name or name in ('.', '..') or not name.startswith('gadget.'):
                raise ValueError('Invalid saved gadget identity')
            if not (SERIAL / name).exists():
                put(SERIAL / 'bind', name)
        if record['console_active']:
            run('systemctl', 'start', 'serial-getty@ttyGS0.service')
    (STATE / 'previous.json').unlink(missing_ok=True)


def start():
    if GADGET.exists() or (STATE / 'previous.json').exists():
        raise RuntimeError('ADB handoff already exists; stop it explicitly first')
    controllers = list(Path('/sys/class/udc').iterdir())
    if len(controllers) != 1:
        raise RuntimeError('Expected exactly one USB device controller')
    identity = serial_number()
    account = pwd.getpwnam('openh432-adb')
    devices = [p.name for p in SERIAL.glob('gadget.*') if p.is_symlink()]
    if len(devices) > 1:
        raise RuntimeError('Ambiguous serial gadget binding')
    if not devices and (controllers[0] / 'function').read_text().strip():
        raise RuntimeError('USB controller belongs to another gadget')
    active = run('systemctl', 'is-active', '--quiet',
                 'serial-getty@ttyGS0.service', check=False).returncode == 0
    (STATE / 'previous.json').write_text(json.dumps({
        'serial_device': devices[0] if devices else '', 'console_active': active}))
    try:
        run('systemctl', 'stop', 'serial-getty@ttyGS0.service')
        if devices:
            put(SERIAL / 'unbind', devices[0])
        GADGET.mkdir()
        # Linux composite development identity, not a production VID allocation.
        put(GADGET / 'idVendor', '0x1d6b')
        put(GADGET / 'idProduct', '0x0104')
        put(GADGET / 'bcdUSB', '0x0200')
        strings = GADGET / 'strings/0x409'
        strings.mkdir()
        put(strings / 'manufacturer', 'Fractal Microsystems')
        put(strings / 'product', 'Braille Sense U2 (ADB development)')
        put(strings / 'serialnumber', identity)
        (GADGET / 'configs/c.1').mkdir()
        put(GADGET / 'configs/c.1/bmAttributes', '0xc0')
        put(GADGET / 'configs/c.1/MaxPower', '2')
        function = GADGET / 'functions/ffs.adb'
        # FunctionFS registers its filesystem when the first instance is
        # created, not necessarily when the kernel boots.
        function.mkdir()
        (GADGET / 'configs/c.1/ffs.adb').symlink_to(function)
        # The unprivileged daemon must traverse the parent even with our
        # restrictive umask. Endpoint access remains private to its UID.
        FFS.parent.mkdir(exist_ok=True)
        FFS.parent.chmod(0o755)
        FFS.mkdir(exist_ok=True)
        run('mount', '-t', 'functionfs', '-o',
            f'uid={account.pw_uid},gid={account.pw_gid},mode=0700', 'adb', str(FFS))
        run('systemd-tmpfiles', '--create', '/usr/lib/tmpfiles.d/openh432-adbd.conf')
        run('systemctl', 'start', 'FMAdb.service')
        bind_when_ready(controllers[0].name)
        run('systemctl', 'start', 'FMAdbApproval.service')
    except Exception:
        clean(restore=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'refresh'))
    parser.add_argument('--restore-console', action='store_true',
                        help='restore the previous development serial console on stop')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('requires root')
    if args.restore_console and args.action != 'stop':
        parser.error('--restore-console is only valid with stop')
    os.umask(0o077)
    STATE.mkdir(mode=0o700, exist_ok=True)
    with (STATE / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == 'start':
            start()
        elif args.action == 'refresh':
            refresh()
        else:
            clean(args.restore_console)


if __name__ == '__main__':
    main()
