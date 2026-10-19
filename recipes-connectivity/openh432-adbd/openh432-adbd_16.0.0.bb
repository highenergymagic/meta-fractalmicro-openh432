# SPDX-License-Identifier: MIT
SUMMARY = "Authenticated USB ADB daemon for Linux"
DESCRIPTION = "Pinned Android 16 daemon with Linux FunctionFS and systemd integration. Not enabled automatically."
LICENSE = "Apache-2.0 & BSD-2-Clause & BSD-3-Clause & ISC & MIT & OpenSSL"
LIC_FILES_CHKSUM = "file://adb/NOTICE;md5=b8b9862d565b7b0106106ac3ea42fab6 \
                    file://boringssl/LICENSE;md5=0131a611be3a37729f61e0b26319da57"

SRC_URI = "git://android.googlesource.com/platform/packages/modules/adb;protocol=https;nobranch=1;name=adb;destsuffix=source/adb \
           git://android.googlesource.com/platform/system/libbase;protocol=https;nobranch=1;name=base;destsuffix=source/libbase \
           git://android.googlesource.com/platform/system/core;protocol=https;nobranch=1;name=core;destsuffix=source/core \
           git://android.googlesource.com/platform/system/logging;protocol=https;nobranch=1;name=logging;destsuffix=source/logging \
           git://android.googlesource.com/platform/external/boringssl;protocol=https;nobranch=1;name=ssl;destsuffix=source/boringssl \
           git://android.googlesource.com/platform/frameworks/native;protocol=https;nobranch=1;name=native;destsuffix=source/native \
           file://CMakeLists.txt;subdir=source \
           file://linux-platform.cpp;subdir=source \
           file://port-linux.py file://gcc-compat.h;subdir=source \
           file://0001-libbase-gcc-logging.patch;patchdir=libbase \
           file://0002-libbase-gcc-annotations.patch;patchdir=libbase \
           file://0003-adb-weak-ptr.patch;patchdir=adb \
           file://0004-adb-layout-check.patch;patchdir=adb \
           file://FMAdb.service file://FMAdbAuth.socket file://openh432-adbd.conf \
           file://adb-keys.py file://adb-usb.py file://adb-approval.py file://FMAdbApproval.service"
SRCREV_adb = "78f769e0904c21771cccf6e4e7b239b21800e189"
SRCREV_base = "bdf0f4db82fae78492c92a55d473aacc4e963e79"
SRCREV_core = "e9d1fa3705d7fbd0ac1c942bc4c276161bfbfed1"
SRCREV_logging = "58dac317ea08b8f275ebd01ce864acab2de30b93"
SRCREV_ssl = "1e3b727981831886a0910cd9e82d5bbee4cc7029"
SRCREV_native = "fcbde2bcff56ca1d7bec9cabf8bdca5e288bf103"
SRCREV_FORMAT = "adb_base_core_logging_ssl_native"
BB_GIT_SHALLOW = "1"
BB_GIT_SHALLOW_DEPTH = "1"
S = "${UNPACKDIR}/source"
DEPENDS = "fmt protobuf protobuf-native brotli lz4 zstd libcap systemd"
inherit cmake pkgconfig systemd useradd

USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --user-group --home-dir /var/lib/openh432-adb-shell --shell /bin/sh openh432-adb"
SYSTEMD_SERVICE:${PN} = "FMAdb.service FMAdbAuth.socket FMAdbApproval.service"
SYSTEMD_AUTO_ENABLE = "disable"
FILES:${PN} += "${nonarch_libdir}/tmpfiles.d"
RDEPENDS:${PN} += "python3-core python3-fcntl python3-unixadmin python3-crypt python3-netclient python3-json python3-terminal"

python do_patch:append() {
    import subprocess
    import sys
    subprocess.run([sys.executable, d.getVar('UNPACKDIR') + '/port-linux.py',
                    d.getVar('S')], check=True)
}

# All AOSP helper libraries are private to this executable, not system providers.
OECMAKE_TARGET_COMPILE = "adbd"
do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${B}/adbd ${D}${sbindir}/adbd
    install -m 0755 ${UNPACKDIR}/adb-keys.py ${D}${sbindir}/fm-adb-keys
    install -m 0755 ${UNPACKDIR}/adb-usb.py ${D}${sbindir}/fm-adb-usb
    install -m 0755 ${UNPACKDIR}/adb-approval.py ${D}${sbindir}/fm-adb-approval
    install -d ${D}${systemd_system_unitdir} ${D}${nonarch_libdir}/tmpfiles.d
    install -m 0644 ${UNPACKDIR}/FMAdb.service ${UNPACKDIR}/FMAdbAuth.socket ${D}${systemd_system_unitdir}/
    install -m 0644 ${UNPACKDIR}/FMAdbApproval.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${UNPACKDIR}/openh432-adbd.conf ${D}${nonarch_libdir}/tmpfiles.d/
}
