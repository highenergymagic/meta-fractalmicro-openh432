# SPDX-License-Identifier: MIT
SUMMARY = "H432B root handoff with RAM-resident startup cue"
LICENSE = "MIT"
inherit core-image
IMAGE_INSTALL = "busybox base-files base-passwd openh432-root-handoff openh432-system-sounds-player kde3-sounds-startup"
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
    install -d ${IMAGE_ROOTFS}/etc/openh432
    touch ${IMAGE_ROOTFS}/etc/openh432/system-sounds.enabled
    printf '%s\n' b > ${IMAGE_ROOTFS}/etc/openh432-root-slot
}
