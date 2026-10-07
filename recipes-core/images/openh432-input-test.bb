# SPDX-License-Identifier: MIT
require openh432-nand-b.bb
SUMMARY = "RAM-only input qualification kernel using installed slot-B root"
do_compile[depends] = "linux-h432b-input-test:do_deploy openh432-early-b:do_image_complete"
do_compile() {
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-input-test/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/kernel-input-test/s5pv210-hims-u2-input-test.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-early-b-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-input-test.img
    test "$(stat -c %s ${B}/openh432-input-test.img)" -le 16760832 || bbfatal "RAM boot image capacity exceeded"
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-input-test.img ${DEPLOYDIR}/
}
