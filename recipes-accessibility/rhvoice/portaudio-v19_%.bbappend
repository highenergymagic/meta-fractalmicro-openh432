# SPDX-License-Identifier: MIT
# Use only the on-device ALSA path; no JACK server in systembase.
PACKAGECONFIG = "alsa"

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://0001-portaudio-alsa-plugin-channels.patch"
