# SPDX-License-Identifier: MIT
SUMMARY = "Offline non-neural RHVoice synthesis engine"
HOMEPAGE = "https://rhvoice.org/"
LICENSE = "GPL-2.0-or-later & BSD-3-Clause & MIT & BSL-1.0"
LIC_FILES_CHKSUM = "file://LICENSE.md;md5=b234ee4d69f5fce4486a80fdaf4a4263"
SRC_URI = "git://github.com/RHVoice/RHVoice.git;protocol=https;branch=master \
 file://0001-cross-build.patch file://0002-preserve-eof-on-arm.patch"
SRCREV = "fc0040f80740bb1ebbc0b7bf32e530b6afaedbec"
DEPENDS = "boost portaudio-v19 speech-dispatcher"
inherit cmake pkgconfig
EXTRA_OECMAKE = "-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
 -DRHVOICE_VERSION_FROM_GIT=${PV} -DRHVOICE_VERSION_TIME=${SOURCE_DATE_EPOCH} \
 -DRHVOICE_VERSION_EXPORT=release -DWITH_DATA=OFF -DENABLE_SONIC=OFF \
 -DBUILD_CLIENT=OFF -DBUILD_SERVICE=OFF -DBUILD_UTILS=OFF \
 -DBUILD_TESTS=ON -DBUILD_SPEECHDISPATCHER_MODULE=ON \
 -DWITH_LIBAO=OFF -DWITH_PULSE=OFF -DWITH_PORTAUDIO=ON \
 -DSPEECH_DISPATCHER_MODULES_DIR=${libexecdir}/speech-dispatcher"
FILES:${PN} += "${libexecdir}/speech-dispatcher ${datadir}/RHVoice"
do_install:append() {
    # Configuration is owned by the appliance policy package.
    rm -f ${D}${sysconfdir}/RHVoice/RHVoice.conf
}
