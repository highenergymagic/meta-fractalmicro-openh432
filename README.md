# meta-fractalmicro-openh432

Fractal Microsystems' OpenH432 operating-system policy layer for Yocto 6.0
Wrynose. Hardware support is separate in
[meta-fractalmicro-H432B](https://github.com/highenergymagic/meta-fractalmicro-H432B).
Use [openh432-build](https://github.com/highenergymagic/openh432-build) for
pinned container builds. Metadata and new policy files are MIT.

Current target: `openh432-ram-dev`, a full glibc/systemd OS in initramfs,
not an installer and not an initrd that switches to persistent storage.
The RAM image uses XZ/CRC32 with a fixed compressor thread count and remains
within the qualified loader's 16 MiB compressed slot. Image metadata and
artifact names derive from the pinned build epoch. Required systemd tools
and dynamically loaded seccomp/ACL/Zstd libraries are explicitly installed;
content guards reject incomplete images despite recommendations being off.
A real U2 RAM boot passed systemd health, read-only hardware checks and a
bounded seccomp/cgroup/filesystem-isolation smoke test. This is not full
security qualification or an installed firmware release.

The development policy exposes an unauthenticated physical USB root shell.
It must not be included in production images.

No automatic storage mounting, partitioning, UBI attachment, filesystem
formatting or firmware updates are configured. Repart is gated, GPT automatic
discovery is disabled and the BSP retains kernel-level storage write guards.
No sound is played automatically.

Production/recovery/systembase/systemext images and coordinated A/B updates
are planned, not implemented. Accessibility services still need bring-up.
Using systemd or Yocto alone does not make this a secure production OS.
