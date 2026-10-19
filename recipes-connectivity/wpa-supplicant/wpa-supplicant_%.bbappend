# SPDX-License-Identifier: MIT
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://0001-nl80211-no-probe-ies-for-passive-scan.patch"
SRC_URI += "file://0002-scan-honor-zero-probe-ie-capability.patch"
SRC_URI += "file://0003-filter-alternative-akms-by-driver-capability.patch"
