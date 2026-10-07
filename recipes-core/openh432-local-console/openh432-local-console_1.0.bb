# SPDX-License-Identifier: MIT
SUMMARY = "Single-user appliance console login policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://autologin.conf"
S = "${UNPACKDIR}"
inherit allarch useradd
RDEPENDS:${PN} = "util-linux-agetty shadow-base"
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--gid 1000 user"
# Locked password; only tty1's privileged agetty bypasses authentication.
# Explicit IDs keep ownership independent of package installation order.
USERADD_PARAM:${PN} = "--uid 1000 --gid user --create-home --home-dir /home/user --shell /bin/sh --password '!' user"
do_install() {
    install -d ${D}${systemd_system_unitdir}/getty@tty1.service.d
    install -m 0644 ${S}/autologin.conf ${D}${systemd_system_unitdir}/getty@tty1.service.d/
}
FILES:${PN} += "${systemd_system_unitdir}/getty@tty1.service.d"
