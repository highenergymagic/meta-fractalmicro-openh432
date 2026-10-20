# SPDX-License-Identifier: MIT
SUMMARY = "Independent H432B recovery RAM filesystem"
LICENSE = "MIT"
inherit core-image
IMAGE_INSTALL = "busybox base-files base-passwd openh432-recovery h432b-storage-policy"
IMAGE_FEATURES = ""
IMAGE_FSTYPES = "cpio.xz"
IMAGE_LINGUAS = ""
NO_RECOMMENDATIONS = "1"
XZ_COMPRESSION_LEVEL = "-6"
XZ_INTEGRITY_CHECK = "crc32"
XZ_THREADS = "1"
REPRODUCIBLE_TIMESTAMP_ROOTFS = "${SOURCE_DATE_EPOCH}"
IMAGE_VERSION_SUFFIX = "-${SOURCE_DATE_EPOCH}"
# Factory seeds are taken from the built immutable image, never the device.
# At runtime recovery has no dependency on either base or extension slot.
do_rootfs[depends] += "openh432-systembase-b:do_image_complete squashfs-tools-native:do_populate_sysroot"
ROOTFS_POSTPROCESS_COMMAND += "recovery_factory_seed; "
recovery_factory_seed() {
    install -d ${IMAGE_ROOTFS}/usr/share/openh432-recovery
    unsquashfs -no-progress -d ${IMAGE_ROOTFS}/usr/share/openh432-recovery/factory \
        ${DEPLOY_DIR_IMAGE}/openh432-systembase-b-h432b.rootfs.squashfs \
        var home root usr/lib/openh432/systemext.verity
    test -d ${IMAGE_ROOTFS}/usr/share/openh432-recovery/factory/var || bbfatal "Missing recovery factory seed"
    test -s ${IMAGE_ROOTFS}/usr/lib/openh432/storage-controller || bbfatal "Missing recovery board storage policy"
}
