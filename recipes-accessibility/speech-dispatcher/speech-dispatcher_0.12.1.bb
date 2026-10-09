# SPDX-License-Identifier: MIT
SUMMARY = "Local speech synthesis dispatcher and SSIP client"
HOMEPAGE = "https://freebsoft.org/speechd"
LICENSE = "GPL-2.0-or-later & GPL-3.0-or-later & LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://COPYING.GPL-2;md5=b234ee4d69f5fce4486a80fdaf4a4263 file://COPYING.GPL-3;md5=d32239bcb673463ab874e80d47fae504 file://COPYING.LGPL;md5=4fbd65380cdd255951079008b364516c"
SRC_URI = "git://github.com/brailcom/speechd.git;protocol=https;nobranch=1 file://0001-say-build-header.patch file://0002-preserve-linker-flags.patch file://0003-alsa-overlap-units.patch file://0004-explicit-appliance-modules.patch file://0005-bounded-alsa-stream-buffer.patch"
SRCREV = "6781ff1709eca1c3d7f748e5361a6aa157dd5f18"
DEPENDS = "glib-2.0 dotconf libsndfile1 alsa-lib systemd"
inherit autotools pkgconfig gettext
EXTRA_OECONF = "--disable-doc --disable-python --disable-ltdl \
 --without-espeak --without-espeak-ng --without-flite --without-ibmtts \
 --without-voxin --without-ivona --without-pico --without-baratinoo --without-kali \
 --without-pulse --without-libao --without-pipewire --without-oss --without-nas \
 --with-alsa --with-default-audio-method=alsa \
 --with-module-bindir=${libexecdir}/speech-dispatcher \
 --with-systemdsystemunitdir=${systemd_system_unitdir} \
 --without-systemduserunitdir"
do_install:append() {
    # The appliance policy provides one unprivileged, Unix-socket-only service.
    rm -f ${D}${systemd_system_unitdir}/speech-dispatcherd.service
    rmdir ${D}${systemd_system_unitdir} ${D}${systemd_unitdir}
}
FILES:${PN} += "${libdir}/speech-dispatcher ${datadir}/speech-dispatcher"
