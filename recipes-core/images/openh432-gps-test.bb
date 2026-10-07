# SPDX-License-Identifier: MIT
require openh432-power-test.bb
SUMMARY = "RAM-only GPS receive diagnostic with read-only storage"
do_compile[depends] = "linux-h432b-gps-test:do_deploy openh432-early-b:do_image_complete"
do_compile() {
    rm -f ${B}/openh432-gps-test.img
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-gps-test/zImage \
        --dtb ${DEPLOY_DIR_IMAGE}/kernel-gps-test/s5pv210-hims-u2-gps-test.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-early-b-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-gps-test.img
    test "$(stat -c %s ${B}/openh432-gps-test.img)" -le 16760832 || bbfatal "RAM boot capacity exceeded"
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-gps-test.img ${DEPLOYDIR}/
}
