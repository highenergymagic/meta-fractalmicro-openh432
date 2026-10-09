# SPDX-License-Identifier: MIT
SUMMARY = "Optional OpenEVV formant synthesizer and Speech Dispatcher module"
HOMEPAGE = "https://github.com/Mudb0y/openevv"
# NOTICE excludes language data and two engine tables from upstream MIT.
# CLOSED records the absence of a redistribution grant for this combined input.
LICENSE = "CLOSED"
OPENH432_OPENEVV_SOURCE_DIR ?= ""
python () {
    if not d.getVar("OPENH432_OPENEVV_SOURCE_DIR"):
        raise bb.parse.SkipRecipe("Requires explicitly supplied restricted OpenEVV source archive")
}
FILESEXTRAPATHS:prepend := "${OPENH432_OPENEVV_SOURCE_DIR}:"
SRC_URI = "file://openevv.tar"
SRC_URI[sha256sum] = "7cdb7fa059d42882996c97c2bf2f4b51b1c1f8dc24e9bd68fa2d251859c9a134"
python do_unpack:prepend() {
    import hashlib
    import os
    source = os.path.join(d.getVar("OPENH432_OPENEVV_SOURCE_DIR"), "openevv.tar")
    with open(source, "rb") as archive:
        actual = hashlib.file_digest(archive, "sha256").hexdigest()
    if actual != d.getVarFlag("SRC_URI", "sha256sum"):
        bb.fatal("Restricted OpenEVV archive checksum mismatch")
}
S = "${UNPACKDIR}/openevv"
DEPENDS = "python3-native speech-dispatcher"
inherit pkgconfig
# Target flags, including link hardening, remain owned by OE. No host rpath.
EXTRA_OEMAKE = "'CC=${CC}' 'AR=${AR}' 'NM=${NM}' \
    'CFLAGS=${CFLAGS} ${LDFLAGS}' 'LANGS=lang/enus' RULES=c \
    'SPEECHD_LIBS=-lspeechd_module'"
do_compile() {
    oe_runmake build/evv speechd
}
do_install() {
    install -d ${D}${bindir} ${D}${libexecdir}/speech-dispatcher \
        ${D}${sysconfdir}/openh432/speech/modules ${D}${datadir}/licenses/openevv
    install -m 0755 ${S}/build/evv ${D}${bindir}/openevv
    install -m 0755 ${S}/build/sd_openevv ${D}${libexecdir}/speech-dispatcher/
    install -m 0644 ${S}/speechd/openevv.conf ${D}${sysconfdir}/openh432/speech/modules/
    install -m 0644 ${S}/LICENSE ${S}/NOTICE ${D}${datadir}/licenses/openevv/
}
FILES:${PN} += "${libexecdir}/speech-dispatcher ${datadir}/licenses/openevv"
