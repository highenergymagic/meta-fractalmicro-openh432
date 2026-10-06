# SPDX-License-Identifier: MIT
require openh432-fastboot-ram.bb
SUMMARY = "RAM-only reboot-mode qualification image"
S = "${UNPACKDIR}"
do_compile[depends] = "linux-h432b-reboot-test:do_deploy openh432-ram-dev:do_image_complete"
do_compile() {
    rm -f ${B}/openh432-reboot-test.img
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-reboot-test/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/kernel-reboot-test/s5pv210-hims-u2-reboot-test.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-ram-dev-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-reboot-test.img
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-reboot-test.img ${DEPLOYDIR}/
}
