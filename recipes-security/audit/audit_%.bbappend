# SPDX-License-Identifier: MIT
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://openh432-auditd.conf"

do_install:append() {
    install -m 0600 ${UNPACKDIR}/openh432-auditd.conf ${D}${sysconfdir}/audit/auditd.conf
}
