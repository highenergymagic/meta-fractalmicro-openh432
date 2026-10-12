# Systembase integrity

The NAND root uses dm-verity over ubiblock. UBI retains bad-block management,
wear management and NAND ECC; SquashFS remains the immutable lower filesystem
for the volatile runtime overlay. This is corruption detection, not secure
boot or authentication of the bootloader and kernel.

## Build outputs

Build `openh432-nand-b` through the pinned BSP launcher. Its dependencies build
the systembase first, then embed the expected verity descriptor in the handoff
initramfs. Kernel compilation is independent of that descriptor, avoiding an
image/kernel-module dependency cycle.

| Artifact | Purpose |
| --- | --- |
| `openh432-systembase-b-h432b.rootfs.squashfs.verity` | Deployable systembase: padded SquashFS followed by its hash tree |
| `openh432-systembase-b-h432b.rootfs.verity` | Descriptor copied into the matching kernel's initramfs |
| `openh432-nand-b.img` | Kernel bundle bound to that systembase |
| `openh432-systembase-b-h432b.rootfs.squashfs` | Unwrapped filesystem for inspection; not the deployable verity root |

The format uses verity version 1, SHA-256, 4096-byte data/hash blocks and no
verity superblock. The salt is the SHA-256 digest of the original SquashFS.
The descriptor contains version, data-block count, hash-start block, root hash,
salt and combined byte count, in that order. Neither randomness nor build-host
time enters these artifacts. The 200 MiB systembase limit includes the tree.

The pinned native `veritysetup` verifies each generated image. Build-time
vectors also check deterministic output, damaged data, damaged hash blocks and
an incorrect root hash. These tests do not open hardware or require loop devices.

## Installation and compatibility

Deploy the kernel and wrapped systembase as a pair. A raw SquashFS image or a
different build's systembase does not satisfy the embedded descriptor. Both
slot names use the same artifact format; the historical `-b` recipe suffix does
not restrict installation to slot B.

Only systembase volumes use UBI's static-volume skip-CRC-at-open flag. Existing
volumes require recreation with `ubimkvol --skipcheck`; this destroys that
volume's old contents. Migrate the inactive slot only, retain the active pair,
clear the target's attempt allowance before modifying it, and restore its
allowance only after both images pass readback. The capacity remains 1651 LEBs
and the IDs remain 3 for A and 4 for B. Kernel and boot-state volume flags do not
change. UBI still verifies a completed static-volume update.

The target-side
[`install-verity-slot.sh`](https://github.com/highenergymagic/openh432-tools/blob/main/scripts/install-verity-slot.sh)
implements that inactive-slot sequence. It requires matching artifact hashes,
explicit replacement confirmation and a healthy active fallback. It does not
reboot or provide an authenticated update manifest.

## Runtime behavior

The handoff checks descriptor syntax and volume length, opens a read-only
`/dev/mapper/systembase` verity mapping, and mounts it as SquashFS. It never
falls back to mounting the underlying unverified block device. Boot health
requires a valid verity status and the selected slot as the backing device.

Corrupt reads return I/O errors. If root handoff fails while a USB host is
connected, the initramfs provides a physical USB root shell independently of
the systembase. Use the normal console tool to access it. The failure reason,
handoff output and kernel log are retained under `/run/openh432-handoff*`.
Exiting the shell continues the managed boot-attempt/fallback policy. Without
a host, the handoff waits up to ten seconds for enumeration before falling
back. Recovery does not acknowledge boot success, write storage, or mount an
unverified root automatically. Like the development image's USB console,
this recovery shell is unauthenticated and requires physical access.

Corruption discovered after a successful
boot does not automatically change slots or force a reboot; dependent programs
may fail and recovery is required. The tree does not replace ECC or repair
corruption, and no verity FEC is enabled. Protection against an attacker who can
replace both the kernel and its root hash is outside this design's scope.
