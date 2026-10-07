# SPDX-License-Identifier: MIT
# BCSP needs hciattach's link establishment and even-parity setup.
# Keep only Classic Bluetooth profiles relevant to initial qualification.
PACKAGECONFIG = "readline systemd tools deprecated udev network-profiles hid-profiles"
