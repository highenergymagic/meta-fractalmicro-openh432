# SPDX-License-Identifier: MIT
SUMMARY = "H432B Android-v2 envelope for the RAM-only fastboot loader"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
SRC_URI = "file://make-boot-image.py"
inherit deploy
COMPATIBLE_MACHINE = "^h432b$"
PACKAGE_ARCH = "${MACHINE_ARCH}"
INHIBIT_DEFAULT_DEPS = "1"
PACKAGES = ""
do_configure[noexec] = "1"
do_compile[depends] += "linux-h432b:do_deploy openh432-ram-dev:do_image_complete"
do_compile() {
    # Delete only this task's own derived output so repeated tasks are valid.
    rm -f ${B}/openh432-ram-boot.img
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/s5pv210-hims-u2.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-ram-dev-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-ram-boot.img
}
do_install[noexec] = "1"
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-ram-boot.img ${DEPLOYDIR}/openh432-ram-boot.img
}
addtask deploy after do_compile before do_build
