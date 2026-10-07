# SPDX-License-Identifier: MIT
require openh432-power-test.bb
SUMMARY = "RAM-only external SD reader test with read-only storage"
do_compile[depends] = "linux-h432b-external-sd-test:do_deploy openh432-early-b:do_image_complete"
do_compile() {
    rm -f ${B}/openh432-external-sd-test.img
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-external-sd-test/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/kernel-external-sd-test/s5pv210-hims-u2-external-sd-test.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-early-b-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-external-sd-test.img
    test "$(stat -c %s ${B}/openh432-external-sd-test.img)" -le 16760832 || bbfatal "RAM boot capacity exceeded"
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-external-sd-test.img ${DEPLOYDIR}/
}
