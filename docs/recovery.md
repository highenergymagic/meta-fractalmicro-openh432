# Accessible recovery

Standalone recovery provides a Grade-1 braille menu, internal-SD reset tools
and a physical USB maintenance shell. It runs from RAM without mounting
systembase, systemext or userdata. It does not start normal system services
or speech. The USB root shell is unauthenticated: this is development policy,
not a production security boundary.

## Build and install

Build `openh432-recovery-image` with the same pinned layers and configuration
as the normal system images. The output is `openh432-recovery.img`, containing
the runtime kernel, board DTB and standalone RAM filesystem. The build and
loader enforce the recovery-volume and boot-envelope size limits.

Factory `/var`, `/home` and `/root` seeds and the systemext descriptor come
from the built immutable systembase, never an installed device. Keep recovery
aligned with the system release when its factory defaults change.

With a recovery-capable U-Boot installed:

```sh
fastboot flash recovery openh432-recovery.img
```

The loader validates the image envelope, recovery marker and volume capacity,
then verifies the written bytes through corrected NAND reads. Recovery is a
single static UBI volume, not A/B. Interrupted updates can leave it unavailable
but do not change normal slots, userdata or the factory loader. Restart the
complete recovery update after correcting a transfer failure. Sparse recovery
images are not accepted. These checks detect corruption, not authenticity.

## Local controls

Enter the bootloader menu with Play during its tactile cue. **Reboot into
recovery** starts the recovery menu; the wipe options start it with the
corresponding action selected. No erase happens automatically on entry.

Dismiss `recovery menu` with a navigation key or Enter. Dot 1 selects the
previous item, Dot 4 the next, and Enter selects it. Actions occur on release;
held keys, repeat events and chords do not confirm operations.

| Item | Effect |
| --- | --- |
| Reboot now | Returns to normal boot |
| Factory reset | Recreates cache and userdata, preserving GPT and both systemext slots |
| Wipe cache | Recreates only the F2FS cache filesystem |

Erase confirmation defaults to `cancel`. Navigate to `erase user data` or
`erase cache`, then press and release Enter. The display reports progress and
completion or failure. Failure never triggers an automatic retry or reboot.
Reboot explicitly after completion. Recovery does not consume A/B attempts
or mark a normal slot successful.

Factory reset removes personal files, settings, SSH host keys, ADB trust and
machine identity. It is filesystem recreation, **not secure erase**. Storage
tools reject mounted partitions and active device-mapper holders and serialize
operations from the menu and maintenance shell.

## Missing storage layout

Neither normal boot nor recovery automatically repartitions a missing or
unrecognized card. Factory reset requires the recognized GPT layout.
Full reprovisioning is a separate USB-shell maintenance operation:

```sh
/usr/libexec/openh432/storage-provision install \
    --factory-root /usr/share/openh432-recovery/factory \
    --extension /path/to/openh432-systemext-h432b.rootfs.erofs.verity \
    --confirm-erase-internal-mmc
```

This replaces **all internal-SD contents**, including extension slots. The
extension must match recovery's embedded descriptor; verification precedes
partition-table replacement. Use recovery and extension artifacts matching the
intended installed systembase. Local installation-media selection is not yet
implemented.

## Diagnostics and validation

The development USB shell operates independently of the local menu. Logs are
in `/run/openh432-recovery-ui.log` and `/run/openh432-recovery-operation.log`
and are lost on reboot.

Source tests cover confirmation, request validation, braille frames, cache
write boundaries and failure without retry. Compilation and physical
qualification are separate checks; consult the
[recovery qualification record](https://github.com/highenergymagic/openh432-build/blob/main/docs/recovery-validation.md)
for tested artifacts and scope.

## Tactile progress

Loading and maintenance screens reserve cells 31–32 for a two-digit
percentage, preceded by a number sign in cell 30. Labels use Grade-1 braille.
The display uses 00–99; a completion message or the next screen replaces it
when the operation finishes.

The loader reports image bytes read, followed by integrity verification.
Recovery startup and formatting report completed operation stages, not elapsed
time or an estimate of remaining seconds. A formatter may remain at the same
percentage while an individual filesystem operation runs. Do not interrupt it
solely because the displayed number is stationary.

Normal Linux startup counts root-handoff and accessibility-service milestones.
The progress writer releases ownership before BRLTTY starts and cannot draw
again during that boot. Once BRLTTY owns the display, all 32 cells are available
to the console.
