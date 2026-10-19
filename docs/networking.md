# Network management

## Composition

The standard systembase selects NetworkManager, its Wi-Fi plugin and `nmcli`,
with the existing wpa_supplicant backend. NetworkManager owns Ethernet and
Wi-Fi addressing, DHCP and connection profiles. systemd-resolved supplies DNS.
networkd is not installed in this composition, and its units and the standalone
`wpa_supplicant@wlan0` instance are masked. Diagnostic images retain networkd.

Network startup is ordered after the local accessibility target and regulatory
setup. No online-wait service gates local login, braille or speech. Connectivity
probes, cellular support, cloud setup and desktop applets are not selected.

DNS resolver initialization also follows local accessibility readiness. The
resolver retains its ordering before network and name-lookup targets, together
with its upstream sandbox and shutdown behavior.

The manager does not add unsupported driver features such as roaming or WPA3.
The internal radio advertises WPA2-PSK authentication; supplicant filters
alternative authentication suites against the station driver's capabilities.

The supplicant integration honors the kernel's zero-length scan-IE capability:
it omits automatically generated Probe Request elements when hardware cannot
carry them. Explicit caller-provided elements retain normal driver validation.
This does not add WPS, P2P or custom probe-content support.

## Persistent state

Connection keyfiles are stored in
`/var/lib/NetworkManager/system-connections`, not deployment-local `/etc`.
The directory is root-only. NetworkManager's own state and secret key also
remain under shared `/var/lib/NetworkManager`. Forgetting a network therefore
survives OS rollback. Factory reset clears the shared state; volatile images
do not retain it across reboot. Network credentials are not copied into the
Fractal Microsystems settings database.

## Access

Root may administer networking. Polkit grants the appliance `user` account
network enable/disable, Wi-Fi scanning, connection activation and profile
editing. The PAM-free console does not register a logind session, so this is
account-based authorization, including any authorized remote session for that
account. Other unprivileged accounts receive no automatic grant. This is not
isolation between applications running under the same account. No unrestricted
root shell or general administrative
authorization is granted by this rule.

```sh
nmcli general status
nmcli device status
nmcli device wifi list
nmcli --ask device wifi connect NETWORK_NAME
nmcli connection show
```

Use `--ask` rather than placing passwords in shell command arguments. The
future accessible settings UI should use NetworkManager's D-Bus API.

## Board policy

The internal radio uses its permanent address: scan randomization and connection
MAC cloning are disabled for `rtl8712s`. Connected-station power saving is
disabled because the driver does not implement it. Wi-Fi uses a higher route
metric than ordinary wired connections. These defaults are not a claim that
NetworkManager's radio toggle electrically removes power; that path requires
hardware verification.

## Qualification

The installed standard image has passed Ethernet DHCP/DNS, local accessibility,
service-health, Wi-Fi scanning, WPA2-PSK association and Wi-Fi-bound ICMP traffic
checks. Appliance-account radio off/on followed by reconnection also passes.
The root-only profile survives image replacement and reboot. Automatic
reconnection and Wi-Fi-bound traffic pass after software reboot and power-button
suspend/resume. These checks do not establish throughput or access-point
interoperability.
Scan signal percentages are unavailable from this driver and must not be
interpreted as measured zero signal strength.
