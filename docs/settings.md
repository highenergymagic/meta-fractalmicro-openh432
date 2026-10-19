# System settings

## Interface and ownership

`openh432-settings` supplies a native D-Bus service and the `settings` CLI.
It stores registered Fractal Microsystems preferences, not network credentials,
Bluetooth pairing records or application databases. NetworkManager and BlueZ
retain ownership of their native configuration and trust records.

```sh
settings list global
settings get global org.fractalmicro.braille.BrailleDisplayEnableEightDotMode
settings put global org.fractalmicro.braille.BrailleDisplayEnableEightDotMode 0
settings reset global org.fractalmicro.braille.BrailleDisplayEnableEightDotMode
```

Boolean values are exactly `0` or `1`. Unknown keys, incorrect scopes and
invalid values fail without changing stored state. Successful writes are quiet;
reads print the value and lists print `key=value` lines. Exit status is zero on
success, one on a service error and two for invalid command syntax.

## Registered preferences

| Scope | Key | Type | Default | Consumer status |
| --- | --- | --- | --- | --- |
| `global` | `org.fractalmicro.braille.BrailleDisplayEnableEightDotMode` | Boolean | `1` | Stored preference; not yet applied to BRLTTY presentation |
| `secure` | `org.fractalmicro.usb.DebuggingEnabled` | Boolean | `0` | Stored preference; no ADB or USB-mode consumer yet |

These initial registrations establish storage and authorization contracts.
Changing either preference does not currently reconfigure hardware. In
particular, the braille preference must not mask cursor dots or transform raw
computer-braille output. Debugging preference is not host authorization.

## Authorization

The service authenticates the caller through the system bus. All callers may
read `global`; root and the appliance account UID 1000 may modify it. Only root
may read or modify `secure`. This is an explicit initial policy, not a claim of
application isolation: programs running as UID 1000 share that authority.
An eventual privileged settings UI requires a separately reviewed policy.

SELinux policy defines a separate `fm_settings_t` service domain and
`fm_settings_data_t` database label. These constrain service access; they do
not replace per-operation D-Bus authorization or grant a UI permission to change
secure settings. The qualification configuration is permissive and therefore
does not enforce those constraints. Application identities and delegated secure
settings authorization remain separate integration work.

See [SELinux integration](selinux.md) for policy composition, filesystem
labeling, audit collection and enforcement qualification.

`secure` denotes authorization, not encrypted storage. Do not put secrets in
this API. Secure values are omitted from broadcast notifications. The database
and its journal files are accessible only to the root-owned service.

## Persistence and rollback

Overrides live in `/var/lib/fractalmicro/settings/settings.db`. Immutable
defaults and the registry are compiled into the service. Reset deletes an
override, so subsequent reads use the default supplied by the running OS.
SQLite transactions use WAL and full synchronization; a revision counter is
committed with each successful mutation. OS rollback does not roll back `/var`.
Schema changes must remain compatible with supported rollback versions; this
implementation rejects a newer schema rather than rewriting it.

Persistent-storage installations retain settings across reboot and slot changes.
Volatile installations do not. Factory reset clears settings with userdata.
SQLite durability does not establish hardware power-loss qualification.

## D-Bus API

Bus/interface: `org.fractalmicro.Settings1`; object: `/org/fractalmicro/Settings1`.

| Method | Inputs | Result |
| --- | --- | --- |
| `Get` | scope, key (`ss`) | canonical value (`s`) |
| `Put` | scope, key, value (`sss`) | committed revision (`t`) |
| `Reset` | scope, key (`ss`) | committed revision (`t`) |
| `List` | scope (`s`) | effective registered values (`a{ss}`) |

`Changed(scope, key, value, revision)` (`ssst`) is emitted after a global write
commits. Clients subscribe before reading initial state and reread after service
reconnection; notifications are not a durable event queue. The service stores
desired preferences only. Consumers remain responsible for reporting effective
state and application failures through their own interfaces.

## Validation scope

The native database tests cover value validation, persistence, reset, revision
overflow rollback and rejection of newer schemas. On-device D-Bus tests cover
appliance-account global writes, secure-scope denial, privileged secure access,
invalid requests and persistence across a service restart and an installed-image
reboot. A/B rollback and abrupt power-loss durability require separate qualification.

SELinux policy loading, the settings domain transition and executable/database
labels have been checked on hardware in permissive mode. These checks do not
establish an enforced application boundary.
