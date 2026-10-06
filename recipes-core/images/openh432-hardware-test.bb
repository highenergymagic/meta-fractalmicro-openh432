# SPDX-License-Identifier: MIT
require openh432-ram-dev.bb
SUMMARY = "OpenH432 development image with audible system-sound tests enabled"
IMAGE_INSTALL:append = " kde3-sounds openh432-system-sounds openh432-sound-test-policy"
