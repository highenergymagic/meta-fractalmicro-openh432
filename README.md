# meta-fractalmicro-openh432

Operating-system policy and image recipes for OpenH432, a Linux-based
operating system in development for the HIMS BrailleSense U2.

This Fractal Microsystems layer defines the software environment above
the board support package. It uses Yocto/OpenEmbedded, glibc and systemd,
with hardware support maintained separately in
[meta-fractalmicro-H432B](https://github.com/highenergymagic/meta-fractalmicro-H432B).

## What this layer provides

- Distribution configuration for `DISTRO = "openh432"`.
- Package selection and development image composition.
- systemd service and access policies.
- Image packaging and checks on required contents and size.

Hardware drivers, device trees and bootloader patches belong to the BSP
layer. Container configuration and source revision locks belong to
[openh432-build](https://github.com/highenergymagic/openh432-build).

## Development images

The layer provides RAM-resident diagnostic environments and a separate
NAND systembase composition. Neither is a production installer.

| Target | Purpose |
| --- | --- |
| `openh432-ram-dev` | A glibc/systemd development system packaged as an initramfs. |
| `openh432-hardware-test` | An explicitly audible test initramfs with startup/shutdown services enabled; requires the assets layer. |
| `openh432-fastboot-ram` | The same runtime kernel and device tree as NAND boot, with a complete standalone RAM root for recovery/development. |

The default systembase includes `FMWiFi.service`, `iw`, `wpa_supplicant`,
`wpa_cli` and the signed regulatory database. Compatible operator-supplied
firmware enables automatic `wlan0` initialization. The station driver supports
WPA2-Personal with CCMP; see the qualification guide for tested limitations.
The standard `wpa_supplicant@wlan0.service` is ordered after radio startup,
and systemd-networkd handles DHCP/IPv6. No network profile or credentials are
shipped. Provision a private profile before starting the supplicant; the
current writable root overlay is volatile and loses that profile on reboot.

The systembase also includes BlueZ and the opt-in
`FMBluetoothTransport.service` for the internal CSR BCSP controller.
The transport service is disabled by default: factory address and radio
configuration still require manual initialization. Discovery, pairing and
L2CAP exchanges have passed on hardware; automatic startup and Bluetooth
audio playback are not implemented. Pairing state in the current root overlay
is volatile. See the [Bluetooth hardware guide](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/bluetooth.md).

The optional `openh432-wifi-test` bundle supports explicit RTL8712 SDIO
firmware, command and cfg80211 passive-scan diagnostics against the existing
slot-B root. It shares the runtime driver and is not a standalone recovery system. Compatible firmware must be supplied independently; this layer does
not fetch or redistribute it. The optional `openh432-wifi-tools` target builds
an archive containing `iw`, its libraries and the signed regulatory database;
it is not a bootable image or a replacement root filesystem. Build it with
`python3 scripts/bsp.py build openh432-wifi-tools` from the build repository.
Its tar archive must be unpacked into a separate temporary directory, not over
the running root. The bundled `iw` requires its accompanying libnl libraries;
the `regulatory.db` and `regulatory.db.p7s` files belong together in the
kernel firmware search path. Select the actual country with `iw reg set`;
do not infer a regulatory domain from the network name. This archive contains
no radio firmware or network credentials. See the
[Wi-Fi qualification guide](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/wifi.md).

The fastboot bundle uses an Android boot-image header for compatibility
with the host tool; the operating system itself is not Android.

The development system has booted on a U2 and passed systemd health and
selected service-isolation checks. The RAM image remains distinct from the
NAND-root composition documented below; neither provides persistent userdata.

The optional [system sounds](docs/system-sounds.md) are sourced by
[meta-fractalmicro-assets](https://github.com/highenergymagic/meta-fractalmicro-assets).
The optional RAM diagnostic image remains quiet; the NAND base includes the
selected boot and shutdown sounds.

## NAND root composition

The slot-B NAND composition is built with `openh432-nand-b` and
`openh432-systembase-b`. The kernel bundle contains the kernel, device tree
and a minimal `openh432-early-b` initramfs, not the complete operating system.
The runtime kernel permits writes to the Linux UBI pool and internal SD,
while protecting factory boot and BBT regions. Early userspace attaches the
existing UBI pool, selects
`systembase_b`, checks its state and slot marker, mounts SquashFS through
ubiblock read-only, and switches root to systemd. No formatting or image
replacement is performed during this handoff.

The base includes local-only gpsd, GPS command-line clients, and optional
proxy-backed RAM assistance; see [GPS service policy](docs/gps.md). Hardware
support is included in the normal NAND runtime kernel.

The base includes wired DHCP configuration and the selected KDE boot/shutdown
sounds from
[meta-fractalmicro-assets](https://github.com/highenergymagic/meta-fractalmicro-assets).
A 64 MiB volatile overlay supplies writable runtime state; changes are lost
on reboot. This is not persistent userdata or coordinated A/B rollback.
The standalone RAM environment remains available for initial conversion and
recovery before a NAND systembase exists. Shared userland and boot-envelope
metadata live in `.inc` files; the NAND image does not inherit a test-image
recipe. The obsolete standalone reboot-test kernel/image has been retired.
The handoff reached systemd both in a RAM-launched test and after a software
reboot using the installed NAND kernel. Ethernet configured automatically.
The startup sound completed, with observed NAND-read playback underruns;
audio buffering still needs work. Power-off, wake, persistent identity and
coordinated updates remain unfinished.

## Building

Follow the [build guide](https://github.com/highenergymagic/openh432-build#building)
for the pinned container workflow and exact layer revisions. This layer
targets Yocto Wrynose.

Builds only produce artifacts. They do not connect to or modify a device.

## Development access and limitations

**Development images expose an unauthenticated root shell over physical
USB. They are not suitable for production use.**

The normal NAND runtime enables Linux UBI and internal SD writes while
protecting factory boot and BBT regions. Historical diagnostic profiles may
retain read-only guards. Images do not automatically partition disks, format
filesystems or install firmware.
Hardware bring-up and accessibility services remain incomplete.

Production and recovery images, persistent system storage, and coordinated
A/B updates are still under development. See the
[validation status](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md)
for completed tests and current limitations, and the
[BSP boot contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/boot-contract.md)
before attempting to boot an image.

For host-side bootstrap and backup tools, see
[openh432-tools](https://github.com/highenergymagic/openh432-tools) and its
[conversion guide](https://github.com/highenergymagic/openh432-tools/blob/main/docs/installation.md).
Building an image and converting a stock device are separate operations.

## License

New metadata and policy files are MIT-licensed. Software included in the
images retains its own upstream licenses.

## Maintenance access

The development systembase-B includes an opt-in, key-only SSH service.
It stays inactive until an operator provisions an authorized public key;
no credentials are built into images. See [maintenance SSH](docs/remote-access.md)
for provisioning, host-key verification and volatile-identity limitations.
