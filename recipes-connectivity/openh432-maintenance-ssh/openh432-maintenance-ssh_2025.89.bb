# SPDX-License-Identifier: MIT
require recipes-core/dropbear/dropbear_2025.89.bb
S = "${UNPACKDIR}/dropbear-${PV}"
SUMMARY = "Key-only opt-in OpenH432 maintenance SSH"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:${COREBASE}/meta/recipes-core/dropbear/dropbear:"
SRC_URI += "file://FMRemoteAccess.service"
PACKAGECONFIG = ""
RPROVIDES:${PN} = ""
RCONFLICTS:${PN} = "dropbear openssh-sshd"
ALTERNATIVE:${PN} = ""
INHIBIT_UPDATERCD_BBCLASS = "1"
SYSTEMD_SERVICE:${PN} = "FMRemoteAccess.service"
SYSTEMD_AUTO_ENABLE = "enable"
SBINCOMMANDS = "dropbear dropbearkey"
BINCOMMANDS = ""
inherit deploy
do_install() {
    install -d ${D}${libexecdir}/openh432-ssh ${D}${systemd_system_unitdir}
    install -m 0755 ${B}/dropbearmulti ${D}${libexecdir}/openh432-ssh/
    ln -s dropbearmulti ${D}${libexecdir}/openh432-ssh/dropbear
    ln -s dropbearmulti ${D}${libexecdir}/openh432-ssh/dropbearkey
    install -m 0644 ${UNPACKDIR}/FMRemoteAccess.service ${D}${systemd_system_unitdir}/
    sed -i -e 's,@LIBEXECDIR@,${libexecdir},g' ${D}${systemd_system_unitdir}/FMRemoteAccess.service
}
FILES:${PN} = "${libexecdir}/openh432-ssh ${systemd_system_unitdir}/FMRemoteAccess.service"
pkg_postrm:${PN} () {
    :
}
# Non-secret runtime payload for volatile-overlay hardware qualification.
# Dependencies still come from the pinned target sysroot/base image.
do_deploy() {
    install -d ${DEPLOYDIR}
    tar --sort=name --mtime=@${SOURCE_DATE_EPOCH} --owner=0 --group=0 --numeric-owner \
        -cf ${DEPLOYDIR}/openh432-maintenance-ssh.tar -C ${D} .
}
addtask deploy after do_install before do_build
