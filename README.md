# meta-fractalmicro-openh432

Yocto/OpenEmbedded distribution policy and image composition for OpenH432
on the H432B BrailleSense U2. This Fractal Microsystems layer supplies
glibc/systemd userspace, service policy and image-format checks.
Hardware drivers and device trees belong to
[meta-fractalmicro-H432B](https://github.com/highenergymagic/meta-fractalmicro-H432B).

OpenH432 is a developer preview, not a complete accessible firmware replacement.

## Build integration

Use the pinned Wrynose composition and Docker workflow in
[openh432-build](https://github.com/highenergymagic/openh432-build).
Select `DISTRO = "openh432"` and `MACHINE = "h432b"`.
That repository supports native Linux x86-64 and ARM64 firmware builders.
Builds produce artifacts and never deploy them.

The manifest imports
[meta-fractalmicro-assets](https://github.com/highenergymagic/meta-fractalmicro-assets)
for separately licensed startup/shutdown sounds.

## Images

| Target | Role |
| --- | --- |
| `openh432-nand-b` | Kernel/DTB/minimal-initramfs bundle for slot B |
| `openh432-systembase-b` | Separate SquashFS userspace, capped below 200 MiB |
| `openh432-early-b` | Root-handoff initramfs used by the NAND kernel bundle |
| `openh432-fastboot-ram` | Runtime kernel with complete standalone RAM root |
| `openh432-ram-dev` | Quiet glibc/systemd development initramfs |
| `openh432-hardware-test` | RAM image with explicit sound-test policy |

The boot envelope uses an Android header for loader compatibility; the OS is
not Android. See the [target catalogue](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/targets.md)
for optional profiles and their prerequisites.

## NAND root and state

Early userspace attaches the existing UBI pool, checks the slot marker,
mounts `systembase_b` through ubiblock and starts systemd. A 64 MiB volatile
overlay supplies writable state. No formatting, repartitioning or image
replacement occurs during root handoff.

The runtime permits Linux UBI and internal-SD writes while protecting factory
boot and BBT regions. Credentials, pairing state, assistance cache and other
overlay changes disappear on reboot. Persistent userdata and coordinated
A/B activation/rollback are not implemented.

## Services

| Feature | Policy |
| --- | --- |
| Ethernet | systemd-networkd DHCP |
| Wi-Fi | FMWiFi startup with compatible external firmware; private supplicant profile required |
| Bluetooth | BlueZ packaged; FMBluetoothTransport disabled pending automatic factory initialization |
| GPS | Local-only gpsd and proxy-backed RAM assistance; [configuration](docs/gps.md) |
| Sounds | Enabled in NAND systembase, quiet RAM development image; [configuration](docs/system-sounds.md) |
| SSH | Key-gated maintenance with volatile identity; [configuration](docs/remote-access.md) |
| Power key | Actions ignored pending qualified shutdown/wake or suspend/resume |

Wi-Fi supports a limited WPA2-Personal/CCMP station profile; see the
[Wi-Fi reference](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/wifi.md).
Bluetooth requires manual radio/identity initialization and has no audio backend;
see the [Bluetooth reference](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/bluetooth.md).

## Deployment and security

Development images expose an unauthenticated physical USB root console.
They are not suitable for production or security-sensitive use. Network
credentials and keys are never built into generic images.

Read the [boot contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/boot-contract.md)
and [conversion guide](https://github.com/highenergymagic/openh432-tools/blob/main/docs/installation.md).
The standalone RAM environment can run before a NAND systembase exists;
it is not a general-purpose installer.

The [support matrix](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md)
distinguishes runtime integration from diagnostics and unqualified features.

## License

New metadata and policy files are MIT-licensed. Software and media retain
their upstream licenses.
