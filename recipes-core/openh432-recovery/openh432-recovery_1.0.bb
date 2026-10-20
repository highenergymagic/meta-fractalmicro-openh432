# SPDX-License-Identifier: MIT
SUMMARY = "Standalone accessible recovery policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://recovery-init file://recovery-ui.py"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "busybox openh432-storage python3-core python3-fcntl python3-io openh432-braille-progress"
do_install() {
    install -m 0755 ${UNPACKDIR}/recovery-init ${D}/init
    install -d ${D}${libexecdir}/openh432
    install -m 0755 ${UNPACKDIR}/recovery-ui.py ${D}${libexecdir}/openh432/recovery-ui
}
FILES:${PN} = "/init ${libexecdir}/openh432/recovery-ui"
