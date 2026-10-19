# SPDX-License-Identifier: MIT
SUMMARY = "OpenH432 network ownership and persistent connection policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://20-openh432.conf file://50-openh432.service.conf file://openh432-networkmanager.conf file://50-openh432-network.rules"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "networkmanager-daemon networkmanager-wifi networkmanager-nmcli wpa-supplicant polkit systemd"
do_install() {
    install -d ${D}${libdir}/NetworkManager/conf.d ${D}${systemd_system_unitdir}/NetworkManager.service.d
    install -m 0644 ${UNPACKDIR}/20-openh432.conf ${D}${libdir}/NetworkManager/conf.d/
    install -m 0644 ${UNPACKDIR}/50-openh432.service.conf ${D}${systemd_system_unitdir}/NetworkManager.service.d/
    install -d ${D}${libdir}/tmpfiles.d ${D}${datadir}/polkit-1/rules.d
    install -m 0644 ${UNPACKDIR}/openh432-networkmanager.conf ${D}${libdir}/tmpfiles.d/
    install -m 0644 ${UNPACKDIR}/50-openh432-network.rules ${D}${datadir}/polkit-1/rules.d/
    # Only compositions selecting this package replace networkd ownership.
    install -d ${D}${sysconfdir}/systemd/system
    for unit in systemd-networkd.service systemd-networkd.socket systemd-networkd-wait-online.service NetworkManager-wait-online.service wpa_supplicant@wlan0.service; do
        ln -s /dev/null ${D}${sysconfdir}/systemd/system/$unit
    done
}
FILES:${PN} += "${libdir}/NetworkManager ${libdir}/tmpfiles.d ${datadir}/polkit-1/rules.d ${systemd_system_unitdir}"
