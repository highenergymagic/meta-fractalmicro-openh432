#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local, connection-only ADB approval on a root-owned virtual console."""
import fcntl
import os
from pathlib import Path
import pwd
import re
import select
import signal
import socket
import stat
import struct
import subprocess
import termios
import time

AUTH = '/run/openh432-adb/auth'
TTY_NUMBER = 8
VT_GETSTATE = 0x5603
VT_ACTIVATE = 0x5606
MAX_PACKET = 4098
KEY_TOOL = ['/usr/sbin/fm-adb-keys']


def active_vt(fd):
    state = bytearray(6)
    fcntl.ioctl(fd, VT_GETSTATE, state, True)
    return struct.unpack('HHH', state)[0]


def fingerprint(packet):
    if not packet.startswith(b'PK') or not 2 < len(packet) <= MAX_PACKET:
        raise ValueError('Invalid ADB authorization request')
    # AOSP includes a trailing NUL in some public-key requests. Never display
    # host-supplied comments or terminal escape sequences.
    key = packet[2:].rstrip(b'\0')
    if b'\0' in key or b'\n' in key or b'\r' in key:
        raise ValueError('Invalid ADB public-key framing')
    result = subprocess.run(KEY_TOOL + ['fingerprint', '/dev/stdin'],
                            input=key, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True, timeout=10)
    value = result.stdout.decode('ascii').strip()
    if not re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}', value):
        raise ValueError('Invalid fingerprint result')
    return value


def decision(line):
    return line.strip().lower() == b'yes'


def usb_connected():
    states = list(Path('/sys/class/udc').glob('*/state'))
    return len(states) == 1 and states[0].read_text().strip() == 'configured'


def prompt(peer, identity, timeout=60):
    """Only the foreground physical VT can supply a decision; EOF denies."""
    console = os.open('/dev/tty0', os.O_RDWR | os.O_NOCTTY | os.O_CLOEXEC)
    tty = None
    saved = None
    previous = active_vt(console)
    switched = False
    try:
        tty = os.open(f'/dev/tty{TTY_NUMBER}',
                      os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC)
        info = os.fstat(tty)
        if not stat.S_ISCHR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise PermissionError('Approval terminal is not private to root')
        saved = termios.tcgetattr(tty)
        mode = termios.tcgetattr(tty)
        mode[0] |= termios.ICRNL
        mode[1] |= termios.OPOST | termios.ONLCR
        mode[3] = termios.ICANON | termios.ECHO
        termios.tcsetattr(tty, termios.TCSAFLUSH, mode)
        os.write(tty, ('\x1b[2J\x1b[HUSB debugging request\n'
                       'Allow this computer for this connection only?\n'
                       f'Key fingerprint: {identity}\n'
                       'Type yes or no, then Enter. Timeout denies access.\n').encode('ascii'))
        fcntl.ioctl(console, VT_ACTIVATE, TTY_NUMBER)
        switched = True
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if active_vt(console) != TTY_NUMBER or not usb_connected():
                return False
            readable, _, _ = select.select([tty, peer], [], [], 0.1)
            if peer in readable:
                # A closed/replaced channel or another protocol event cancels
                # this prompt; never carry a decision to a different request.
                return False
            if tty in readable:
                line = os.read(tty, 128)
                return line.endswith(b'\n') and decision(line)
        return False
    finally:
        try:
            if tty is not None:
                try:
                    os.write(tty, b'\x1b[2J\x1b[H')
                    if saved is not None:
                        termios.tcsetattr(tty, termios.TCSAFLUSH, saved)
                finally:
                    os.close(tty)
        finally:
            try:
                if switched and active_vt(console) == TTY_NUMBER and previous != TTY_NUMBER:
                    fcntl.ioctl(console, VT_ACTIVATE, previous)
            finally:
                os.close(console)


def serve(peer):
    while True:
        packet, _, flags, _ = peer.recvmsg(MAX_PACKET)
        if not packet:
            return
        if flags & socket.MSG_TRUNC:
            raise ValueError('Oversized ADB auth packet')
        if packet[:2] in (b'CK', b'DC'):
            continue
        if packet[:2] != b'PK':
            raise ValueError('Unexpected ADB auth packet')
        try:
            accepted = prompt(peer, fingerprint(packet))
        except (OSError, ValueError, subprocess.SubprocessError):
            accepted = False
        # AOSP requires exactly these two-byte replies, with no key or newline.
        peer.sendall(b'OK' if accepted else b'NO')


def stopped(signum, frame):
    raise SystemExit(0)


def main():
    if os.geteuid() != 0:
        raise PermissionError('Local approval broker requires root')
    signal.signal(signal.SIGTERM, stopped)
    signal.signal(signal.SIGINT, stopped)
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as peer:
        peer.connect(AUTH)
        _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        # The systemd-created listener belongs to root even though adbd receives
        # its descriptor. Do not accept a socket supplied by an ordinary user.
        if uid not in (0, pwd.getpwnam('openh432-adb').pw_uid):
            raise PermissionError('Unexpected ADB auth peer')
        serve(peer)


if __name__ == '__main__':
    main()
