# GPS and assisted acquisition

The NAND systembase composition includes gpsd, its command-line clients, and
the OpenH432 AGPS service package. Device drivers and UART/power descriptions
remain in the hardware layer. The NAND runtime kernel used by
`openh432-nand-b` and the GPS diagnostic profile now share the qualified
GlobalTop GMM-U2P power/reset sequencing and UART description. This promotes
GPS without enabling unrelated diagnostic hardware. The normal runtime now
allows Linux UBI maintenance and internal SD writes; the static systembase
itself remains mounted read-only.
Previously installed NAND kernels lack this support and must be updated
alongside the base userspace. Build and boot qualification are distinct.

## Activation and ownership

A udev rule identifies physical UART1 at `e2900400.serial`, creates
`/dev/openh432-gps` with access limited to the dedicated `openh432-gps`
account, and requests `gpsd.service`. Generic gpsd socket activation and
gpsdctl hotplug units are masked. The packaged policy must be installed
alongside gpsd.

gpsd wants, but does not require, `agps-data-upload.service`, and starts
after that bounded attempt completes. Missing cache, untrusted time or
unavailable assistance must not prevent ordinary GPS operation. The uploader
and gpsd launcher hold the same exclusive lock for their lifetimes. An
attempt to run an uploader while gpsd owns that lock fails without touching
the UART.

gpsd runs unprivileged, listens on loopback, and reads at fixed 9600 baud
without reconfiguring the receiver. It does not expose location over the
Ethernet interface. Privileged diagnostic programs must not bypass this
ownership protocol.

## Cache refresh

`agps-data-refresh.timer` requests a refresh two minutes after boot with
up to five minutes of random delay, then every six hours. It does not delay
boot or wait for network-online. Failed refreshes preserve the previous
cache. The only network sources are:

- https://gpsdata-proxy-openh432.highenergymagic.net/EPO.DAT
- https://gpsdata-proxy-openh432.highenergymagic.net/EPO.MD5

TLS certificate verification is mandatory. Redirects, environment-provided
proxies, oversized files, malformed records, inconsistent dates and checksum
mismatches are rejected. There is no direct upstream fallback. MD5 checks
file/sidecar consistency; it is not a substitute for TLS authentication.
Internal record XORs and current validity are checked independently.

Data are atomically replaced in `/var/cache/openh432-agps/EPO.DAT`.
The current development system has a volatile writable overlay, so this cache
does not yet survive reboot. Persistent userdata integration must preserve
that path in a later storage-policy change. Predictions are runtime data,
never pinned build inputs or redistributed image assets.

## Upload policy

Only the current six-hour GPS-only EPO set is supplied, using the qualified
PMTK721 RAM-aiding path. Zero-ID records are omitted. Every packet requires a
checksum-valid success acknowledgement; timeout or rejection stops the
attempt. Current UTC is supplied using PMTK740 only after a recent systemd
time-synchronization marker. No location is guessed. Firmware identification
must match the tested release before any aiding write.

This initial policy accepts time synchronization no older than one hour.
Its explicit GPS/UTC offset is valid only through December 2026, based on IERS
Bulletin C72. After that window it declines aiding until the policy is updated;
ordinary GPS remains available. A maintained leap-second/time-trust policy
is future work, not an assumption that this offset lasts forever.

Uploads neither write receiver flash nor change baud/protocol mode. Normal
NMEA reception is checked after successful upload. Cache refresh does not
interrupt an active navigation session; newly downloaded data are applied
on the next gpsd service start. Refresh followed by a deliberate
`systemctl restart gpsd.service` applies them immediately, but disconnects
existing GPS clients.

Receiver power-off, resume/re-aiding and inactivity-based power savings are
not implemented by these services. The diagnostic kernel currently keeps
the receiver powered. A successful upload does not prove satellite reception
or faster time to first fix.

## Validation

The pinned Yocto build of `openh432-systembase-b` passed with gpsd 3.27.5
and the AGPS package. The resulting SquashFS image is 27,340,800 bytes,
below the 200 MiB systembase limit. It has not yet undergone a new cross-host
bit-for-bit comparison.

The GPS-enabled kernel and base image were subsequently installed in slot B
with matching image readbacks and unchanged slot-A hashes. A normal NAND
boot reached systemd with gpsd and the refresh timer active. Local receiver
reports, proxy HTTPS refresh, and a service-managed 31-satellite acknowledged
upload passed from the installed system. Linux UBI and internal SD reported
writable; factory boot and BBT partitions remained protected.

The first empty-cache assistance check took approximately 44 seconds on the
NAND-backed system. It succeeded, but interpreter/module loading on this
path is a remaining startup-performance issue. A successful GPS upload still
does not demonstrate a navigation fix.

The packaged programs, units, rules and dependencies were then staged into
the running GPS test kernel's volatile overlay. Hardware checks passed for:

- unassisted gpsd startup with no cached predictions;
- proxy-only HTTPS refresh with certificate validation;
- service-ordered UTC and 31-satellite RAM upload, with all acknowledgements
  accepted and NMEA reception verified;
- gpsd restart and local JSON reports after upload;
- rejection of a concurrent upload without increasing the UART TX count;
- loopback-only GPS listeners and an active refresh timer.

The kernel remained untainted, NAND UBI remained read-only, and no systemd
units were failed at the end of the test. No satellite fix was obtained:
the reports remained at mode 1. These checks establish service integration,
not acquisition-time improvement.
