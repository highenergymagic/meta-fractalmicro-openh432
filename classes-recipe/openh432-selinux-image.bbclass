# SPDX-License-Identifier: MIT
# Label both immutable filesystems before image generation and verity hashing.
# The extension gets contexts from the same pinned policy, not a second copy
# of the policy package in its /usr union.
DEPENDS += "refpolicy-targeted policycoreutils-native attr-native"
do_image[depends] += "refpolicy-targeted:do_populate_sysroot policycoreutils-native:do_populate_sysroot attr-native:do_populate_sysroot"
IMAGE_PREPROCESS_COMMAND:append = " openh432_label_image; "

openh432_label_image() {
    contexts="${RECIPE_SYSROOT}${sysconfdir}/selinux/targeted/contexts/files/file_contexts"
    test -s "$contexts" || bbfatal "Missing SELinux file contexts"
    setfiles -m -r "${IMAGE_ROOTFS}" "$contexts" "${IMAGE_ROOTFS}" || \
        bbfatal "SELinux build-time labeling failed"
    getfattr --only-values -n security.selinux "${IMAGE_ROOTFS}/usr" >/dev/null || \
        bbfatal "SELinux labels were not retained by the image staging filesystem"
    test ! -e "${IMAGE_ROOTFS}/.autorelabel" || \
        bbfatal "Immutable images must not defer labeling to boot"
}
