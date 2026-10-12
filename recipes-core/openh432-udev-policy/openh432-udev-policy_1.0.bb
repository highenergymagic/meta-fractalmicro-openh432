# SPDX-License-Identifier: MIT
SUMMARY = "Device coldplug policy for the H432B appliance"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://50-openh432-coldplug.conf file://50-openh432-workers.conf \
    file://FMAccessibility.target file://FMPeripheralColdplug.service \
    file://50-accessibility-first.conf"
S = "${UNPACKDIR}"
COMPATIBLE_MACHINE = "^h432b$"
PACKAGE_ARCH = "${MACHINE_ARCH}"
RDEPENDS:${PN} = "udev"
inherit systemd
SYSTEMD_SERVICE:${PN} = "FMAccessibility.target FMPeripheralColdplug.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install() {
    install -d ${D}${systemd_system_unitdir}/systemd-udev-trigger.service.d
    install -m 0644 ${UNPACKDIR}/50-openh432-coldplug.conf ${D}${systemd_system_unitdir}/systemd-udev-trigger.service.d/
    install -d ${D}${sysconfdir}/udev/udev.conf.d ${D}${sysconfdir}/udev/rules.d
    install -m 0644 ${UNPACKDIR}/50-openh432-workers.conf ${D}${sysconfdir}/udev/udev.conf.d/
    # No raw SmartMedia device exists on this board. USB readers use block rules.
    ln -s /dev/null ${D}${sysconfdir}/udev/rules.d/75-probe_mtd.rules
    install -m 0644 ${UNPACKDIR}/FMAccessibility.target ${UNPACKDIR}/FMPeripheralColdplug.service ${D}${systemd_system_unitdir}/
    for unit in systemd-networkd.service FMRegulatory.service wpa_supplicant@wlan0.service; do
        install -d ${D}${systemd_system_unitdir}/$unit.d
        install -m 0644 ${UNPACKDIR}/50-accessibility-first.conf ${D}${systemd_system_unitdir}/$unit.d/
    done
}

FILES:${PN} += "${systemd_system_unitdir}"
