# Android Debug Bridge

## Availability

`openh432-adbd` provides the Android 16 daemon on GNU/Linux. The standard
systembase includes its development tools, disabled by default. A local virtual
console provides connection-only approval through BRLTTY. Settings integration
and release-policy qualification remain pending; this is not yet the release
USB policy.

The recipe pins the daemon and its AOSP dependencies to the Android 16.0.0 r4
source composition. It builds with the BSP's OpenEmbedded toolchain on the
pinned build host. Android system services, a property daemon and the Android
application runtime are not required.

## Security boundary

The port retains AOSP's signature verification and authentication state
machine. It requires an unprivileged service identity and a systemd-supplied
authentication socket. Missing FunctionFS endpoints cause startup failure;
there is no automatic TCP listener, environment-selected port or root mode.

Approved public keys are read from `/var/lib/openh432-adb/adb_keys`, without
following a symlink. Deployment must keep the directory and file root-owned
and non-writable by the daemon or appliance account, while permitting daemon
read access. Persistent installations must retain this state across slot
updates and erase it during factory reset. Enabling debugging and approving a
host are separate decisions; neither is implied by connecting a cable.

The authentication channel is a root-accessible Unix sequential-packet socket
at `/run/openh432-adb/auth`. The local approval broker supplies the Android
framework's approval/rejection role. No automatic acceptance policy is provided.
SELinux enforcement and app-level isolation require separate qualification.

## Local approval

When debugging is explicitly enabled, an unknown host opens a prompt on the
root-owned virtual console `tty8`. BRLTTY exposes that console through braille
and speech. The prompt shows a SHA-256 fingerprint of the validated public key,
not the host-supplied name or comment. Type `yes` and Enter to allow the current
connection, or `no` and Enter to deny it. Other input and a 60-second timeout
deny access. The previous console is restored afterward; switching away from
the prompt or losing the USB connection also cancels approval.

This prompt never remembers a host. Reconnection requires fresh approval unless
an administrator separately provisions its public key. It is a privileged local
console, not an API granting approval rights to all applications running as the
appliance user. The development image's root maintenance interfaces remain
privileged and must be replaced or restricted by the release USB policy.

## Host-key administration

The privileged `fm-adb-keys` utility manages explicitly provisioned public keys:

```sh
fm-adb-keys add /path/to/adbkey.pub
fm-adb-keys list
fm-adb-keys remove SHA256:host-fingerprint
fm-adb-keys clear
```

It validates Android's public-key encoding, discards host-supplied comments,
rejects unsafe trust-store ownership and permissions, and commits changes with
an atomic replacement and directory synchronization. Mutations restart an
already running daemon and rebind its FunctionFS gadget to invalidate existing
sessions; they do not enable debugging. A restart failure is reported even if
the key update was committed.
Only public keys belong here. Never copy a host's private `adbkey` file onto
the device. The command is an administrative interface, not a substitute for
an application-facing authorization API.

## Development USB handoff

With independent network access established, an administrator can select ADB:

```sh
fm-adb-usb start
```

The helper stops the development serial console, prepares FunctionFS, starts
the unprivileged daemon, and binds USB only after its endpoints are available.
Setup failure attempts to restore the previous serial-console binding.
An unknown host requires local approval; remembered hosts require separate key
provisioning. USB connection never grants access by itself. To end the session
and restore that development console:

```sh
fm-adb-usb stop --restore-console
```

Without `--restore-console`, stop leaves USB disconnected. This manual helper
does not change the next boot's USB policy. The kernel retains its built-in
serial gadget for initramfs recovery. The ADB composition uses the Linux
composite development USB identity; a production VID/PID allocation is still
required. It presents the board identity supplied through the device tree (not
a verified manufacturer serial number), manufacturer “Fractal Microsystems”
and product “Braille Sense U2 (ADB development)”.

## Scope

The first integration target is authenticated USB shell and file transfer.
Wireless TLS pairing, mDNS, MTP and Android application installation are not
provided by this build target. The upstream no-JDWP implementation is selected
only for the process-tracking translation unit; the daemon is not compiled as
Android recovery and authentication is not bypassed.

The release USB policy must be qualified with absent, unauthorized and authorized
hosts, reconnects, key revocation, suspend/resume and root-mount recovery before
replacing the development serial console. Source tests and compilation alone do
not establish that qualification.

Development hardware tests have demonstrated refusal of an unknown key,
an unprivileged shell with a provisioned key, checksum-matched file transfer,
session termination on revocation, and restoration of the serial console.
The local prompt has also demonstrated explicit approval, denial and timeout on hardware.
These checks do not qualify wireless pairing or SELinux confinement.

The integration requires exact success from the upstream TLS key-comparison
API and rejects allocation/setup failures and negative comparison results.
Offline compiled vectors cover these cases. This hardening does not enable or
qualify a wireless listener.
