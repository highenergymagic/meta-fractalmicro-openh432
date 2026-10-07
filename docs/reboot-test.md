# Reboot and maintenance integration

Reboot-mode support is part of the normal runtime kernel and maintenance
bootloader. Use the normal NAND or standalone RAM composition below.

For a complete standalone RAM environment, build `openh432-fastboot-ram`.
It uses the runtime kernel and the `openh432-ram-dev` root filesystem;
it does not require a NAND systembase. Its output remains
`openh432-ram-boot.img` for compatibility with the host workflow.

For normal NAND boot, build `openh432-nand-b` and `openh432-systembase-b`.
The kernel bundle includes only the minimal root-handoff initramfs.

See the [BSP reboot-mode contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/reboot-mode.md)
for request values, qualification limits and optional diagnostics.
