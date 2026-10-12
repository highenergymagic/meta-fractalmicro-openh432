# SPDX-License-Identifier: MIT
SUMMARY = "Systemd runtime hardware watchdog policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://60-openh432-watchdog.conf"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "systemd"

do_install() {
    install -d ${D}${libdir}/systemd/system.conf.d
    install -m 0644 ${S}/60-openh432-watchdog.conf ${D}${libdir}/systemd/system.conf.d/
}
FILES:${PN} = "${libdir}/systemd/system.conf.d/60-openh432-watchdog.conf"
