# SPDX-License-Identifier: MIT
SUMMARY = "Confirm healthy managed NAND boots after the local braille session starts"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://mark-good file://FMMarkBootSuccessful.service file://fw_env.config"
S = "${UNPACKDIR}"
inherit allarch systemd
RDEPENDS:${PN} = "h432b-bootstate-check libubootenv-bin openh432-braille openh432-local-console"
SYSTEMD_SERVICE:${PN} = "FMMarkBootSuccessful.service"
SYSTEMD_AUTO_ENABLE = "enable"
do_install() {
    install -d ${D}${libexecdir}/openh432 ${D}${systemd_system_unitdir} ${D}${sysconfdir}
    install -m 0755 ${UNPACKDIR}/mark-good ${D}${libexecdir}/openh432/
    install -m 0644 ${UNPACKDIR}/FMMarkBootSuccessful.service ${D}${systemd_system_unitdir}/
    install -m 0600 ${UNPACKDIR}/fw_env.config ${D}${sysconfdir}/
}
