# SPDX-License-Identifier: MIT
require openh432-base-image.inc
SUMMARY = "Standalone OpenH432 RAM recovery and development root filesystem"

# Maintenance transfers use the same opt-in SSH policy as the NAND runtime.
IMAGE_INSTALL:append = " openh432-wired-policy openh432-maintenance-ssh"
