# SPDX-License-Identifier: MIT
SUMMARY = "Accessible cancellable power-button countdown"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://openh432-power-key.c file://power-gesture.h file://FMPowerKey.service file://75-h432b-power-key.rules"
S = "${UNPACKDIR}"
DEPENDS = "systemd"
RDEPENDS:${PN} = "systemd"
inherit pkgconfig systemd
SYSTEMD_SERVICE:${PN} = "FMPowerKey.service"
SYSTEMD_AUTO_ENABLE = "enable"
do_compile() {
    ${CC} ${CFLAGS} ${CPPFLAGS} -std=gnu11 -Wall -Wextra -Werror \
        ${S}/openh432-power-key.c -o ${B}/openh432-power-key \
        ${LDFLAGS} $(pkg-config --cflags --libs libsystemd)
}
do_install() {
    install -d ${D}${sbindir} ${D}${systemd_system_unitdir} ${D}${nonarch_base_libdir}/udev/rules.d
    install -m 0755 ${B}/openh432-power-key ${D}${sbindir}/
    install -m 0644 ${S}/FMPowerKey.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${S}/75-h432b-power-key.rules ${D}${nonarch_base_libdir}/udev/rules.d/
}
FILES:${PN} += "${nonarch_base_libdir}/udev/rules.d"
