#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local Grade-1 recovery interface. Never mounts or repairs storage on entry."""
import fcntl
import glob
import os
from pathlib import Path
import select
import struct
import subprocess

LETTERS = (1, 3, 9, 25, 17, 11, 27, 19, 10, 26, 5, 7, 13,
           29, 21, 15, 31, 23, 14, 30, 37, 39, 58, 45, 61, 53)
EVENT = struct.Struct('@llHHI')
KEYS = (0x1f1, 0x1f4, 28)  # Linux KEY_BRL_DOT1, KEY_BRL_DOT4, KEY_ENTER
LABELS = ('reboot now', 'factory reset', 'wipe cache')
FACTORY = '/usr/share/openh432-recovery/factory'
PROVISION = '/usr/libexec/openh432/storage-provision'


def frame(text):
    if len(text) > 32 or any(c != ' ' and not 'a' <= c <= 'z' for c in text):
        raise ValueError('recovery text must be lowercase Grade-1 letters and spaces')
    return bytes(0 if c == ' ' else LETTERS[ord(c) - ord('a')] for c in text).ljust(32, b'\0')


def progress_frame(text, percent):
    if len(text) > 28 or not 0 <= percent <= 99:
        raise ValueError('invalid progress frame')
    result = bytearray(frame(text))
    digits = (26, 1, 3, 9, 25, 17, 11, 27, 19, 10)
    result[29:] = bytes((0x3c, digits[percent // 10], digits[percent % 10]))
    return bytes(result)


class Menu:
    def __init__(self, request='menu'):
        self.item = {'menu': 0, 'factory-reset': 1, 'wipe-cache': 2}[request]
        self.confirming = False
        self.yes = False
        self.notice = 'recovery menu'

    def label(self):
        if self.notice:
            return self.notice
        if self.confirming:
            return ('erase user data' if self.item == 1 else 'erase cache') if self.yes else 'cancel'
        return LABELS[self.item]

    def key(self, key):
        if self.notice:
            self.notice = ''
            return None
        if self.confirming:
            if key in KEYS[:2]:
                self.yes = not self.yes
            elif key == KEYS[2]:
                self.confirming = False
                action = ('factory-reset' if self.item == 1 else 'wipe-cache') if self.yes else None
                self.yes = False
                return action
        elif key == KEYS[0]:
            self.item = (self.item - 1) % len(LABELS)
        elif key == KEYS[1]:
            self.item = (self.item + 1) % len(LABELS)
        elif key == KEYS[2]:
            if self.item == 0:
                return 'reboot'
            self.confirming = True
            self.yes = False
        return None


def request_from_cmdline(text):
    values = [word.split('=', 1)[1] for word in text.split()
              if word.startswith('openh432.recovery=')]
    if not values:
        return 'menu'  # A fastboot RAM boot has no loader-added request.
    if len(values) != 1 or values[0] not in ('menu', 'factory-reset', 'wipe-cache'):
        raise ValueError('invalid recovery request')
    return values[0]


def open_keyboard():
    found = []
    try:
        for path in sorted(glob.glob('/dev/input/event*')):
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
            name = bytearray(128)
            try:
                fcntl.ioctl(fd, 0x80804506, name)  # EVIOCGNAME(128)
                if name.split(b'\0', 1)[0] == b'H432B keyboard and controls':
                    found.append(fd)
                    fd = -1
            finally:
                if fd >= 0:
                    os.close(fd)
        if len(found) != 1:
            raise OSError('board keyboard missing or ambiguous')
        fcntl.ioctl(found[0], 0x40044590, 1)  # EVIOCGRAB
        return found.pop()
    finally:
        for fd in found:
            os.close(fd)


def pressed(fd):
    bits = bytearray(96)  # Linux KEY_CNT is 768.
    fcntl.ioctl(fd, 0x80604518, bits)  # EVIOCGKEY(96)
    return {i for i in range(768) if bits[i // 8] & (1 << (i % 8))}


def perform(action, update=None):
    if action == 'reboot':
        subprocess.run(['sync'], check=True)
        subprocess.run(['reboot', '-f'], check=True)
        raise RuntimeError('reboot returned')
    if action not in ('factory-reset', 'wipe-cache'):
        raise ValueError('unsupported recovery action')
    command = [PROVISION, action, '--confirm-erase-internal-mmc']
    if action == 'factory-reset':
        command += ['--factory-root', FACTORY]
    with open('/run/openh432-recovery-operation.log', 'ab', buffering=0) as log:
        if update is None:
            subprocess.run(command, stdout=log, stderr=log, check=True)
            return
        command.append('--progress')
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=log) as child:
            for line in child.stdout:
                log.write(line)
                if line.startswith(b'OPENH432_PROGRESS '):
                    _, percent, label = line.decode('ascii').rstrip('\n').split(' ', 2)
                    update(label, int(percent))
            if child.wait():
                raise subprocess.CalledProcessError(child.returncode, command)


def main():
    if os.geteuid() != 0 or not Path('/run/openh432-recovery').is_file():
        raise RuntimeError('requires the standalone recovery environment')
    menu = Menu(request_from_cmdline(Path('/proc/cmdline').read_text()))
    display = os.open('/dev/h432b-braille', os.O_WRONLY | os.O_CLOEXEC)
    keyboard = open_keyboard()
    try:
        def show(text):
            if os.write(display, frame(text)) != 32:
                raise OSError('short braille frame')
        def update(text, percent):
            if os.write(display, progress_frame(text, percent)) != 32:
                raise OSError('short progress frame')
        show(menu.label())
        armed = not pressed(keyboard)
        dropping = False
        pending = None
        while True:
            select.select([keyboard], [], [])
            data = os.read(keyboard, EVENT.size * 32)
            if not data or len(data) % EVENT.size:
                raise OSError('invalid input stream')
            for _, _, kind, code, value in EVENT.iter_unpack(data):
                if kind == 0 and code == 3:  # SYN_DROPPED: discard until report.
                    dropping, armed, pending = True, False, None
                elif kind == 0 and code == 0:
                    down = pressed(keyboard)
                    if dropping:
                        dropping = False
                        pending = None
                    elif not down and pending is not None:
                        action = menu.key(pending)
                        pending = None
                        if action:
                            update('working please wait', 0)
                            try:
                                perform(action, update)
                                menu.notice = 'complete press enter'
                            except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError):
                                menu.notice = 'failed no automatic retry'
                            # Drop events queued during the destructive operation.
                            while select.select([keyboard], [], [], 0)[0]:
                                os.read(keyboard, EVENT.size * 32)
                            armed = False
                            down = pressed(keyboard)
                        show(menu.label())
                    if len(down) > 1:
                        pending = None
                    armed = not down
                elif kind == 1 and not dropping and value == 1:
                    pending = code if armed and code in KEYS else None
                    armed = False
    finally:
        os.close(keyboard)
        os.close(display)


if __name__ == '__main__':
    main()
