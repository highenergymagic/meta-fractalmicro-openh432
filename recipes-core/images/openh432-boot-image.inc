# SPDX-License-Identifier: MIT
SUMMARY = "H432B Android-v2 boot envelope"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://make-boot-image.py"
inherit deploy
COMPATIBLE_MACHINE = "^h432b$"
PACKAGE_ARCH = "${MACHINE_ARCH}"
INHIBIT_DEFAULT_DEPS = "1"
PACKAGES = ""
do_configure[noexec] = "1"
S = "${UNPACKDIR}"
do_install[noexec] = "1"
addtask deploy after do_compile before do_build
