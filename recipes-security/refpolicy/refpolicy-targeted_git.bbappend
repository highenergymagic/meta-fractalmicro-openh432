# SPDX-License-Identifier: MIT
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://fm_settings.te file://fm_settings.if file://fm_settings.fc file://0001-seutil-read-file-contexts-through-policy-symlink.patch"

# Linux 6.12 supports policy format 33. The pinned layer hardcodes 35 in
# rebuild_policy; override that function until upstream exposes a variable.
OPENH432_POLICY_VERSION = "33"
POLICY_UNK_PERMS = "deny"
python () {
    if d.getVar("OPENH432_SELINUX_MODE") not in ("permissive", "enforcing"):
        bb.fatal("OPENH432_SELINUX_MODE must be permissive or enforcing")
}
CONFFILES:${PN} = ""
FILES:${PN} = "${sysconfdir}/selinux ${datadir}/openh432/selinux"
FILES:${PN}-dev:remove = "${sysconfdir}/selinux/sepolgen.conf"
FILES:${PN}-dev += "${datadir}/openh432/selinux/sepolgen.conf"
FILES:${PN}-dev += "${datadir}/selinux/${POLICY_NAME}/*.pp ${POLICY_STORE_ROOT}/${POLICY_NAME}/"
do_compile:prepend() {
    install -m 0644 ${UNPACKDIR}/fm_settings.te ${S}/policy/modules/services/
    install -m 0644 ${UNPACKDIR}/fm_settings.if ${S}/policy/modules/services/
    install -m 0644 ${UNPACKDIR}/fm_settings.fc ${S}/policy/modules/services/
}

rebuild_policy() {
    printf '%s\n' 'module-store = direct' \
        '[setfiles]' \
        'path = ${STAGING_DIR_NATIVE}${base_sbindir_native}/setfiles' \
        'args = -q -c $@ $<' '[end]' \
        '[sefcontext_compile]' \
        'path = ${STAGING_DIR_NATIVE}${sbindir_native}/sefcontext_compile' \
        'args = $@' '[end]' > ${D}${sysconfdir}/selinux/semanage.conf
    printf 'policy-version = ${OPENH432_POLICY_VERSION}\nstore-root = "${POLICY_STORE_ROOT}"\n' \
        >> ${D}${sysconfdir}/selinux/semanage.conf
    semodule -p ${D} -s ${POLICY_NAME} -n -B
    rm -f ${D}${sysconfdir}/selinux/semanage.conf
    rm -rf ${D}${POLICY_STORE_ROOT}/final
}

# Policy and enforcement mode belong to the immutable OS deployment, not
# the three-way-merged writable /etc or shared /var policy module store.
do_install:append() {
    # Compiled PCRE caches encode the build host's word size. Ship portable
    # text contexts; libselinux parses these on the 32-bit target instead.
    find ${D}${sysconfdir}/selinux/${POLICY_NAME}/contexts/files \
        -name 'file_contexts*.bin' -type f -delete
    install -d ${D}${datadir}/openh432
    mv ${D}${sysconfdir}/selinux ${D}${datadir}/openh432/selinux
    ln -s ../usr/share/openh432/selinux ${D}${sysconfdir}/selinux
    printf '%s\n' '/usr/share/openh432/selinux /etc/selinux' >> \
        ${D}${datadir}/openh432/selinux/${POLICY_NAME}/contexts/files/file_contexts.subs_dist
}

# Version all runtime policy inputs using relative names, independent of the
# build directory and architecture. The result is protected by image verity.
fakeroot python do_label_identity() {
    import hashlib
    from pathlib import Path
    root = Path(d.getVar('D') + d.getVar('datadir')) / 'openh432/selinux'
    target = root / d.getVar('POLICY_NAME') / 'label-version'
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        if path == target or not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    target.write_text(digest.hexdigest() + '\n')
}
addtask label_identity after do_install before do_package do_populate_sysroot
