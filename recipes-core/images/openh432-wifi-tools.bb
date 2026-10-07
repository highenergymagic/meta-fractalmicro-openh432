# SPDX-License-Identifier: MIT
SUMMARY = "Optional wireless diagnostic userspace archive"
DESCRIPTION = "Pinned iw, libnl and signed regulatory database for wireless qualification. Not a bootable root filesystem."
LICENSE = "MIT"

inherit core-image

IMAGE_INSTALL = "iw wireless-regdb-static"
IMAGE_FEATURES = ""
IMAGE_LINGUAS = ""
IMAGE_FSTYPES = "tar.xz"
IMAGE_NAME_SUFFIX = ""
IMAGE_ROOTFS_EXTRA_SPACE = "0"
IMAGE_OVERHEAD_FACTOR = "1.0"
REPRODUCIBLE_TIMESTAMP_ROOTFS = "${SOURCE_DATE_EPOCH}"
IMAGE_VERSION_SUFFIX = "-${SOURCE_DATE_EPOCH}"
NO_RECOMMENDATIONS = "1"
XZ_COMPRESSION_LEVEL = "-6"
XZ_INTEGRITY_CHECK = "crc32"
XZ_THREADS = "1"
XZ_MEMLIMIT = "128MiB"
