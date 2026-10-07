# SPDX-License-Identifier: MIT
SUMMARY = "Internal braille console policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://FMBraille.service file://brltty.conf"
S = "${UNPACKDIR}"
inherit systemd
RDEPENDS:${PN} = "brltty"
SYSTEMD_SERVICE:${PN} = "FMBraille.service"
# The normal NAND image provides the internal braille console at startup.
SYSTEMD_AUTO_ENABLE:${PN} = "enable"
do_install() {
    install -d ${D}${systemd_system_unitdir} ${D}${sysconfdir}
    install -m 0644 ${S}/FMBraille.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${S}/brltty.conf ${D}${sysconfdir}/
}
CONFFILES:${PN} = "${sysconfdir}/brltty.conf"
