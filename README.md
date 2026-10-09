# OpenH432 distribution layer

Yocto/OpenEmbedded distribution policy and image definitions for OpenH432,
maintained by Fractal Microsystems. This layer supplies glibc/systemd
userspace, service configuration and image assembly. The standard NAND image
starts an interactive BRLTTY console and automatically logs in the local
appliance account `user`.

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
The assets layer supplies separately licensed system sounds and speech data.

## Images

| Recipe | Purpose |
| --- | --- |
| `openh432-nand-b` | Slot-independent kernel bundle and loader-selected root handoff |
| `openh432-systembase-b` | Separate SquashFS system userspace |
| `openh432-fastboot-ram` | Standalone RAM environment for recovery and development |

The NAND kernel mounts the slot-matched systembase and starts systemd.
The same image pair supports either slot; historical `-b` recipe names remain
for compatibility. A health-gated service acknowledges successful managed
boots. Writable runtime state remains volatile; persistent userdata and a
signed update installer are not implemented. Additional images and their
prerequisites are listed in the
[target catalogue](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/targets.md).

## Configuration and reference

- [Runtime policy](docs/runtime.md): root filesystem, services and state lifetime.
- [Braille console](docs/braille.md): internal display, keyboard ownership and local-console integration.
- [Remote access](docs/remote-access.md): maintenance SSH and credentials.
- [Offline speech](docs/speech.md): voice packages, local client API and audio policy.
- [Optional OpenEVV](docs/openevv.md): restricted build inputs and evaluation interface.
- [System sounds](docs/system-sounds.md): packages, playback and volume policy.
- [GPS service](docs/gps.md): receiver ownership and assistance configuration.
- [Support matrix](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md): feature availability and limitations.
- [Installation](https://github.com/highenergymagic/openh432-tools/blob/main/docs/installation.md): image deployment and recovery prerequisites.

Development images expose an unauthenticated physical USB root console.
They are not production images or a complete accessible firmware replacement.

## Licence

New metadata and policy files are MIT-licensed. Packaged software, firmware
and media retain their respective upstream licences.
