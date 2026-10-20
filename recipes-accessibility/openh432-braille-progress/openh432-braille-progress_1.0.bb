# SPDX-License-Identifier: MIT
SUMMARY = "Early braille progress and exclusive console handoff"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://braille-progress.c"
S = "${UNPACKDIR}"
do_compile() {
    ${CC} ${CFLAGS} ${CPPFLAGS} -Wall -Wextra -Werror \
        ${S}/braille-progress.c ${LDFLAGS} -o ${B}/braille-progress
}
do_install() {
    install -d ${D}${libexecdir}/openh432
    install -m 0755 ${B}/braille-progress ${D}${libexecdir}/openh432/braille-progress
    for unit in systemd-udev-trigger FMSpeech FMBraille; do
        install -d ${D}${systemd_system_unitdir}/$unit.service.d
    done
    printf '%s\n' '[Service]' 'ExecStartPost=-${libexecdir}/openh432/braille-progress mark "devices ready" 6' \
        > ${D}${systemd_system_unitdir}/systemd-udev-trigger.service.d/progress.conf
    printf '%s\n' '[Service]' 'ExecStartPost=-+${libexecdir}/openh432/braille-progress mark "speech ready" 7' \
        > ${D}${systemd_system_unitdir}/FMSpeech.service.d/progress.conf
    printf '%s\n' '[Service]' 'ExecStartPre=-${libexecdir}/openh432/braille-progress finish "starting braille" 8' \
        > ${D}${systemd_system_unitdir}/FMBraille.service.d/progress.conf
}
# Initramfs needs only the small writer, not systemd or its service drop-ins.
PACKAGES =+ "${PN}-policy"
FILES:${PN} = "${libexecdir}/openh432/braille-progress"
FILES:${PN}-policy = "${systemd_system_unitdir}"
RDEPENDS:${PN}-policy = "${PN}"
