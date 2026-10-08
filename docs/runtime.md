# Runtime policy

## Root filesystem and state

The NAND kernel bundle contains a root-handoff initramfs and startup cue,
not the full userspace. Early
userspace attaches the existing UBI pool, checks the slot marker and mounts
the matching SquashFS systembase through ubiblock before starting systemd.
Root handoff does not format, repartition or replace storage images.
The standard systembase uses gzip compression, with a single build compressor
thread. Its artifact suffix is `.squashfs`; the kernel bundle's handoff
initramfs remains XZ-compressed. Static-volume CRC verification remains enabled.

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
| GPS | Local-only gpsd with proxy-backed RAM assistance; automatic start after 90 seconds |
| System sounds | NAND startup cue in root-handoff initramfs, fallback/shutdown in systembase; quiet RAM development image |
| Boot success | FMMarkBootSuccessful enabled; acknowledges only a managed, healthy boot attempt |
| Built-in console | tty1 autologin as unprivileged user (UID/GID 1000) |
| SSH | Key-gated maintenance with volatile identity |
| Power key | systemd-logind deep suspend; power-only wake and braille supply control |
| Braille | FMBraille enabled; internal display, keyboard and routing devices owned by BRLTTY |
| Keyboard / selectors | Kernel evdev devices and BRLTTY chord translation; no keypad-lock or notification policy |
| Battery | Kernel read-only power_supply telemetry; no charger or low-battery policy |
| Vibration | Bounded h432b-vibrator-test command installed; never started automatically |

Configuration references:
[remote access](remote-access.md), [GPS](gps.md),
[system sounds](system-sounds.md),
[Wi-Fi](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/wifi.md)
and [Bluetooth](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/bluetooth.md).

## Suspend policy

The standard systembase includes `openh432-suspend`. A power-switch press
requests `mem` suspend with `deep` selected; pressing power again resumes the
existing session. Short and long presses have the same logind action.
Other keys and selectors are not wake sources. Idle suspend, lid actions,
hibernation and hybrid sleep are disabled.

The kernel removes braille-cell drive power during suspend and restores the
cached frame on wake. No user-space blanking or display-power script is needed.
USB reconnects after wake, so maintenance clients must reopen their connection.

Core sleep, display power and power-only wake have passed device tests.
RTC-based sleep-time accounting has passed with network correction stopped.
Peripheral recovery is not fully qualified;
see the [power-management reference](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/power-control.md)
before relying on unattended suspend.

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
serial. Root handoff mounts the matching systembase. A timer schedules
`FMMarkBootSuccessful.service` without blocking the multi-user target. The service still waits 30 seconds after its console dependencies start,
then checks the mounted root, UBI geometry, BRLTTY,
tty1 and the local user session. The locked `h432b-bootstate-check` helper
restores that slot's attempt allowance only if the stored serial still matches.
Network connectivity is not a health requirement; stale acknowledgements fail.

The packaged `59-openh432-bootstate.rules` excludes UBI volumes named
`bootstate_a` and `bootstate_b` from generic persistent-storage filesystem
probing. These contain environment records, not filesystems; a probe's open
reader can prevent the exclusive UBI update needed for acknowledgment.
Normal device creation, systemd tagging and probing of other volumes remain
enabled. Other tools must also avoid holding these volumes open during updates.

`59-openh432-managed-images.rules` also suppresses raw-UBI filesystem discovery
for the named kernel, recovery and systembase image volumes. The loader and
root handoff select these explicitly; discovering an inactive static image
would otherwise trigger a full-volume CRC read. This rule does not suppress
the selected root's UBI integrity check or affect block-device, MMC or USB
storage discovery.

The argument names are compatible with RAUC conventions, but RAUC and a signed
bundle installer are not included. A hung kernel has no qualified watchdog
recovery. See the [boot contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/boot-contract.md)
for state format, update ordering and maintenance behavior.

## Device discovery

The standard H432B systembase includes `openh432-udev-policy`. Coldplug
replays device events without replaying module, bus and driver bookkeeping
events. The built-in maintenance tty receives an initial add event before the
bulk pass, so it does not wait behind general device discovery. The bulk pass
still includes the tty and all other devices; a missing tty does not fail boot.
All device subsystems remain eligible; device permissions, persistent
storage links, input properties and subsequent USB/SD hotplug use the normal
udev rules. Four concurrent workers bound discovery-helper contention on the
single-core target.

The policy masks `75-probe_mtd.rules`: the board's soldered NAND is not
SmartMedia. USB storage readers continue to use block-device discovery.
The policy does not shorten event timeouts, disable udev or suppress device
initialization. These settings apply only to the H432B machine.

## Security boundary

Development images provide an unauthenticated physical USB root console.
They are not suitable for production or security-sensitive use.
Generic images do not contain network credentials or user keys.

The [support matrix](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md)
distinguishes runtime integration from optional diagnostics and unsupported
features. Service inclusion alone does not establish hardware qualification.
