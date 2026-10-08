# SPDX-License-Identifier: MIT
SUMMARY = "Opt-in system sound lifecycle services (audio assets not included)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://FMBootSound.service file://FMShutdownSound.service file://fm-system-sound.sh"
S = "${UNPACKDIR}"
inherit allarch systemd
SYSTEMD_SERVICE:${PN} = "FMBootSound.service FMShutdownSound.service"
SYSTEMD_AUTO_ENABLE:${PN} = "disable"
PACKAGES =+ "${PN}-player"
FILES:${PN}-player = "${libexecdir}/fm-system-sound"
RDEPENDS:${PN}-player = "alsa-utils-aplay alsa-utils-amixer"
RDEPENDS:${PN} = "systemd ${PN}-player"
do_install() {
    install -d ${D}${systemd_system_unitdir} ${D}${libexecdir}
    install -m 0644 ${UNPACKDIR}/*.service ${D}${systemd_system_unitdir}/
    install -m 0755 ${UNPACKDIR}/fm-system-sound.sh ${D}${libexecdir}/fm-system-sound
}
