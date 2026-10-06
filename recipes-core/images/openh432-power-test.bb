# SPDX-License-Identifier: MIT
require openh432-nand-b.bb
SUMMARY = "RAM-only PMIC inventory kernel using installed slot-B root"
do_compile[depends] = "linux-h432b-power-test:do_deploy openh432-early-b:do_image_complete"
do_compile() {
    rm -f ${B}/openh432-power-test.img
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-power-test/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/kernel-power-test/s5pv210-hims-u2-power-test.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-early-b-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-power-test.img
    test "$(stat -c %s ${B}/openh432-power-test.img)" -le 16760832 || bbfatal "RAM boot image capacity exceeded"
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-power-test.img ${DEPLOYDIR}/
}
