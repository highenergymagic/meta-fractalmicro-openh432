# Reboot-mode RAM qualification image

`openh432-reboot-test` packages the separate experimental reboot-mode kernel
and device tree with the normal development initramfs. It uses the existing
Android-v2 fastboot envelope format, not an Android userland.

Build explicitly through the pinned build launcher with the matching hardware
layer providing `linux-h432b-reboot-test`:

```sh
python3 scripts/bsp.py build --local-layers openh432-reboot-test
```

The output is `openh432-reboot-test.img`. The default RAM image and NAND
carrier recipes are unchanged. This is not an installer, a CE carrier, or
a NAND partition image; use only the qualified RAM boot transport.

## Validation

The pinned native-amd64 build completed 2,860 tasks. Correcting the recipe's
source-directory declaration and rebuilding preserved the image bytes:
SHA256 `5d7dc8ebb2a9e2caf73531513d5cd50a5a65133e07b3ddd03dd84e8e37c61dba`.

On the qualification device, the image reached the diagnostic USB shell with
zero failed services, no kernel taint, and the syscon reboot-mode driver bound.
A userspace bootloader reboot argument survived into the existing bootstrap.
A separately staged RAM consumer cleared that request and entered fastboot.
The combined automatic persistent boot chain is not installed or qualified.
These results do not establish cross-host reproducibility for this new image.
