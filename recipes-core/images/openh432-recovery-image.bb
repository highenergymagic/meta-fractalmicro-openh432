# SPDX-License-Identifier: MIT
require openh432-boot-image.inc
SUMMARY = "Independent NAND recovery kernel and RAM filesystem"
DEPENDS += "dtc-native"
do_compile[depends] += "linux-h432b-runtime:do_deploy openh432-recovery-root:do_image_complete"
do_compile() {
    # The image writer refuses overwrites; remove only this task's prior output.
    rm -f ${B}/openh432-recovery.img
    install -m 0644 ${DEPLOY_DIR_IMAGE}/kernel-runtime/s5pv210-hims-u2-runtime.dtb ${B}/recovery.dtb
    fdtput -t s ${B}/recovery.dtb /chosen fractalmicro,recovery-v1 standalone
    python3 ${UNPACKDIR}/make-boot-image.py \
        --kernel ${DEPLOY_DIR_IMAGE}/kernel-runtime/zImage \
        --dtb ${B}/recovery.dtb \
        --ramdisk ${DEPLOY_DIR_IMAGE}/openh432-recovery-root-h432b.rootfs.cpio.xz \
        --output ${B}/openh432-recovery.img
    test "$(stat -c %s ${B}/openh432-recovery.img)" -le 33521664 || bbfatal "Recovery volume capacity exceeded"
}
do_deploy() {
    install -d ${DEPLOYDIR}
    install -m 0644 ${B}/openh432-recovery.img ${DEPLOYDIR}/
}
