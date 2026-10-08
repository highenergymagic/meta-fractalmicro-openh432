# Runtime policy

## Root filesystem and state

The NAND kernel bundle contains only the root-handoff initramfs. Early
userspace attaches the existing UBI pool, checks the slot marker and mounts
the matching SquashFS systembase through ubiblock before starting systemd.
Root handoff does not format, repartition or replace storage images.

The systembase is limited to less than 200 MiB. A 64 MiB volatile overlay
provides writable runtime state. Changes to credentials, pairing state,
assistance caches and other overlay files are lost on reboot. Persistent
userdata is not implemented. Managed A/B boots use persistent attempt limits
and automatic acknowledgement of a healthy local console.

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
| Boot success | FMMarkBootSuccessful enabled; acknowledges only a managed, healthy boot attempt |
| Built-in console | tty1 autologin as unprivileged user (UID/GID 1000) |
| SSH | Key-gated maintenance with volatile identity |
| Power key | Actions ignored pending qualified shutdown/wake or suspend/resume |
| Braille | FMBraille enabled; internal display, keyboard and routing devices owned by BRLTTY |
| Keyboard / selectors | Kernel evdev devices and BRLTTY chord translation; no keypad-lock or notification policy |
| Battery | Kernel read-only power_supply telemetry; no charger or low-battery policy |
| Vibration | Bounded h432b-vibrator-test command installed; never started automatically |

Configuration references:
[remote access](remote-access.md), [GPS](gps.md),
[system sounds](system-sounds.md),
[Wi-Fi](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/wifi.md)
and [Bluetooth](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/bluetooth.md).

## Local account

The standard NAND image includes `openh432-local-console`. It creates the
single appliance account `user` (UID/GID 1000, shell `/bin/sh`, home
`/home/user`) and enables automatic login only for `getty@tty1`.
Logging out returns to the same account. No password is supplied or stored:
the account's password is locked, and the local getty performs the authorized
login without a password. The account has no sudo or additional device groups.

Root remains password-locked. SSH remains key-only and is not enabled by
this policy; serial and USB services are unchanged. Physical access to the
built-in console provides access to the appliance account.

The home directory currently lives in the volatile root overlay. Files and
account changes are lost on reboot until persistent userdata is implemented.

## Managed A/B boots

The loader supplies one `rauc.slot=A|B` argument and an `openh432.attempt`
serial. Root handoff mounts the matching systembase. After 30 seconds,
`FMMarkBootSuccessful.service` checks the mounted root, UBI geometry, BRLTTY,
tty1 and the local user session. The locked `h432b-bootstate-check` helper
restores that slot's attempt allowance only if the stored serial still matches.
Network connectivity is not a health requirement; stale acknowledgements fail.

The argument names are compatible with RAUC conventions, but RAUC and a signed
bundle installer are not included. A hung kernel has no qualified watchdog
recovery. See the [boot contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/boot-contract.md)
for state format, update ordering and maintenance behavior.

## Security boundary

Development images provide an unauthenticated physical USB root console.
They are not suitable for production or security-sensitive use.
Generic images do not contain network credentials or user keys.

The [support matrix](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md)
distinguishes runtime integration from optional diagnostics and unsupported
features. Service inclusion alone does not establish hardware qualification.
