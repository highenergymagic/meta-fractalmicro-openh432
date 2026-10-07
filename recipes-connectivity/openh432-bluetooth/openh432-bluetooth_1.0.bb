# SPDX-License-Identifier: MIT
SUMMARY = "H432B factory BCSP Bluetooth transport service"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://FMBluetoothTransport.service"
S = "${UNPACKDIR}"
inherit allarch systemd
RDEPENDS:${PN} = "bluez5"
SYSTEMD_SERVICE:${PN} = "FMBluetoothTransport.service"
# First hardware test is explicit; avoid repeated attachment on a failed link.
SYSTEMD_AUTO_ENABLE = "disable"
do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/FMBluetoothTransport.service ${D}${systemd_system_unitdir}/
}
