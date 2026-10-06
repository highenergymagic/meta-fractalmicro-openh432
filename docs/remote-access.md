# Maintenance SSH

The development systembase-B image includes `openh432-maintenance-ssh`,
built from the Dropbear version and checksum in the pinned OE-Core recipe.
It is a root maintenance console, not a production multi-user access policy.

`FMRemoteAccess.service` starts only when an operator has provisioned a
nonempty `/root/.ssh/authorized_keys`. Password login and local/remote TCP
forwarding are disabled. No operator keys, passwords or device host keys
are compiled into the image or stored in this repository. Telnet is not used.

Provision public keys through an already trusted local console. Create
`/root/.ssh` owned by root with mode 0700 and `authorized_keys` with mode
0600. Preserve any existing authorized keys. Then start the service:

```sh
systemctl start FMRemoteAccess.service
systemctl status FMRemoteAccess.service --no-pager
/usr/libexec/openh432-ssh/dropbearkey -y -f /run/openh432-ssh/host_ed25519
```

Obtain the host public key through that trusted console and pin it in the
operator's SSH known-hosts file before connecting over the network. Connect
as root with the corresponding private operator key; use strict host-key
checking and disable fallback password authentication.

The service listens on TCP port 22. Use a trusted maintenance LAN.
The current root overlay is volatile: provisioned keys disappear on reboot,
and the service generates a fresh Ed25519 host key in `/run`. A restart also
recreates its runtime directory. Reprovision and repin explicitly after
restart/reboot. Do not disable host-key verification to hide that change.
Persistent per-device identity requires a separately designed data partition
policy; a shared image must never contain a shared private host key.

## Volatile-overlay qualification payload

The recipe also deploys `openh432-maintenance-ssh.tar`, containing only its
executables and systemd unit. It contains no credentials and is not a rootfs
or firmware image. It permits qualification in a RAM overlay without writing
NAND. Its shared-library dependencies must already be present from the same
pinned userspace build; do not use it with an arbitrary rootfs.

For a running-device test, transfer the payload using a trusted local path,
verify its SHA-256 against the build host over the existing trusted console,
inspect its paths, and extract it only into the intended volatile overlay.
Run `systemctl daemon-reload`, provision a public key and start the service
as above. Do not overwrite an existing SSH service or authorized-key file.

Qualify a key-authenticated session and host-key verification while USB is
still attached before disconnecting USB. This is especially important when
using SSH to observe the battery changing from external power to discharge.

## Qualification

The package built with the pinned OE toolchain and passed package QA.
The systembase-B image includes the service's enablement link but no operator
keys. A volatile-overlay test passed a key-authenticated Ethernet login with
a host key obtained over USB and strict verification. A password-only request
was rejected with public-key authentication as the only offered method.
Systemd remained healthy, UBI read-only and the kernel untainted. The same
procedure was repeated after a RAM-kernel reboot; DHCP assigned a different
address, which was obtained from the device's local console before connecting.
This is runtime-payload qualification, not installation of the rebuilt base
image or qualification of persistent identities.
