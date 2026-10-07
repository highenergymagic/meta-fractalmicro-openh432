# GPS and assisted acquisition

The NAND systembase composition includes gpsd, its command-line clients, and
the OpenH432 AGPS service package. Device drivers and UART/power descriptions
remain in the hardware layer. Normal runtime and GPS diagnostics share receiver sequencing. Use matching
kernel and systembase artifacts from the pinned composition; gpsd requires
the UART and power support supplied by the hardware layer.

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
not implemented by these services. The receiver power driver keeps
the receiver powered. A successful upload does not prove satellite reception
or faster time to first fix.

## Validation and limits

The installed slot-B system passed local gpsd reports, proxy HTTPS refresh,
UTC and 31-satellite acknowledged RAM assistance, and NMEA recovery afterward.
Empty-cache startup, loopback-only listeners and rejection of concurrent
uploader access have also passed.

No satellite fix or improved acquisition time is demonstrated. NAND-backed
interpreter startup has been slow (an empty-cache check took about 44 seconds
in one test); service ordering and cold-load latency require further work.
Time-policy expiry, volatile cache and unimplemented receiver PM remain
operational limitations.
