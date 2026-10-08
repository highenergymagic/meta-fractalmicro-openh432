# SPDX-License-Identifier: MIT
SUMMARY = "Power-button suspend policy for the H432B appliance"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://95-h432b-suspend.conf file://50-h432b-sleep.conf"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "systemd"
do_install() {
    install -d ${D}${sysconfdir}/systemd/logind.conf.d ${D}${sysconfdir}/systemd/sleep.conf.d
    install -m 0644 ${UNPACKDIR}/95-h432b-suspend.conf ${D}${sysconfdir}/systemd/logind.conf.d/
    install -m 0644 ${UNPACKDIR}/50-h432b-sleep.conf ${D}${sysconfdir}/systemd/sleep.conf.d/
}
