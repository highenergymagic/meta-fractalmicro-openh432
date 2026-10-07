# SPDX-License-Identifier: MIT
# Board policy replaces upstream activation, not the upstream daemon.
FILESEXTRAPATHS:prepend := "${THISDIR}/../openh432-agps/files:"
SRC_URI += "file://gpsd.service"
PACKAGECONFIG = ""
SYSTEMD_SERVICE:${PN} = "gpsd.service"
SYSTEMD_AUTO_ENABLE = "disable"
INHIBIT_UPDATERCD_BBCLASS = "1"
do_install:append() {
    install -m 0644 ${UNPACKDIR}/gpsd.service ${D}${systemd_system_unitdir}/gpsd.service
    rm -f ${D}${systemd_system_unitdir}/gpsd.socket ${D}${systemd_system_unitdir}/gpsdctl@.service
    ln -s /dev/null ${D}${systemd_system_unitdir}/gpsd.socket
    ln -s /dev/null ${D}${systemd_system_unitdir}/gpsdctl@.service
}

FILES:${PN} += "${systemd_system_unitdir}/gpsd.socket ${systemd_system_unitdir}/gpsdctl@.service"
