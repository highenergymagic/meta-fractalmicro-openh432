# SPDX-License-Identifier: MIT
require openh432-sound-test-policy_1.0.bb
SUMMARY = "Default NAND startup/shutdown sounds with bounded cold-I/O allowance"
do_install:append() {
    install -d ${D}${sysconfdir}/systemd/system/FMBootSound.service.d
    printf '%s\n' '[Service]' 'TimeoutStartSec=60s' 'TimeoutStopSec=10s' \
        > ${D}${sysconfdir}/systemd/system/FMBootSound.service.d/nand.conf
    install -d ${D}${sysconfdir}/systemd/system/FMShutdownSound.service.d
    printf '%s\n' '[Service]' 'TimeoutStopSec=30s' \
        > ${D}${sysconfdir}/systemd/system/FMShutdownSound.service.d/nand.conf
}
