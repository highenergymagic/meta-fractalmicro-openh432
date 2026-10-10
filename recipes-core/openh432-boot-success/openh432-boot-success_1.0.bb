# SPDX-License-Identifier: MIT
SUMMARY = "Confirm healthy managed NAND boots after the local braille session starts"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://mark-good file://FMMarkBootSuccessful.service file://FMMarkBootSuccessful.timer file://fw_env.config file://59-openh432-bootstate.rules file://59-openh432-managed-images.rules"
S = "${UNPACKDIR}"
inherit allarch systemd
# The UBI probe exclusions are also needed wherever volumes are updated,
# including the RAM recovery image, so they are a separate package.
PACKAGES =+ "${PN}-ubi-rules"
RDEPENDS:${PN} = "h432b-bootstate-check libubootenv-bin openh432-braille openh432-local-console ${PN}-ubi-rules"
SYSTEMD_SERVICE:${PN} = "FMMarkBootSuccessful.timer"
SYSTEMD_AUTO_ENABLE = "enable"
do_install() {
    install -d ${D}${libexecdir}/openh432 ${D}${systemd_system_unitdir} ${D}${sysconfdir}
    install -m 0755 ${UNPACKDIR}/mark-good ${D}${libexecdir}/openh432/
    install -m 0644 ${UNPACKDIR}/FMMarkBootSuccessful.service ${UNPACKDIR}/FMMarkBootSuccessful.timer ${D}${systemd_system_unitdir}/
    install -d ${D}${nonarch_base_libdir}/udev/rules.d
    install -m 0644 ${UNPACKDIR}/59-openh432-bootstate.rules ${UNPACKDIR}/59-openh432-managed-images.rules ${D}${nonarch_base_libdir}/udev/rules.d/
    install -m 0600 ${UNPACKDIR}/fw_env.config ${D}${sysconfdir}/
}

FILES:${PN}-ubi-rules = "${nonarch_base_libdir}/udev/rules.d/59-openh432-managed-images.rules ${nonarch_base_libdir}/udev/rules.d/59-openh432-bootstate.rules"
FILES:${PN} += "${systemd_system_unitdir}/FMMarkBootSuccessful.service"
