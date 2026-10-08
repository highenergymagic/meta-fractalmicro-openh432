# SPDX-License-Identifier: MIT
SUMMARY = "Read-only slot-matched UBI root handoff"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://init file://early-sound"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "busybox coreutils mtd-utils-ubifs"
do_install() {
    install -m 0755 ${UNPACKDIR}/init ${D}/init
    install -d ${D}${libexecdir}
    install -m 0755 ${UNPACKDIR}/early-sound ${D}${libexecdir}/openh432-early-sound
}
FILES:${PN} = "/init ${libexecdir}/openh432-early-sound"
