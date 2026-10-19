#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Guarded integration of pinned AOSP host adbd with Linux FunctionFS/systemd.

Changes intentionally fail on upstream drift. No cryptographic or authentication
protocol implementation is replaced. Wireless support is not enabled by this port.
"""
from pathlib import Path
import sys


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"Unexpected pinned source: {path}: {old[:70]!r}")
    path.write_text(text.replace(old, new))


def harden_tls_key_comparison(path):
    # EVP_PKEY_cmp returns negative values on errors. Only 1 means equality.
    # Keep this check correct even though this port has no wireless listener.
    replace(path, '''        EVP_PKEY_set1_RSA(known_evp.get(), key);
        if (EVP_PKEY_cmp(known_evp.get(), evp_pkey.get())) {''',
            '''        if (known_evp && EVP_PKEY_set1_RSA(known_evp.get(), key) == 1 &&
            EVP_PKEY_cmp(known_evp.get(), evp_pkey.get()) == 1) {''')


def port(root):
    harden_tls_key_comparison(root / "adb/daemon/auth.cpp")
    replace(root / "adb/proto/key_type.proto", 'syntax = "proto3";',
            'syntax = "proto3";\noption optimize_for = LITE_RUNTIME;')
    replace(root / "adb/tls/tls_connection.cpp", "#include <limits.h>",
            "#include <limits.h>\n#include <string.h>")
    # The matching private liblog is linked statically, so all of its Android
    # API-30 logging entry points are available without a platform API probe.
    logging = root / "libbase/logging.cpp"
    text = logging.read_text()
    availability = "__builtin_available(android 30, *)"
    if text.count(availability) != 9:
        raise ValueError("Unexpected libbase logging availability checks")
    logging.write_text(text.replace(availability, "true"))
    main = root / "adb/daemon/main.cpp"
    replace(main, "    umask(0);", '''    // systemd supplies the unprivileged identity and auth socket.
    if (getuid() == 0 || geteuid() == 0) {
        LOG(FATAL) << "OpenH432 adbd must run as an unprivileged account";
    }
    umask(0077);''')
    replace(main, '''#if defined(__ANDROID__)
    if (access(USB_FFS_ADB_EP0, F_OK) == 0) {''', '''    if (access(USB_FFS_ADB_EP0, F_OK) == 0) {''')
    replace(main, '''        is_usb = true;
    }
#endif''', '''        is_usb = true;
    }
    if (!is_usb) {
        LOG(FATAL) << "FunctionFS endpoint is unavailable; refusing TCP fallback";
    }''')
    text = main.read_text()
    start = text.index("    // If one of these properties is set")
    end = text.index('    LOG(INFO) << "adbd started";', start)
    main.write_text(text[:start] + "    // USB-only: no property/environment-controlled TCP listener.\n\n" + text[end:])
    usb = root / "adb/daemon/usb.cpp"
    replace(usb, '#include "daemon/property_monitor.h"', '// USB lifecycle is owned by systemd, not Android properties.')
    text = usb.read_text()
    start = text.index("    // When the device is acting as a USB host")
    end = text.index("    while (true) {", start)
    usb.write_text(text[:start] + text[end:])
    replace(usb, '''        if (android::base::GetBoolProperty(kPropertyUsbDisabled, false)) {
            VLOG(USB) << "pausing USB due to " << kPropertyUsbDisabled;
            prop_mon.Run();
            VLOG(USB) << "resuming USB";
        }
''', '')
    for name in ("adb/daemon/auth.cpp", "native/libs/adbd_auth/adbd_auth.cpp"):
        path = root / name
        replace(path, 'android_get_control_socket("adbd")', 'openh432_auth_socket("adbd")')
        replace(path, '#define TRACE_TAG AUTH' if name.startswith("adb/") else '#define ANDROID_BASE_UNIQUE_FD_DISABLE_IMPLICIT_CONVERSION',
                ('#define TRACE_TAG AUTH' if name.startswith("adb/") else '#define ANDROID_BASE_UNIQUE_FD_DISABLE_IMPLICIT_CONVERSION') + '\nextern "C" int openh432_auth_socket(const char*);')
    auth = root / "native/libs/adbd_auth/adbd_auth.cpp"
    replace(auth, '''    {"/adb_keys", true /* follow symlinks */},
    {"/data/misc/adb/adb_keys", false /* don't follow symlinks */},''',
            '''    {"/var/lib/openh432-adb/adb_keys", false /* don't follow symlinks */},''')
    replace(auth, 'PLOG(ERROR) << "adbd_auth: failed to get adbd authentication socket";',
            'PLOG(FATAL) << "adbd_auth: failed to get adbd authentication socket";')
    replace(root / "adb/daemon/shell_service.cpp", 'env["TMPDIR"] = "/data/local/tmp";',
            'env["TMPDIR"] = "/tmp";')
    # OE uses 64-bit time on 32-bit ARM. The legacy raw AIO syscall expects a
    # time32 structure, unlike libc's timespec; use the kernel time64 interface.
    aio = root / "core/libasyncio/AsyncIO.cpp"
    replace(aio, '#include <sys/syscall.h>', '#include <sys/syscall.h>\n#include <linux/time_types.h>')
    replace(aio,
            '    return syscall(__NR_io_getevents, ctx, min_nr, max_nr, events, timeout);',
            '''#if defined(__NR_io_pgetevents_time64)
    struct __kernel_timespec kernel_timeout = {};
    if (timeout) {
        kernel_timeout.tv_sec = timeout->tv_sec;
        kernel_timeout.tv_nsec = timeout->tv_nsec;
    }
    return syscall(__NR_io_pgetevents_time64, ctx, min_nr, max_nr, events,
                   timeout ? &kernel_timeout : nullptr, nullptr);
#else
    return syscall(__NR_io_getevents, ctx, min_nr, max_nr, events, timeout);
#endif''')


if __name__ == "__main__":
    port(Path(sys.argv[1]))
