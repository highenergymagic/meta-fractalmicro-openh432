# SPDX-License-Identifier: MIT
SUMMARY = "OpenH432 proxy-only EPO cache and optional RAM host aiding"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
FILESEXTRAPATHS:prepend := "${THISDIR}/../../tests:"
SRC_URI = "file://test_agps.py file://openh432-agps.py file://agps-data-refresh.service file://agps-data-refresh.timer file://agps-data-upload.service file://FMGPSStart.timer file://gpsd.service file://70-openh432-gps.rules"
S = "${UNPACKDIR}"
inherit allarch systemd useradd python3native
USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "--system --no-create-home --home / --shell /sbin/nologin --user-group openh432-gps"
SYSTEMD_SERVICE:${PN} = "agps-data-refresh.timer FMGPSStart.timer"
SYSTEMD_AUTO_ENABLE = "enable"
RDEPENDS:${PN} = "gpsd ca-certificates python3-core python3-netclient python3-crypt python3-fcntl python3-terminal python3-json"
do_compile() {
    ${PYTHON} ${UNPACKDIR}/test_agps.py
}
do_install() {
    install -d ${D}${libexecdir} ${D}${systemd_system_unitdir} ${D}${nonarch_base_libdir}/udev/rules.d
    install -m 0755 ${UNPACKDIR}/openh432-agps.py ${D}${libexecdir}/openh432-agps
    for unit in FMGPSStart.timer agps-data-refresh.service agps-data-refresh.timer agps-data-upload.service; do
        install -m 0644 ${UNPACKDIR}/$unit ${D}${systemd_system_unitdir}/
    done
    install -m 0644 ${UNPACKDIR}/70-openh432-gps.rules ${D}${nonarch_base_libdir}/udev/rules.d/
}
FILES:${PN} += "${systemd_system_unitdir} ${nonarch_base_libdir}/udev/rules.d"
