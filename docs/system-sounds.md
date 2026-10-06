# System sound services

The optional openh432-system-sounds recipe provides FMBootSound.service and
FMShutdownSound.service. It is not included in the development image and both
units are disabled by default. This is bring-up policy, not a production audio
session manager.

Before enabling, qualify speaker/headphone routing and provide
/usr/share/openh432/sounds/startup.wav and shutdown.wav as 44.1 kHz stereo
S16_LE PCM. Create /etc/openh432/system-sounds.enabled only after those checks.
The player uses card OpenH432, analog volume 45 (below the kernel ceiling 50),
and mutes outputs after playback. Playback is bounded by systemd timeouts.

The shutdown unit is armed at boot and runs its stop action before filesystem
and sound targets stop. The helper plays only when systemd reports stopping,
not on an ordinary service stop/restart. A marker enables timeout cleanup
without muting unrelated audio when the service never started playback.
Shutdown sound is best-effort; it cannot precede an independent hardware cutoff.
These lifecycle paths still need live qualification.

## Requested assets

The selected KDE files exactly match kdebase 3.5.10's official archive:
https://download.kde.org/Attic/3.5.10/src/kdebase-3.5.10.tar.bz2

Archive SHA256:
77aa9d8f28c532f2e7a5157a7f4ba8df1001f00fa1cb72cb70b388b3d0e16b61

Members under kdebase-3.5.10/kcontrol/knotify/sounds/:

- KDE_Startup_1.ogg: d9bc793b2d1ced1728862cdd01274f943291dabf4eb4215725251d15a3133c73
- KDE_Logout_1.ogg: e0bd2e7efe63345e82412032b8aebc8d41be6d0756400f53884ddd8250832d9d

The archive includes GPLv2 COPYING, but no sound-specific author/license
notice has been established. Assets are not currently packaged or published.
The MIT license of our integration code does not relicense those recordings.

## Build validation

Pinned Yocto build and package QA passed. This source has not yet been
deployed for live event/sound qualification. Offline layer tests also pass.
