# Runtime policy

## Root filesystem and state

The NAND kernel bundle contains only the root-handoff initramfs. Early
userspace attaches the existing UBI pool, checks the slot marker and mounts
the matching SquashFS systembase through ubiblock before starting systemd.
Root handoff does not format, repartition or replace storage images.

The systembase is limited to less than 200 MiB. A 64 MiB volatile overlay
provides writable runtime state. Changes to credentials, pairing state,
assistance caches and other overlay files are lost on reboot. Persistent
userdata and coordinated A/B activation or rollback are not implemented.

The normal runtime permits Linux UBI maintenance and internal-SD writes.
Factory boot and bad-block-table regions remain protected.
See the [storage reference](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/nand.md)
for layout and write boundaries.

## Service defaults

| Service or interface | Policy |
| --- | --- |
| Ethernet | systemd-networkd DHCP |
| Wi-Fi | FMWiFi startup requires extracted radio firmware; station credentials supplied separately |
| Bluetooth | BlueZ packaged; FMBluetoothTransport disabled pending automatic factory initialization |
| GPS | Local-only gpsd with proxy-backed RAM assistance |
| System sounds | Enabled in NAND systembase; quiet RAM development image |
| SSH | Key-gated maintenance with volatile identity |
| Power key | Actions ignored pending qualified shutdown/wake or suspend/resume |
| Braille | FMBraille enabled; internal display, keyboard and routing devices owned by BRLTTY |
| Keyboard / selectors | Kernel evdev devices; no chord translation, keypad-lock or notification policy |
| Battery | Kernel read-only power_supply telemetry; no charger or low-battery policy |
| Vibration | Bounded h432b-vibrator-test command installed; never started automatically |

Configuration references:
[remote access](remote-access.md), [GPS](gps.md),
[system sounds](system-sounds.md),
[Wi-Fi](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/wifi.md)
and [Bluetooth](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/bluetooth.md).

## Security boundary

Development images provide an unauthenticated physical USB root console.
They are not suitable for production or security-sensitive use.
Generic images do not contain network credentials or user keys.

The [support matrix](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md)
distinguishes runtime integration from optional diagnostics and unsupported
features. Service inclusion alone does not establish hardware qualification.
