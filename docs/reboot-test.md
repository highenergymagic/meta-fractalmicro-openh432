# Reboot-mode development

Reboot-mode support is part of the normal runtime kernel and maintenance
bootloader. The former standalone reboot-test image has been retired.

For a complete standalone RAM environment, build `openh432-fastboot-ram`.
It uses the runtime kernel and the `openh432-ram-dev` root filesystem;
it does not require a NAND systembase. Its output remains
`openh432-ram-boot.img` for compatibility with the host workflow.

For normal NAND boot, build `openh432-nand-b` and `openh432-systembase-b`.
The kernel bundle includes only the minimal root-handoff initramfs.

See the [BSP reboot-mode contract](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/reboot-mode.md)
for request values, qualification limits and optional diagnostics.
Historical test results remain in Git history, not as extra image targets.
