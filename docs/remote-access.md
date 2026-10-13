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
/usr/libexec/openh432-ssh/dropbearkey -y -f /var/lib/openh432-ssh/host_ed25519
```

Obtain the host public key through that trusted console and pin it in the
operator's SSH known-hosts file before connecting over the network. Connect
as root with the corresponding private operator key; use strict host-key
checking and disable fallback password authentication.

The service listens on TCP port 22. Use a trusted maintenance LAN.
The host key is generated once in `/var/lib/openh432-ssh/host_ed25519`.
Systemd creates its root-owned directory with mode 0700; the key has mode 0600.
Generation is serialized and the validated key is atomically published after
syncing it. An invalid existing key stops the service instead of rotating its
identity. Service restarts reuse the same key.

In persistent-storage mode, shared `/var` retains the host key across reboots,
image updates and slot rollback. Shared `/root` retains authorized keys. A
factory reset clears both. In the default volatile-storage mode, both are
lost on reboot. Persistent mode is therefore required for durable remote-access
identity; machine ID alone does not provide it.

Upgrading from the older runtime-key service creates a new persistent key on
its first start. Obtain and pin that new public key through the trusted local
console. Do not disable host-key verification to hide an unexpected change.
Both eligible OS slots must use this service policy for stable SSH identity
across rollback. An older image that still reads its key from `/run` does not
automatically adopt the persistent key, even though the file is retained.
A shared image must never contain a private host key.

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
still attached before disconnecting USB. Verify independent network access before removing a diagnostic USB connection.

## Qualification

Key-authenticated sessions and strict host-key verification passed over
Ethernet and Wi-Fi. Password-only authentication was rejected. The normal
systembase includes the key-gated service; no credentials are shipped.
Persistent identity has source tests for reuse, failed generation, malformed
keys and unsafe permissions. On hardware, the installed helper retained a
pre-update public host identity through a kernel/base/extension update and
an ordinary software reboot. This test exercised systemd state-directory
creation and key preparation without enabling a network listener. Multi-user
policy and untrusted network exposure are not qualified.
