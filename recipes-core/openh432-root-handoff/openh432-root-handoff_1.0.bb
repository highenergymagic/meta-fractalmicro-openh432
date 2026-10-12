# SPDX-License-Identifier: MIT
SUMMARY = "Read-only slot-matched UBI root handoff"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://init file://early-sound file://verity-open file://initramfs-recovery file://start-early-sound"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "busybox coreutils mtd-utils-ubifs libdevmapper util-linux-flock"
do_install() {
    install -m 0755 ${UNPACKDIR}/init ${D}/init
    install -d ${D}${libexecdir}
    install -m 0755 ${UNPACKDIR}/early-sound ${D}${libexecdir}/openh432-early-sound
    install -m 0755 ${UNPACKDIR}/start-early-sound ${D}${libexecdir}/openh432-start-early-sound
    install -m 0755 ${UNPACKDIR}/verity-open ${D}${libexecdir}/openh432-verity-open
    install -m 0755 ${UNPACKDIR}/initramfs-recovery ${D}${libexecdir}/openh432-initramfs-recovery
}
FILES:${PN} = "/init ${libexecdir}/openh432-early-sound ${libexecdir}/openh432-start-early-sound ${libexecdir}/openh432-verity-open ${libexecdir}/openh432-initramfs-recovery"
