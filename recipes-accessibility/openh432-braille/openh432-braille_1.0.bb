# SPDX-License-Identifier: MIT
SUMMARY = "Internal braille console policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://FMBraille.service file://brltty.conf file://brltty-speech.conf file://brltty.prefs file://speech.conf"
S = "${UNPACKDIR}"
inherit systemd
OPENH432_SPEECH_BACKEND ?= "rhvoice"
RDEPENDS:${PN} = "brltty"
RDEPENDS:${PN}:append = "${@' openh432-speech' if d.getVar('OPENH432_SPEECH_BACKEND') == 'openevv' else ''}"
SYSTEMD_SERVICE:${PN} = "FMBraille.service"
# The normal NAND image provides the internal braille console at startup.
SYSTEMD_AUTO_ENABLE:${PN} = "enable"
do_install() {
    install -d ${D}${systemd_system_unitdir} ${D}${sysconfdir}
    install -m 0644 ${S}/FMBraille.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${S}/brltty.conf ${D}${sysconfdir}/
    if [ "${OPENH432_SPEECH_BACKEND}" = openevv ]; then
        cat ${S}/brltty-speech.conf >> ${D}${sysconfdir}/brltty.conf
        install -m 0644 ${S}/brltty.prefs ${D}${sysconfdir}/
        install -d ${D}${systemd_system_unitdir}/FMBraille.service.d
        install -m 0644 ${S}/speech.conf ${D}${systemd_system_unitdir}/FMBraille.service.d/
    fi
}
CONFFILES:${PN} = "${sysconfdir}/brltty.conf"
FILES:${PN}:append = " ${systemd_system_unitdir}/FMBraille.service.d"
