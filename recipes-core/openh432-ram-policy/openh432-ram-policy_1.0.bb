# SPDX-License-Identifier: MIT
SUMMARY = "RAM-only systemd development policy; not production login policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://init file://serial-getty@ttyGS0.service \
    file://90-power-input-qualification.conf file://ram-guard.conf file://openh432-ram.conf file://00-openh432.preset"
S = "${UNPACKDIR}"
inherit allarch systemd
SYSTEMD_SERVICE:${PN} = "serial-getty@ttyGS0.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"
RDEPENDS:${PN} = "systemd busybox"
do_install() {
    install -d ${D}${sysconfdir}/systemd/logind.conf.d
    install -m 0644 ${UNPACKDIR}/90-power-input-qualification.conf ${D}${sysconfdir}/systemd/logind.conf.d/
    install -m 0755 ${UNPACKDIR}/init ${D}/init
    install -d ${D}${sysconfdir}/systemd/system/systemd-repart.service.d
    install -m 0644 ${UNPACKDIR}/serial-getty@ttyGS0.service ${D}${sysconfdir}/systemd/system/
    install -m 0644 ${UNPACKDIR}/ram-guard.conf ${D}${sysconfdir}/systemd/system/systemd-repart.service.d/
    install -d ${D}${sysconfdir}/systemd/journald.conf.d
    install -m 0644 ${UNPACKDIR}/openh432-ram.conf ${D}${sysconfdir}/systemd/journald.conf.d/
    install -d ${D}${systemd_unitdir}/system-preset
    install -m 0644 ${UNPACKDIR}/00-openh432.preset ${D}${systemd_unitdir}/system-preset/
    install -d ${D}${sysconfdir}/systemd/system-generators
    ln -s /dev/null ${D}${sysconfdir}/systemd/system-generators/systemd-gpt-auto-generator
}
FILES:${PN} += "/init ${systemd_unitdir}/system-preset"
