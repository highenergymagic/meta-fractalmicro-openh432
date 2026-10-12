# SPDX-License-Identifier: MIT
require openh432-base-image.inc
SUMMARY = "Slot-independent NAND systembase with systemd, networking and system sounds"
IMAGE_INSTALL:append = " openh432-power-key"
IMAGE_INSTALL:append = " openh432-system-sounds kde3-sounds openh432-nand-sound-policy openh432-wired-policy openh432-maintenance-ssh gpsd gps-utils openh432-agps openh432-wifi openh432-bluetooth h432b-vibrator-test openh432-braille openh432-local-console openh432-boot-success openh432-suspend openh432-udev-policy openh432-speech"
# Gzip reduces cold executable startup cost on Cortex-A8; keep one compressor thread.
IMAGE_FSTYPES = "squashfs"
SRC_URI += "file://make-verity-image.py"
S = "${UNPACKDIR}"
# Keep the unpacked formatter: image.bbclass otherwise clears S in do_rootfs.
do_rootfs[cleandirs] = "${IMAGE_ROOTFS} ${IMGDEPLOYDIR}"
# image.bbclass normally skips source tasks; this image has a local formatter.
python () {
    d.delVarFlag('do_fetch', 'noexec')
    d.delVarFlag('do_unpack', 'noexec')
}
addtask do_image_complete after do_unpack
DEPENDS += "cryptsetup-native"
do_image_complete[depends] += "cryptsetup-native:do_populate_sysroot"
EXTRA_IMAGECMD:squashfs = "-comp gzip -noappend -processors 1"
IMAGE_POSTPROCESS_COMMAND:remove = "check_ram_slot_size;"
ROOTFS_POSTPROCESS_COMMAND += "write_systembase_slot; "
write_systembase_slot() {
    install -d ${IMAGE_ROOTFS}/usr/lib/openh432
    printf '%s\n' any > ${IMAGE_ROOTFS}/usr/lib/openh432/root-slot
    rm -f ${IMAGE_ROOTFS}/init
}

# A volatile overlay must not repeat deferred package setup at every boot.
python check_no_deferred_postinsts() {
    from pathlib import Path
    root = Path(d.getVar('IMAGE_ROOTFS'))
    pending = [str(p.relative_to(root)) for backend in ('ipk', 'deb', 'rpm')
               for p in (root / ('etc/' + backend + '-postinsts')).glob('*')
               if p.is_file()]
    if pending:
        bb.fatal('Systembase contains deferred first-boot scripts: ' + ', '.join(pending))
}
ROOTFS_POSTPROCESS_COMMAND += "check_no_deferred_postinsts; "

# Kernel compilation has no dependency on this rootfs. The handoff image takes
# this descriptor only after the systembase and its kernel modules are complete.
python make_systembase_verity() {
    import os
    import subprocess
    from pathlib import Path
    directory = Path(d.getVar('IMGDEPLOYDIR'))
    name = d.getVar('IMAGE_NAME')
    link = d.getVar('IMAGE_LINK_NAME')
    capacity = int(d.getVar('H432B_SYSTEMBASE_LEBS')) * int(d.getVar('H432B_UBI_LEB_BYTES'))
    subprocess.run(['python3', d.getVar('UNPACKDIR') + '/make-verity-image.py',
                    str(directory / (name + '.squashfs')),
                    str(directory / (name + '.squashfs.verity')),
                    str(directory / (name + '.verity')),
                    '--capacity', str(capacity)], check=True)
    for suffix in ('.squashfs.verity', '.verity'):
        path = directory / (link + suffix)
        if path.is_symlink():
            path.unlink()
        os.symlink(name + suffix, path)
}
IMAGE_POSTPROCESS_COMMAND += "make_systembase_verity; "
