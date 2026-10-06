# SPDX-License-Identifier: MIT
SUMMARY = "Read-only slot-matched UBI root handoff"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://init"
S = "${UNPACKDIR}"
inherit allarch
RDEPENDS:${PN} = "busybox mtd-utils-ubifs"
do_install() {
    install -m 0755 ${UNPACKDIR}/init ${D}/init
}
FILES:${PN} = "/init"
