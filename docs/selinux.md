# SELinux integration

## Availability and security boundary

The standard systembase includes a targeted SELinux policy through the pinned
`meta-selinux` layer. It boots in **permissive mode**: policy violations are
recorded, not blocked. Unix permissions, service sandboxes and D-Bus caller
checks remain independent controls. This configuration is not a production
application-isolation policy.

The distribution selects `refpolicy-targeted` and policy format 33 for Linux
6.12. `OPENH432_SELINUX_MODE` accepts `permissive` or `enforcing`, but enforcing
boot is not qualified and must not be presented as a supported release mode.
The settings daemon has its own `fm_settings_t` domain and database label;
there is no corresponding complete policy for future application identities.

## Immutable policy and filesystem labels

Policy is installed under `/usr/share/openh432/selinux`; `/etc/selinux` points
there. Policy therefore follows the selected, verity-protected OS deployment
rather than shared writable state. Runtime policy editing is not the update
interface.

Base and extension filesystems receive labels during image generation, before
verity hashing. Portable text file contexts are shipped instead of compiled
context caches tied to the build host's word size.

`FMSELinuxState.service` labels writable state when the build-generated policy
identity changes. It records completion only after relabeling succeeds. The
ephemeral root receives the immutable root's label on every boot; this does
not recursively relabel the immutable image or rehash the policy from NAND.
Configuration merging treats SELinux labels as vendor metadata, while file
content, ownership, capabilities and other extended attributes retain their
normal three-way merge semantics.

Policy updates must preserve access to shared `/var`, homes and application
data across supported A/B rollback versions. A matching label marker is not
proof of policy coverage or power-loss durability.

## Diagnostics

```sh
sestatus
auditctl -s
ausearch -m AVC -ts boot
systemctl status FMSELinuxState.service
```

Run these through a trusted administrative console. `auditd` writes root-only
records to `/var/log/audit/audit.log`, rotating at 8 MiB with three files
retained. Raw records avoid name-service lookups on the logging path. Low-space
or disk-error conditions suspend file logging instead of halting the device.
Early events and events while the collector is unavailable can still reach
the kernel log. A quiet `dmesg` does not demonstrate correct enforcement.

## Qualification

Hardware checks cover policy loading, the settings domain transition,
executable/database labels, persistent-state labeling and the existing D-Bus
authorization checks. Enforcing-mode boot, complete service/application policy,
policy rollback compatibility and enforcement across suspend/resume remain
unqualified. Do not generate broad allow rules solely to silence audit output.
