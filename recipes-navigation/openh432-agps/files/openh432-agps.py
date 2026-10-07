#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Proxy-only EPO cache and bounded MT3339 RAM aiding. No receiver flash writes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import struct
import subprocess
import tempfile
import termios
import time
import urllib.request

BASE = "https://gpsdata-proxy-openh432.highenergymagic.net/"
CACHE = Path("/var/cache/openh432-agps")
DEVICE = Path("/dev/openh432-gps")
MAX_BYTES = 276480
GPS_EPOCH = 315964800
# IERS Bulletin C72: no leap second through December 2026.
# Fail closed for aiding after this validity window; ordinary GPS still works.
OFFSET = 18
OFFSET_VALID_UNTIL = 1798761600  # 2027-01-01 UTC

def xor(data):
    value = 0
    for item in data:
        value ^= item
    return value

def clock_ready(now=None):
    now = time.time() if now is None else now
    marker = Path("/run/systemd/timesync/synchronized")
    try:
        age = now - marker.stat().st_mtime
    except OSError:
        return False
    return 0 <= age < 3600 and 1767225600 <= now < OFFSET_VALID_UNTIL

def inspect(data):
    if not data or len(data) > MAX_BYTES or len(data) % 2304:
        raise ValueError("invalid GPS-only EPO length")
    first = int.from_bytes(data[:3], "little")
    for index in range(len(data) // 72):
        record = data[index * 72:(index + 1) * 72]
        if int.from_bytes(record[:3], "little") != first + index // 32 * 6:
            raise ValueError("inconsistent EPO dates")
        if record[3] not in (0, index % 32 + 1):
            raise ValueError("invalid EPO satellite slot")
        words = struct.unpack("<18I", record)
        if xor(words[:-1]) != words[-1]:
            raise ValueError("EPO record checksum mismatch")
    return first, first + len(data) // 2304 * 6

def current_records(data, now):
    if not 1767225600 <= now < OFFSET_VALID_UNTIL:
        raise ValueError("time or leap-offset validity unavailable")
    first, end = inspect(data)
    hour = (int(now) - GPS_EPOCH + OFFSET) // 3600
    if not first <= hour < end:
        raise ValueError("EPO does not cover current time")
    start = first + ((hour-first) // 6) * 6
    # Do not begin a transfer at the edge of an expiring set.
    if start * 3600 + GPS_EPOCH - OFFSET + 21600 - now < 90:
        raise ValueError("EPO set is about to expire")
    offset = ((hour-first) // 6) * 2304
    records = [data[offset+i*72:offset+(i+1)*72] for i in range(32)]
    return [record for record in records if record[3]]

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("proxy redirect refused")

def retrieve(name, limit):
    if name not in ("EPO.DAT", "EPO.MD5"):
        raise ValueError("unexpected resource")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(BASE+name, headers={
        "User-Agent": "OpenH432-AGPS/1", "Accept": "application/octet-stream"})
    with opener.open(request, timeout=10) as response:
        if response.status != 200 or response.geturl() != BASE+name:
            raise ValueError("unexpected proxy response")
        data = response.read(limit+1)
    if len(data) > limit:
        raise ValueError("oversized proxy response")
    return data

def verify_md5(data, sidecar):
    match = re.fullmatch(rb"([0-9a-fA-F]{32})[\s\x00]*", sidecar)
    if not match or hashlib.md5(data).hexdigest() != match[1].decode().lower():
        raise ValueError("EPO companion checksum mismatch")

def refresh():
    if not clock_ready():
        print("AGPS refresh skipped: trusted current time unavailable")
        return
    error = None
    for attempt in range(2):
        try:
            data = retrieve("EPO.DAT", MAX_BYTES)
            verify_md5(data, retrieve("EPO.MD5", 1024))
            current_records(data, time.time())
            CACHE.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=CACHE, prefix=".epo-", delete=False) as tmp:
                name = tmp.name
                tmp.write(data)
                tmp.flush()
                os.fsync(tmp.fileno())
            try:
                os.chmod(name, 0o644)
                os.replace(name, CACHE/"EPO.DAT")
            finally:
                if os.path.exists(name):
                    os.unlink(name)
            print("AGPS cache refreshed and validated")
            return
        except (OSError, ValueError) as exc:
            error = exc
    raise RuntimeError("proxy refresh failed; previous cache retained") from error

def frame(body):
    return b"$"+body+b"*"+format(xor(body),"02X").encode()+b"\r\n"

def decode(line):
    match = re.fullmatch(rb"\$([^*\r\n]+)\*([0-9a-fA-F]{2})",line.strip())
    if not match or xor(match[1]) != int(match[2],16):
        return None
    return match[1].split(b",")

class Receiver:
    def __init__(self, device=DEVICE):
        self.fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self.buffer = b""
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.ioctl(self.fd, termios.TIOCEXCL)
            attrs = termios.tcgetattr(self.fd)
            attrs[0] = attrs[1] = attrs[3] = 0
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[4] = attrs[5] = termios.B9600
            attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
            termios.tcflush(self.fd, termios.TCIFLUSH)
        except Exception:
            os.close(self.fd)
            raise

    def close(self):
        try:
            fcntl.ioctl(self.fd, termios.TIOCNXCL)
        finally:
            os.close(self.fd)

    def send(self, body):
        data = frame(body)
        deadline = time.monotonic()+2
        while data:
            if time.monotonic() >= deadline:
                raise TimeoutError("GPS write timeout")
            if select.select([], [self.fd], [], 0.1)[1]:
                try:
                    data = data[os.write(self.fd,data):]
                except BlockingIOError:
                    continue

    def wait(self, predicate, timeout=2):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            while b"\n" in self.buffer:
                line,self.buffer = self.buffer.split(b"\n",1)
                fields = decode(line)
                if fields and predicate(fields):
                    return fields
            if len(self.buffer) > 8192:
                raise ValueError("GPS line too long")
            if select.select([self.fd],[],[],0.1)[0]:
                block=os.read(self.fd,4096)
                if not block:
                    raise OSError("GPS disconnected")
                self.buffer+=block
        raise TimeoutError("GPS acknowledgement timeout")

    def command(self, body, number):
        self.send(body)
        fields=self.wait(lambda f: len(f)>=3 and f[0]==b"PMTK001" and f[1]==number)
        if fields[2]!=b"3":
            raise ValueError("GPS rejected command "+number.decode())

def upload():
    if not DEVICE.exists():
        print("AGPS skipped: receiver unavailable")
        return
    if not clock_ready():
        print("AGPS skipped: trusted current time unavailable")
        return
    try:
        with (CACHE/"EPO.DAT").open("rb") as stream:
            data=stream.read(MAX_BYTES+1)
        records=current_records(data,time.time())
    except (OSError,ValueError):
        print("AGPS skipped: no valid cached data")
        return
    # Resolve hardware identity, never infer it from a tty suffix alone.
    name=DEVICE.resolve().name
    if "e2900400.serial" not in str((Path("/sys/class/tty")/name).resolve()):
        raise ValueError("unexpected GPS UART")
    if "console="+name in Path("/proc/cmdline").read_text():
        raise ValueError("refusing console UART")
    receiver=Receiver()
    try:
        receiver.send(b"PMTK605")
        ident=receiver.wait(lambda f: f[0]==b"PMTK705")
        if ident[1:4]!=[b"AXN_2.31_3339_13082100",b"5464",b"Gmm-u2p"]:
            raise ValueError("unqualified GPS firmware")
        now=time.gmtime()
        body=("PMTK740,%d,%d,%d,%d,%d,%d"%now[:6]).encode()
        receiver.command(body,b"740")
        for record in records:
            words=struct.unpack("<18I",record)
            body=("PMTK721,%X,"%record[3]+",".join("%X"%w for w in words)).encode()
            receiver.command(body,b"721")
            time.sleep(0.1)
        receiver.wait(lambda f: f[0] in (b"GPGGA",b"GPRMC"),timeout=3)
        print("AGPS RAM upload accepted: %d satellites; NMEA verified"%len(records))
    finally:
        receiver.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("refresh","upload","gpsd"))
    action=parser.parse_args().action
    try:
        if action == "refresh":
            refresh()
        else:
            with Path("/run/openh432-gps/serial.lock").open("a") as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                if action == "upload":
                    upload()
                else:
                    return subprocess.call(["/usr/sbin/gpsd","-N","-b","-s","9600",
                                            "-n",str(DEVICE)])
    except (OSError,ValueError,RuntimeError) as exc:
        # Never log raw NMEA, coordinates, device serials or downloaded data.
        print("AGPS "+action+" unavailable: "+type(exc).__name__)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
