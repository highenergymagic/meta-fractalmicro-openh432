# SPDX-License-Identifier: MIT
SUMMARY = "Local offline speech service"
OPENH432_SPEECH_BACKEND ?= "rhvoice"
python () {
    if d.getVar("OPENH432_SPEECH_BACKEND") not in ("rhvoice", "openevv"):
        bb.fatal("OPENH432_SPEECH_BACKEND must be rhvoice or openevv")
}
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://FMSpeech.service file://speechd.conf file://speechd-openevv.conf file://RHVoice.conf \
 file://asound.conf file://speech-env.sh file://speech-audio"
S = "${UNPACKDIR}"
inherit allarch systemd
RDEPENDS:${PN} = "speech-dispatcher openh432-local-console alsa-utils-amixer ${@'openevv' if d.getVar('OPENH432_SPEECH_BACKEND') == 'openevv' else 'rhvoice rhvoice-slt'}"
SYSTEMD_SERVICE:${PN} = "FMSpeech.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"
do_install() {
    install -d ${D}${systemd_system_unitdir} ${D}${sysconfdir}/openh432/speech \
        ${D}${sysconfdir}/RHVoice ${D}${sysconfdir}/profile.d ${D}${libexecdir}/openh432
    install -m 0644 ${S}/FMSpeech.service ${D}${systemd_system_unitdir}/
    if [ "${OPENH432_SPEECH_BACKEND}" = openevv ]; then
        install -m 0644 ${S}/speechd-openevv.conf ${D}${sysconfdir}/openh432/speech/speechd.conf
        rmdir ${D}${sysconfdir}/RHVoice
    else
        install -m 0644 ${S}/speechd.conf ${D}${sysconfdir}/openh432/speech/
        install -m 0644 ${S}/RHVoice.conf ${D}${sysconfdir}/RHVoice/
    fi
    install -m 0644 ${S}/asound.conf ${D}${sysconfdir}/openh432/speech/
    install -m 0644 ${S}/speech-env.sh ${D}${sysconfdir}/profile.d/openh432-speech.sh
    install -m 0755 ${S}/speech-audio ${D}${libexecdir}/openh432/
}
FILES:${PN} += "${libexecdir}/openh432"
CONFFILES:${PN} = "${sysconfdir}/openh432/speech/asound.conf ${sysconfdir}/openh432/speech/speechd.conf ${@'${sysconfdir}/RHVoice/RHVoice.conf' if d.getVar('OPENH432_SPEECH_BACKEND') == 'rhvoice' else ''}"
