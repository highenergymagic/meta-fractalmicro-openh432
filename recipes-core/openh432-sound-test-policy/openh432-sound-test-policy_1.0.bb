# SPDX-License-Identifier: MIT
SUMMARY = "Explicit opt-in to audible boot/shutdown tests"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
inherit allarch
RDEPENDS:${PN} = "kde3-sounds openh432-system-sounds"
do_install() {
    install -d ${D}${sysconfdir}/openh432
    touch ${D}${sysconfdir}/openh432/system-sounds.enabled
    install -d ${D}${sysconfdir}/systemd/system/multi-user.target.wants
    ln -s ${systemd_system_unitdir}/FMBootSound.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/FMBootSound.service
    ln -s ${systemd_system_unitdir}/FMShutdownSound.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/FMShutdownSound.service
}
