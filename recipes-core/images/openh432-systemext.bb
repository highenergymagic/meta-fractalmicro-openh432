# SPDX-License-Identifier: MIT
SUMMARY = "Slot-independent read-only OpenH432 system extension"
LICENSE = "MIT"
inherit core-image
inherit openh432-selinux-image
SRC_URI = "file://make-verity-image.py"
S = "${UNPACKDIR}"
do_rootfs[cleandirs] = "${IMAGE_ROOTFS} ${IMGDEPLOYDIR}"
python () {
    d.delVarFlag('do_fetch', 'noexec')
    d.delVarFlag('do_unpack', 'noexec')
}
addtask do_image_complete after do_unpack
do_image_complete[depends] += "cryptsetup-native:do_populate_sysroot"
IMAGE_INSTALL = ""
IMAGE_FEATURES = ""
IMAGE_LINGUAS = ""
NO_RECOMMENDATIONS = "1"
IMAGE_FSTYPES = "erofs"
EXTRA_IMAGECMD:erofs = "-T ${SOURCE_DATE_EPOCH} -U 6e351382-ae8c-4a19-98de-8dfbb2f03d52"
IMAGE_VERSION_SUFFIX = "-${SOURCE_DATE_EPOCH}"
REPRODUCIBLE_TIMESTAMP_ROOTFS = "${SOURCE_DATE_EPOCH}"
ROOTFS_POSTPROCESS_COMMAND += "write_extension_release; "
write_extension_release() {
    install -d ${IMAGE_ROOTFS}/usr/lib/extension-release.d
    printf 'ID=openh432\nSYSEXT_LEVEL=1\n' > ${IMAGE_ROOTFS}/usr/lib/extension-release.d/extension-release.openh432
}
python wrap_extension_verity() {
    import os
    import subprocess
    from pathlib import Path
    directory = Path(d.getVar('IMGDEPLOYDIR'))
    name = d.getVar('IMAGE_NAME')
    link = d.getVar('IMAGE_LINK_NAME')
    subprocess.run(['python3', d.getVar('UNPACKDIR') + '/make-verity-image.py',
                    str(directory / (name + '.erofs')),
                    str(directory / (name + '.erofs.verity')),
                    str(directory / (name + '.verity')),
                    '--capacity', str(2 * 1024 * 1024 * 1024)], check=True)
    for suffix in ('.erofs.verity', '.verity'):
        path = directory / (link + suffix)
        if path.is_symlink():
            path.unlink()
        os.symlink(name + suffix, path)
}
IMAGE_POSTPROCESS_COMMAND += "wrap_extension_verity; "
