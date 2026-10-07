# OpenH432 distribution layer

Yocto/OpenEmbedded distribution policy and image definitions for OpenH432,
maintained by Fractal Microsystems. This layer supplies glibc/systemd
userspace, service configuration and image assembly.

Board drivers, device trees and bootloader support are maintained in
[meta-fractalmicro-H432B](https://github.com/highenergymagic/meta-fractalmicro-H432B).

## Build integration

| Setting | Value |
| --- | --- |
| Distribution | `openh432` |
| Supported machine | `h432b` |
| Yocto series | Wrynose |
| C library / init | glibc / systemd |

Use [openh432-build](https://github.com/highenergymagic/openh432-build) for the
pinned layer composition and build commands. The composition includes
OpenEmbedded Core, meta-oe, the hardware layer and
[meta-fractalmicro-assets](https://github.com/highenergymagic/meta-fractalmicro-assets).
The assets layer supplies separately licensed system sounds.

## Images

| Recipe | Purpose |
| --- | --- |
| `openh432-nand-b` | Slot-B kernel, device tree and minimal root-handoff initramfs |
| `openh432-systembase-b` | Separate SquashFS system userspace |
| `openh432-fastboot-ram` | Standalone RAM environment for recovery and development |

The NAND kernel mounts the slot-matched systembase and starts systemd.
Writable runtime state uses a volatile overlay; persistent userdata and
coordinated A/B updates are not implemented. Additional images and their
prerequisites are listed in the
[target catalogue](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/targets.md).

## Configuration and reference

- [Runtime policy](docs/runtime.md): root filesystem, services and state lifetime.
- [Braille console](docs/braille.md): internal display, keyboard ownership and local-console integration.
- [Remote access](docs/remote-access.md): maintenance SSH and credentials.
- [System sounds](docs/system-sounds.md): packages, playback and volume policy.
- [GPS service](docs/gps.md): receiver ownership and assistance configuration.
- [Support matrix](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md): feature availability and limitations.
- [Installation](https://github.com/highenergymagic/openh432-tools/blob/main/docs/installation.md): image deployment and recovery prerequisites.

Development images expose an unauthenticated physical USB root console.
They are not production images or a complete accessible firmware replacement.

## Licence

New metadata and policy files are MIT-licensed. Packaged software, firmware
and media retain their respective upstream licences.
