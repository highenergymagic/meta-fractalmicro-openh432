# SPDX-License-Identifier: MIT
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://0002-linux-optional-probes.patch"
DEPENDS:append = " speech-dispatcher"
EXTRA_OECONF:remove = "--disable-speech-support"
EXTRA_OECONF:append = " --enable-speech-support --with-speech-driver=sd,-all"
# The built-in driver archive needs its client library on the final link.
EXTRA_OEMAKE:append = " SPEECH_DRIVER_LIBRARIES='-lspeechd -lglib-2.0'"
