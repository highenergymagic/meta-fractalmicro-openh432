# SPDX-License-Identifier: MIT
require openh432-base-image.inc
SUMMARY = "Slot-independent NAND systembase with systemd, networking and system sounds"
IMAGE_INSTALL:append = " openh432-system-sounds kde3-sounds openh432-nand-sound-policy openh432-wired-policy openh432-maintenance-ssh gpsd gps-utils openh432-agps openh432-wifi openh432-bluetooth h432b-vibrator-test openh432-braille openh432-local-console openh432-boot-success openh432-suspend"
IMAGE_FSTYPES = "squashfs-xz"
IMAGE_POSTPROCESS_COMMAND:remove = "check_ram_slot_size;"
ROOTFS_POSTPROCESS_COMMAND += "write_systembase_slot; "
write_systembase_slot() {
    install -d ${IMAGE_ROOTFS}/usr/lib/openh432
    printf '%s\n' any > ${IMAGE_ROOTFS}/usr/lib/openh432/root-slot
    rm -f ${IMAGE_ROOTFS}/init
}
