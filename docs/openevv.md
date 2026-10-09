# Optional OpenEVV speech

OpenEVV is an optional formant-synthesis backend under evaluation. It is not
installed by the default systembase. An explicit build profile selects it
for systembase, including BRLTTY console speech and character feedback.
The recipe builds American English with compiled rules and
a native Speech Dispatcher module using the OE target compiler.

## Restricted inputs

The recipe requires an explicitly supplied source archive. Upstream's MIT
license does not cover the language data, synthesizer tables, XML scanner
tables, or ETI-derived language material identified in its NOTICE. The
combined package is therefore marked CLOSED; that label is not a license
or a grant of redistribution rights. LICENSE and NOTICE accompany the
installed package.

Do not place the archive, generated language sources, or resulting binaries
in the public BSP repositories. The build launcher accepts a private archive
through `--openevv-source`, verifies its pinned checksum, and records that
checksum in the build record. Without this input the recipe is skipped.
Supplying it enables the recipe, not automatic image installation. Add
`--speech-backend openevv` to select it for systembase instead of RHVoice/SLT.

The evaluated input is upstream commit
`39075043324cf6717745c52284a1909d45b35d61`, archived with Git's tar format and
the prefix `openevv/`. Its SHA-256 is
`7cdb7fa059d42882996c97c2bf2f4b51b1c1f8dc24e9bd68fa2d251859c9a134`.
Changing the input requires updating both the recipe and launcher pins.

## Build and interfaces

Using an appropriately obtained matching archive:

```sh
python3 scripts/bsp.py build openevv --local-layers --without-wifi \
    --openevv-source /private/path/openevv.tar
```

Run this from the build repository. It builds a component, not a flashable
image, and does not access the device. The package provides:

- `/usr/bin/openevv`: command-line WAV synthesis.
- `/usr/libexec/speech-dispatcher/sd_openevv`: persistent synthesis module.
- `/etc/openh432/speech/modules/openevv.conf`: module settings.

For a complete private image, use the standard build targets with both
`--openevv-source /private/path/openevv.tar` and
`--speech-backend openevv`, plus the normal stock-firmware input. Apply the
same options to fetch and build. The speech service and client socket are
unchanged; the selected image does not depend on RHVoice or SLT.

## Target qualification

Compiled-rule American English has been exercised on the H432B at 800 MHz.
A sustained protocol test generated 89.46 seconds of PCM in 9.94 seconds.
First PCM arrived in 122–225 ms; the protocol STOP event followed its request
by 96 ms. A separate command-line request test measured approximately 320 ms
to ALSA RUNNING and 263 ms from cancel-command launch to PCM idle. These are
software observations, not acoustic or keyboard-to-speech latency.

Normal-rate and Speech Dispatcher rate +60 playback were reported clean and
completed without logged underruns using the bounded ALSA buffer policy.
The short synthesis benchmark used under 9 MiB resident memory. These tests
do not establish performance under all concurrent workloads or other languages.

The selected systembase has booted from NAND with both FMSpeech and FMBraille
active, BRLTTY's Speech Dispatcher driver connected, and playback completed
without logged underruns. Automatic console speech and character feedback
are enabled by this profile. Local typing, spoken command output and braille
operation have been confirmed. Power-button deep suspend/wake restored console
speech, and an ordinary empty-port reboot after resume reached the same service
configuration. Open streams across sleep and repeated-cycle endurance remain
unqualified; keyboard-to-speech latency remains unmeasured.

The classic-voice protocol checks covered voice selection, rate/pitch/volume,
punctuation, spelling, characters, index marks, stop, pause and recovery.
The optional `Wideband 1` module test terminated with SIGSEGV on this target;
leave wideband disabled. The standalone wideband WAV command completed, but
that does not qualify wideband service playback.

The ALSA backend requests a 10 ms period and 200 ms buffer and retains an
80 ms refill margin. Stop drops queued PCM rather than waiting for that
buffer to drain. The appliance dispatcher loads its configured backend
without implicit fallback modules that would compete for the exclusive PCM.

## Release boundary

An installation image and an A/B update may use the same built systembase.
A release profile must explicitly select this package and resolve distribution
rights for its restricted inputs before publishing either form. Excluding
source data from Git does not remove it from compiled binaries or images.
