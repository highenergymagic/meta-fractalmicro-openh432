# SPDX-License-Identifier: MIT
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://defer-resolver.py"

# NetworkManager already starts after local accessibility. Keep DNS setup out
# of the earlier sysinit critical path, preserving all service protections.
do_install:append() {
    if ${@bb.utils.contains('PACKAGECONFIG', 'resolved', 'true', 'false', d)}; then
        ${PYTHON} ${UNPACKDIR}/defer-resolver.py ${D}${systemd_system_unitdir}/systemd-resolved.service
    fi
}
