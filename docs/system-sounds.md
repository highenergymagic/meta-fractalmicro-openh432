# System sound services

The `openh432-system-sounds` package supplies `FMBootSound.service` and
`FMShutdownSound.service`. Image policy selects enablement:

| Image | Policy |
| --- | --- |
| `openh432-early-b` | RAM-resident startup cue during root preparation |
| `openh432-systembase-b` | Shutdown cue and fallback startup service |
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

## Early NAND startup

The root-handoff initramfs includes only the startup asset, its source/licence,
and the shared ALSA player/mixer dependencies. It does not include systemd or
the full userspace. Playback runs alongside root preparation, with a 20-second
timeout and bounded cleanup; handoff waits for the helper to finish.

Successful playback creates `/run/openh432-startup-sound.done`. The handoff
preserves this volatile marker and its diagnostic log across switch-root.
`FMBootSound.service` skips playback when the marker exists; failure leaves
the normal userspace fallback available. Neither path changes the volume cap.
Shutdown playback remains in the systembase.

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
The initramfs startup path has completed without reported underruns on
successive normal NAND boots and was confirmed audibly clean. The completion
marker suppresses duplicate userspace playback. Exact artifact scope and
measurements are recorded in the
[hardware validation record](https://github.com/highenergymagic/openh432-build/blob/main/docs/hardware-validation.md).
These checks do not qualify playback under arbitrary concurrent workloads.

Playback started after deep-sleep resume has also passed, including an audible
speed/quality check on the preceding image. That test explicitly invoked the
startup service; ordinary resume does not automatically play a boot cue.
A shutdown cue cannot guarantee electrical poweroff or complete before an
independent hardware cutoff.
