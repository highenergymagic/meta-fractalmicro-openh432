# SPDX-License-Identifier: MIT
SUMMARY = "H432B wired DHCP network policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://20-wired.network"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "systemd-networkd"
do_install() {
    install -d ${D}${systemd_unitdir}/network
    install -m 0644 ${UNPACKDIR}/20-wired.network ${D}${systemd_unitdir}/network/
}
FILES:${PN} += "${systemd_unitdir}/network"
