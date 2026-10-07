# SPDX-License-Identifier: MIT
require openh432-boot-image.inc
SUMMARY = "Standalone RAM recovery bundle using the runtime kernel"
do_compile[depends] += "linux-h432b-runtime:do_deploy openh432-ram-dev:do_image_complete"
do_compile() {
    # Delete only this task's own derived output so repeated tasks are valid.
    rm -f ${B}/openh432-ram-boot.img
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-runtime/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/kernel-runtime/s5pv210-hims-u2-runtime.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-ram-dev-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-ram-boot.img
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-ram-boot.img ${DEPLOYDIR}/openh432-ram-boot.img
}
