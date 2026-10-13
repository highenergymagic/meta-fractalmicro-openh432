# SPDX-License-Identifier: MIT
SUMMARY = "OpenH432 deployment configuration and persistent storage policy"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://config-deployment.py file://storage-layout.json file://storage-runtime.py file://storage-provision.py file://persistent-machine-id.conf file://persistent-boot-health.conf"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "python3-core python3-crypt python3-fcntl python3-json python3-io python3-netclient btrfs-tools f2fs-tools util-linux-blkid util-linux-sfdisk util-linux-lsblk util-linux-blockdev util-linux-mount util-linux-umount cryptsetup libdevmapper coreutils"
do_install() {
    install -d ${D}${libexecdir}/openh432 ${D}${datadir}/openh432
    install -m 0755 ${UNPACKDIR}/config-deployment.py ${D}${libexecdir}/openh432/config-deployment
    install -m 0755 ${UNPACKDIR}/storage-runtime.py ${D}${libexecdir}/openh432/storage-runtime
    install -m 0755 ${UNPACKDIR}/storage-provision.py ${D}${libexecdir}/openh432/storage-provision
    install -m 0644 ${UNPACKDIR}/storage-layout.json ${D}${datadir}/openh432/storage-layout.json
    install -d ${D}${systemd_system_unitdir}/systemd-machine-id-commit.service.d
    install -m 0644 ${UNPACKDIR}/persistent-machine-id.conf ${D}${systemd_system_unitdir}/systemd-machine-id-commit.service.d/
    install -d ${D}${systemd_system_unitdir}/FMMarkBootSuccessful.service.d
    install -m 0644 ${UNPACKDIR}/persistent-boot-health.conf ${D}${systemd_system_unitdir}/FMMarkBootSuccessful.service.d/
}
FILES:${PN} += "${datadir}/openh432 ${systemd_system_unitdir}"
