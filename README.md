# meta-fractalmicro-openh432

Operating-system policy and image recipes for OpenH432, a Linux-based
operating system in development for the HIMS BrailleSense U2.

This Fractal Microsystems layer defines the software environment above
the board support package. It uses Yocto/OpenEmbedded, glibc and systemd,
with hardware support maintained separately in
[meta-fractalmicro-H432B](https://github.com/highenergymagic/meta-fractalmicro-H432B).

## What this layer provides

- Distribution configuration for `DISTRO = "openh432"`.
- Package selection and development image composition.
- systemd service and access policies.
- Image packaging and checks on required contents and size.

Hardware drivers, device trees and bootloader patches belong to the BSP
layer. Container configuration and source revision locks belong to
[openh432-build](https://github.com/highenergymagic/openh432-build).

## Development images

The current operating system is a RAM-resident development environment,
not a production installation or an installer.

| Target | Purpose |
| --- | --- |
| `openh432-ram-dev` | A glibc/systemd development system packaged as an initramfs. |
| `openh432-fastboot-ram` | The kernel, device tree and development initramfs packaged for the BSP's fastboot RAM loader. |

The fastboot bundle uses an Android boot-image header for compatibility
with the host tool; the operating system itself is not Android.

The development system has booted on a U2 and passed systemd health and
selected service-isolation checks. A boot from NAND still runs this
initramfs; it does not imply a transition to a persistent production root.

## Building

Follow the [build guide](https://github.com/highenergymagic/openh432-build#building)
for the pinned container workflow and exact layer revisions. This layer
targets Yocto Wrynose.

Builds only produce artifacts. They do not connect to or modify a device.

## Development access and limitations

**Development images expose an unauthenticated root shell over physical
USB. They are not suitable for production use.**

Default storage access is protected against writes. Images do not
automatically partition disks, format filesystems or install firmware.
Hardware bring-up and accessibility services remain incomplete.

Production and recovery images, persistent system storage, and coordinated
A/B updates are still under development. See the
[validation status](https://github.com/highenergymagic/openh432-build/blob/main/docs/status.md)
for completed tests and current limitations, and the
[BSP boot contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/boot-contract.md)
before attempting to boot an image.

## License

New metadata and policy files are MIT-licensed. Software included in the
images retains its own upstream licenses.
