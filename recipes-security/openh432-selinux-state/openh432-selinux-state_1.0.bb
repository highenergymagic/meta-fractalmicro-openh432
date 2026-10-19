# SPDX-License-Identifier: MIT
SUMMARY = "Versioned SELinux labeling of persistent appliance state"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://label-state file://FMSELinuxState.service file://50-selinux-health.conf"
S = "${UNPACKDIR}"
inherit allarch systemd
FILES:${PN} += "${systemd_system_unitdir}/FMMarkBootSuccessful.service.d"
RDEPENDS:${PN} = "coreutils policycoreutils-setfiles refpolicy-targeted"
SYSTEMD_SERVICE:${PN} = "FMSELinuxState.service"
SYSTEMD_AUTO_ENABLE = "enable"
do_install() {
    install -d ${D}${libexecdir}/openh432 ${D}${systemd_system_unitdir}/FMMarkBootSuccessful.service.d
    install -m 0755 ${UNPACKDIR}/label-state ${D}${libexecdir}/openh432/selinux-label-state
    install -m 0644 ${UNPACKDIR}/FMSELinuxState.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${UNPACKDIR}/50-selinux-health.conf ${D}${systemd_system_unitdir}/FMMarkBootSuccessful.service.d/
}
