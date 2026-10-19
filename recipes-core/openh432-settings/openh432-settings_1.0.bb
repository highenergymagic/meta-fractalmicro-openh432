# SPDX-License-Identifier: MIT
SUMMARY = "Typed appliance settings service and command-line client"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://settings-store.c file://settings-store.h file://settings-bus.h file://settingsd.c file://settings.c file://settings-test.c file://FMSettings.service file://org.fractalmicro.Settings1.conf file://org.fractalmicro.Settings1.service"
S = "${UNPACKDIR}"
DEPENDS = "systemd sqlite3"
DEPENDS:class-native = "sqlite3-native"
inherit pkgconfig systemd
BBCLASSEXTEND = "native"
SYSTEMD_SERVICE:${PN} = "FMSettings.service"
SYSTEMD_AUTO_ENABLE = "enable"
RDEPENDS:${PN}:class-target = "dbus"
FILES:${PN} += "${datadir}/dbus-1"

do_compile() {
    settings_flags=$(pkg-config --cflags --libs libsystemd sqlite3)
    bus_flags=$(pkg-config --cflags --libs libsystemd)
    ${CC} ${CFLAGS} -Wall -Wextra -Werror ${S}/settings-store.c ${S}/settingsd.c ${LDFLAGS} $settings_flags -o settingsd
    ${CC} ${CFLAGS} -Wall -Wextra -Werror ${S}/settings.c ${LDFLAGS} $bus_flags -o settings
}
do_compile:class-native() {
    settings_flags=$(pkg-config --cflags --libs sqlite3)
    ${CC} ${CFLAGS} -UNDEBUG -Wall -Wextra -Werror ${S}/settings-store.c ${S}/settings-test.c ${LDFLAGS} $settings_flags -o settings-test
    ./settings-test
}
do_install() {
    install -d ${D}${bindir} ${D}${libexecdir}/openh432 ${D}${systemd_system_unitdir}
    install -m 0755 settings ${D}${bindir}/settings
    install -m 0755 settingsd ${D}${libexecdir}/openh432/settingsd
    install -m 0644 ${S}/FMSettings.service ${D}${systemd_system_unitdir}/
    install -d ${D}${datadir}/dbus-1/system.d ${D}${datadir}/dbus-1/system-services
    install -m 0644 ${S}/org.fractalmicro.Settings1.conf ${D}${datadir}/dbus-1/system.d/
    install -m 0644 ${S}/org.fractalmicro.Settings1.service ${D}${datadir}/dbus-1/system-services/
}
do_install:class-native() {
    install -d ${D}${bindir}
    install -m 0755 settings-test ${D}${bindir}/openh432-settings-test
}
