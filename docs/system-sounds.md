# System sound services

The `openh432-system-sounds` package supplies `FMBootSound.service` and
`FMShutdownSound.service`. Image policy selects enablement:

| Image | Policy |
| --- | --- |
| `openh432-systembase-b` | Assets included; boot/shutdown services enabled |
| `openh432-ram-dev` | Quiet; sound services not selected |
| `openh432-hardware-test` | Assets and explicit sound-test policy enabled |

These are bounded system cues, not an audio session manager. In a custom
image, before enabling, qualify speaker/headphone routing and provide
/usr/share/openh432/sounds/startup.wav and shutdown.wav as 44.1 kHz stereo
S16_LE PCM. Create /etc/openh432/system-sounds.enabled only after those checks.
The player uses card OpenH432, analog volume 45 (below the kernel ceiling 50),
and mutes outputs after playback. Playback is bounded by systemd timeouts.

The shutdown unit is armed at boot and runs its stop action before filesystem
and sound targets stop. The helper plays only when systemd reports stopping,
not on an ordinary service stop/restart. A marker enables timeout cleanup
without muting unrelated audio when the service never started playback.
Shutdown sound is best-effort; it cannot precede an independent hardware cutoff.
Live startup playback and shutdown playback during a systemd reboot have
both been heard and confirmed by the operator. Electrical poweroff is separate.
Shutdown latency still needs qualification with continuous console capture.

## Asset provenance

The selected KDE files exactly match kdebase 3.5.10's official archive:
https://download.kde.org/Attic/3.5.10/src/kdebase-3.5.10.tar.bz2

Archive SHA256:
77aa9d8f28c532f2e7a5157a7f4ba8df1001f00fa1cb72cb70b388b3d0e16b61

Members under kdebase-3.5.10/kcontrol/knotify/sounds/:

- KDE_Startup_1.ogg: d9bc793b2d1ced1728862cdd01274f943291dabf4eb4215725251d15a3133c73
- KDE_Logout_1.ogg: e0bd2e7efe63345e82412032b8aebc8d41be6d0756400f53884ddd8250832d9d

The separate meta-fractalmicro-assets layer packages these files using the
archive's GPLv2 COPYING as its documented package-level licensing basis.
No sound-specific author/license notice has been established; this distinction
is retained in that layer. Original Ogg files and COPYING accompany the WAVs.
Our MIT integration metadata does not relicense the recordings.

## Validation and limits

Startup and systemd-reboot shutdown playback have been heard on hardware.
The normal NAND base includes assets and policy, but NAND-backed startup has
exhibited underruns. Buffering and startup latency need further qualification.
A shutdown cue cannot guarantee electrical poweroff or complete before an
independent hardware cutoff.
