# Internal braille console

The standard systembase includes BRLTTY and `FMBraille.service`. The service
starts automatically in the NAND image.
It uses the H432B kernel display/input drivers, not an emulated serial port.

## Operation

On a compatible runtime kernel:

```sh
systemctl start FMBraille
systemctl status FMBraille
journalctl -u FMBraille
systemctl stop FMBraille
```

While running, BRLTTY exclusively owns the display and the keyboard/routing
evdev devices. Stopping it releases those devices. The power key and selectors
remain outside its ownership.

Configuration is in `/etc/brltty.conf`. The default uses the Linux console
screen backend, the H432B braille backend and the en-nabcc text table.
The build omits the optional capability/user-creation scripts and external
Python latex-access translator; it does not install their runtime dependencies.
Contraction, application policy, notification modes and keypad locking are
not configured. Do not run another raw-GPIO display writer concurrently.

## Privileges and application API

The service currently runs as root for the board device and console access.
BrlAPI is restricted to a local Unix socket and root peer authentication,
under the private `/run/brltty` directory. No TCP listener, shared secret
or network-accessible braille service is configured.

Application-specific access and privilege reduction require separate policy.
Runtime configuration remains subject to the image's volatile overlay.

## Scope

The operator confirmed readable virtual-console output, key entry at the
login prompt and scroll-key navigation. Routing and broader chord coverage
remain unqualified. Root's password is locked by default; this service does
not create accounts, set passwords or enable automatic console login. See the
[hardware interface](https://github.com/highenergymagic/meta-fractalmicro-H432B/blob/main/docs/braille.md)
for electrical and transport qualification limits.
