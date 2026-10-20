# Persistent storage

## Integration status

Persistent storage is an opt-in image configuration. Build with
`scripts/bsp.py build openh432-nand-b --storage-mode persistent` plus the
usual firmware and speech inputs. The default `volatile` mode retains the
existing temporary root overlay and does not require MMC provisioning.

Persistent images require a provisioned internal SD and the matching system
extension. Do not deploy them to an unprepared device. Installing packages or
booting an image never repartitions or formats storage. The implementation
has disposable-disk and initial hardware provisioning/boot qualification.
Power-loss qualification remains incomplete. The modern loader implements
raw extension writes and combined image verification. An inactive-slot update,
corrupt-extension rejection and subsequent verified NAND boot have passed on
hardware. See [slot updates](#slot-updates) for its limits.

## Storage contract

The internal SD is identified by its H432B controller, not Linux block-device
numbering. The version 1 GPT layout reserves 2 GiB each for `systemext_A` and
`systemext_B`, 4 GiB for `cache`, and the remaining capacity for `userdata`.
System extensions are EROFS images with dm-verity, cache is unverified F2FS,
and userdata is unencrypted Btrfs. Encryption requires a future explicit
migration; plaintext cache must not be mistaken for encrypted user storage.

Each boot selects a kernel, systembase, system extension and configuration
deployment as a matched set. An extension supplements `/usr`; mounting it
directly over the base `/usr` is not supported. A slot letter is not a release
identity. The systembase integrity digest identifies its configuration
deployment. Its immutable `/usr/lib/openh432/systemext.verity` descriptor
identifies the matching system extension. The build produces an EROFS image,
an appended-tree `.erofs.verity` payload and its `.verity` descriptor.

The persistent kernel bundle also contains that extension descriptor in its
DTB, allowing the loader to verify the complete three-image set at activation.

Before starting systemd, the handoff verifies partition geometry, mounts
userdata, creates the selected extension's dm-verity mapping, and combines
its `/usr` with the base `/usr` through a read-only overlay. It then selects
or prepares `/etc` and binds shared state. A mismatch enters initramfs
recovery; it is never interpreted as an installation request.

Shared state is independent of OS rollback:

| State | Runtime path | Policy |
| --- | --- | --- |
| Application/user content | `/data` | Shared; never reverted by OS rollback |
| User home directories | `/home`, `/root` | Shared |
| Service state | `/var` | Shared; backward-compatible migrations required |
| SSH host key | `/var/lib/openh432-ssh` | Shared, root-only; cleared by factory reset |
| Machine identity | `/etc/machine-id` | Shared across deployments; mode `0444` |
| OS configuration | `/etc` | Separate writable deployment directory |
| Scratch space | `/cache` | Disposable; not a source of trusted executable images |

The handoff validates the persistent machine ID and binds it into `/etc`
without regenerating it. It is readable by unprivileged system services;
it is not a credential. SSH private keys retain their
separate root-only permissions.

Applications may store settings at
`/data/data/<application-id>/files/<install-instance-id>/settings.db`.
The storage layer does not inspect, migrate, merge or restore these databases.
SQLite transaction and schema handling belongs to the application. OS rollback
does not roll back `/data`; a factory reset explicitly deletes it.

## Configuration preparation

`/usr/libexec/openh432/config-deployment DEFAULTS DESTINATION` initializes a
deployment containing `defaults`, writable `etc`, and `deployment.json`.
Pass `--previous PREVIOUS_DEPLOYMENT` to reconcile an update. Run as root to
preserve owner IDs, modes and extended attributes. The destination must not
exist; its parent must be canonical, trusted and writable only by root.

The reconciler compares whole filesystem objects, including metadata:

* Unmodified configuration receives the new vendor version.
* Local-only modifications, additions and deletions survive.
* Identical local/vendor changes are accepted.
* Competing modifications or incompatible directory changes abort preparation.

It does not perform textual merges, insert conflict markers, follow symlinks
while copying, overwrite an existing deployment or modify the previous tree.
Conflicts report paths, not configuration contents. Symlinks are preserved as
symlinks; unsupported objects such as FIFOs are rejected. The immutable
baseline is checked before it is used. Output is verified, synchronized and
published by rename only after preparation succeeds. This supplies filesystem
durability boundaries, not a guarantee against defective storage hardware.

The caller must stop configuration writers before final preparation and keep
them stopped through activation. A before/after consistency check detects
many races but is not a replacement for quiescing writers. Interrupted staging
directories are not deployments and must never be selected. Their cleanup is
an offline maintenance operation, not a normal boot task.

Account databases and required boot files need explicit migration/validation
when both local state and vendor defaults change. Conflicts abort the trial
boot before it is acknowledged healthy. The loader verifies images before
selecting a candidate; configuration is prepared from verified defaults in
initramfs during that trial boot. Do not mark the candidate successful before
configuration and mount checks pass. Persistent device identity must
not be regenerated merely because the selected OS deployment changes.

## Slot updates

Update the inactive slot with a matching kernel bundle, appended-tree
systembase and appended-tree system extension from one build. For inactive B:

```sh
fastboot flash systemext_B systemext.erofs.verity
fastboot flash systembase_B systembase.squashfs.verity
fastboot flash kernel_B kernel.img
fastboot set_active b
fastboot reboot
```

Each write invalidates B before modifying storage. MMC writes receive range
readback; NAND updates receive complete-volume readback when all fragments
have arrived. Intermediate fragment acknowledgements are not completion.
`set_active` checks all three images against the kernel descriptors before
persisting B as the trial candidate. Slot A and shared userdata are retained.
The accessible-console health service acknowledges the new boot only after
its configuration and storage checks succeed. No individual flash command
marks a slot successful.

Use the modern loader with the MMC backend and a kernel carrying the extension
descriptor; the earlier NAND-only activation path is not sufficient. The modern
loader supports Android fastboot's automatic sparse splitting of raw images.
The 112 MiB limit applies to each download; complete systembase and extension
images may reach 200 MiB and 2 GiB respectively, including integrity data.
Keep the normal raw build artifacts as inputs to the commands above. See the
[loader transfer contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/modern-uboot.md#fastboot-interface)
for sparse-format restrictions and ordered NAND fragments. Do not retry a
timed-out write blindly; reconnect, inspect the device and verify its state
before restarting the whole image. Interrupted transfers cannot be resumed
from a persisted download offset.

## Provisioning and reset requirements

Provisioning must positively identify the internal controller, verify the
partition plan, and require an explicit installation operation. A layout
mismatch during ordinary boot is a recovery condition, not permission to erase
storage. Factory reset recreates cache and userdata while retaining OS images.
It must operate from initramfs with those filesystems unmounted. The separate
`/usr/libexec/openh432/storage-provision` utility exposes these operations:

```text
storage-provision install --factory-root ROOT --extension PAYLOAD --confirm-erase-internal-mmc
storage-provision factory-reset --factory-root ROOT --confirm-erase-internal-mmc
storage-provision wipe-cache --confirm-erase-internal-mmc
```

`ROOT` is a mounted, verified systembase tree; `PAYLOAD` is the matching
appended-tree EROFS image. These are maintenance interfaces, not a complete
stock-firmware conversion installer. The tool identifies the internal SD
through hardware-layer controller policy and refuses mounted partitions or
active device-mapper holders. Installation replaces its partition table and
all contents. Factory reset preserves the partition table and both extension
partitions, but deletes cache, user content, configuration and machine identity.
Neither operation securely erases flash media.

Provisioning seeds `/var`, `/home` and `/root` from the factory tree, creates
shared subvolumes and a new machine ID, and writes its completion marker last.
An interrupted installation requires explicit maintenance. Configuration
publication and boot acknowledgement are separate durable operations, not
a cross-device atomic transaction. Extension/configuration health is checked
before NAND boot acknowledgement; the configuration last-good pointer is
published afterward. An interruption between those writes can retain the
previous reconciliation baseline and must be handled during maintenance.
The health service can write this marker but retains read-only access to
configuration, identity and user-data subtrees. A persistent machine-ID bind
is already durable and is excluded from systemd's transient-ID commit service.

## Design references

The deployment-local configuration model follows
[OSTree's configuration reconciliation](https://ostreedev.github.io/ostree/deployment/),
without requiring OSTree's boot or repository format. Vendor defaults should
use native `/usr/lib` lookup locations where supported; otherwise retain an
immutable baseline as described in
[systemd's image-building guidance](https://systemd.io/BUILDING_IMAGES/).
