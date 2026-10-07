# SPDX-License-Identifier: MIT
SUMMARY = "Automatic H432B Wi-Fi passive-scan interface startup"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://openh432-wifi-start file://FMWiFi.service file://20-wireless.network file://10-openh432.conf"
S = "${UNPACKDIR}"
inherit allarch systemd
RDEPENDS:${PN} = "iw wireless-regdb-static busybox wpa-supplicant wpa-supplicant-cli"
SYSTEMD_SERVICE:${PN} = "FMWiFi.service"
SYSTEMD_AUTO_ENABLE = "enable"
H432B_WIFI_COUNTRY ?= "00"
do_install() {
    install -d ${D}${libexecdir} ${D}${systemd_system_unitdir} ${D}${sysconfdir}/default
    install -d ${D}${systemd_unitdir}/network ${D}${systemd_system_unitdir}/wpa_supplicant@wlan0.service.d
    install -m 0644 ${UNPACKDIR}/20-wireless.network ${D}${systemd_unitdir}/network/
    install -m 0644 ${UNPACKDIR}/10-openh432.conf ${D}${systemd_system_unitdir}/wpa_supplicant@wlan0.service.d/
    install -m 0755 ${UNPACKDIR}/openh432-wifi-start ${D}${libexecdir}/
    install -m 0644 ${UNPACKDIR}/FMWiFi.service ${D}${systemd_system_unitdir}/
    printf 'WIFI_COUNTRY=%s\n' '${H432B_WIFI_COUNTRY}' > ${D}${sysconfdir}/default/openh432-wifi
}
CONFFILES:${PN} = "${sysconfdir}/default/openh432-wifi"

FILES:${PN} += "${systemd_unitdir}/network/20-wireless.network ${systemd_system_unitdir}/wpa_supplicant@wlan0.service.d"
