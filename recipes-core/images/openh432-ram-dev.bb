# SPDX-License-Identifier: MIT
SUMMARY = "OpenH432 RAM-only systemd hardware-development image"
LICENSE = "MIT"
inherit core-image
IMAGE_INSTALL = "packagegroup-core-boot systemd systemd-networkd openh432-ram-policy alsa-utils-aplay alsa-utils-amixer"
IMAGE_FEATURES = ""
IMAGE_FSTYPES = "cpio.gz"
IMAGE_LINGUAS = ""
IMAGE_ROOTFS_EXTRA_SPACE = "0"
NO_RECOMMENDATIONS = "1"
# A physical root debug shell is explicit in ram-policy, not a login policy.
# A future production image MUST NOT include that package.
python check_ram_slot_size() {
    import os
    from glob import glob
    paths = glob(d.getVar('IMGDEPLOYDIR') + '/*.cpio.gz')
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
    if not (root / 'init').is_file():
        bb.fatal('Missing RAM /init bootstrap')
}
ROOTFS_POSTPROCESS_COMMAND += "finalize_ram_root; "
