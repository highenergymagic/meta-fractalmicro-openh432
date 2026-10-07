# SPDX-License-Identifier: MIT
SUMMARY = "OpenH432 shared development userland"
LICENSE = "MIT"
inherit core-image h432b-systembase
IMAGE_INSTALL = "packagegroup-core-boot os-release systemd systemd-networkd systemd-analyze systemd-extra-utils libseccomp libacl libzstd openh432-ram-policy alsa-utils-aplay alsa-utils-amixer mtd-utils mtd-utils-ubifs coreutils"
IMAGE_FEATURES = ""
# SquashFS is the same DEBUG userland for NAND-base qualification, not a
# production root; it retains the physical USB root shell from ram-policy.
IMAGE_FSTYPES = "cpio.xz squashfs-xz"
EXTRA_IMAGECMD:squashfs-xz = "-comp xz -noappend -processors 1"
# CRC32 is supported by the kernel decoder; one compressor thread makes the
# stream independent of the build host CPU count, with an 8 MiB dictionary.
XZ_COMPRESSION_LEVEL = "-6"
XZ_INTEGRITY_CHECK = "crc32"
XZ_THREADS = "1"
XZ_MEMLIMIT = "128MiB"
IMAGE_LINGUAS = ""
IMAGE_ROOTFS_EXTRA_SPACE = "0"
REPRODUCIBLE_TIMESTAMP_ROOTFS = "${SOURCE_DATE_EPOCH}"
IMAGE_VERSION_SUFFIX = "-${SOURCE_DATE_EPOCH}"
# systemd dlopens these libraries as recommendations upstream. They are
# explicit above because the requested seccomp/ACL/Zstd features must work.
NO_RECOMMENDATIONS = "1"
# A physical root debug shell is explicit in ram-policy, not a login policy.
# A future production image MUST NOT include that package.
python check_ram_slot_size() {
    import os
    from glob import glob
    paths = glob(d.getVar('IMGDEPLOYDIR') + '/*.cpio.xz')
    if not paths:
        bb.fatal('No compressed RAM image found')
    for path in paths:
        if os.path.getsize(path) > 16 * 1024 * 1024:
            bb.fatal('RAM image exceeds the tested 16 MiB RAM52 slot: ' + path)
}
IMAGE_POSTPROCESS_COMMAND += "check_ram_slot_size; "

# This image is the final RAM root, not a transient initrd or disk installer.
python finalize_ram_root() {
    from pathlib import Path
    root = Path(d.getVar('IMAGE_ROOTFS'))
    (root / 'etc/fstab').write_text('# OpenH432 RAM development: no persistent mounts\n')
    (root / 'etc/machine-id').write_text('')
    if (root / 'etc/initrd-release').exists():
        bb.fatal('RAM development image must not enter systemd initrd switch-root mode')
    for required in ('init', 'usr/lib/os-release', 'usr/bin/systemd-analyze', 'usr/bin/systemd-run',
                     'usr/bin/systemd-repart', 'usr/bin/systemd-sysext',
                     'usr/lib/systemd/systemd-networkd', 'usr/lib/libseccomp.so.2',
                     'usr/lib/libacl.so.1', 'usr/lib/libzstd.so.1'):
        if not (root / required).is_file():
            bb.fatal('Missing RAM development component: ' + required)
}
ROOTFS_POSTPROCESS_COMMAND += "finalize_ram_root; "
