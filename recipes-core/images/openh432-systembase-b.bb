# SPDX-License-Identifier: MIT
require openh432-base-image.inc
SUMMARY = "Slot-independent NAND systembase with systemd, networking and system sounds"
IMAGE_INSTALL:append = " openh432-system-sounds kde3-sounds openh432-nand-sound-policy openh432-wired-policy openh432-maintenance-ssh gpsd gps-utils openh432-agps openh432-wifi openh432-bluetooth h432b-vibrator-test openh432-braille openh432-local-console openh432-boot-success openh432-suspend openh432-udev-policy openh432-speech"
# Gzip reduces cold executable startup cost on Cortex-A8; keep one compressor thread.
IMAGE_FSTYPES = "squashfs"
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
