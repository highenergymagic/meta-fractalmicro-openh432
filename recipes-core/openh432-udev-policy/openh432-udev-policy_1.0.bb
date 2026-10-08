# SPDX-License-Identifier: MIT
SUMMARY = "Device coldplug policy for the H432B appliance"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://50-openh432-coldplug.conf file://50-openh432-workers.conf"
S = "${UNPACKDIR}"
COMPATIBLE_MACHINE = "^h432b$"
PACKAGE_ARCH = "${MACHINE_ARCH}"
RDEPENDS:${PN} = "udev"

do_install() {
    install -d ${D}${systemd_system_unitdir}/systemd-udev-trigger.service.d
    install -m 0644 ${UNPACKDIR}/50-openh432-coldplug.conf ${D}${systemd_system_unitdir}/systemd-udev-trigger.service.d/
    install -d ${D}${sysconfdir}/udev/udev.conf.d ${D}${sysconfdir}/udev/rules.d
    install -m 0644 ${UNPACKDIR}/50-openh432-workers.conf ${D}${sysconfdir}/udev/udev.conf.d/
    # No raw SmartMedia device exists on this board. USB readers use block rules.
    ln -s /dev/null ${D}${sysconfdir}/udev/rules.d/75-probe_mtd.rules
}

FILES:${PN} += "${systemd_system_unitdir}/systemd-udev-trigger.service.d"
