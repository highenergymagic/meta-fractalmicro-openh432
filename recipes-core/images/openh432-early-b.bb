# SPDX-License-Identifier: MIT
SUMMARY = "Minimal H432B slot-B root handoff initramfs"
LICENSE = "MIT"
inherit core-image
IMAGE_INSTALL = "busybox base-files base-passwd openh432-root-handoff"
IMAGE_FEATURES = ""
IMAGE_FSTYPES = "cpio.xz"
IMAGE_LINGUAS = ""
NO_RECOMMENDATIONS = "1"
XZ_COMPRESSION_LEVEL = "-6"
XZ_INTEGRITY_CHECK = "crc32"
XZ_THREADS = "1"
REPRODUCIBLE_TIMESTAMP_ROOTFS = "${SOURCE_DATE_EPOCH}"
IMAGE_VERSION_SUFFIX = "-${SOURCE_DATE_EPOCH}"
ROOTFS_POSTPROCESS_COMMAND += "write_early_slot; "
write_early_slot() {
    install -d ${IMAGE_ROOTFS}/etc
    printf '%s\n' b > ${IMAGE_ROOTFS}/etc/openh432-root-slot
}
