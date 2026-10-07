# SPDX-License-Identifier: MIT
require openh432-reboot-test.bb
SUMMARY = "NAND slot-B kernel bundle with minimal root handoff"
do_compile[depends] = "linux-h432b-runtime:do_deploy openh432-early-b:do_image_complete"
do_compile() {
    rm -f ${B}/openh432-nand-b.img
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-runtime/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/kernel-runtime/s5pv210-hims-u2-runtime.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-early-b-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-nand-b.img
    test "$(stat -c %s ${B}/openh432-nand-b.img)" -le 16760832 || bbfatal "kernel slot capacity exceeded"
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-nand-b.img ${DEPLOYDIR}/
}
