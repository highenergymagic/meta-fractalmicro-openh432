# Offline speech

The systembase speech service uses Speech Dispatcher with a build-selected
backend. The default development backend is RHVoice with English SLT;
[optional OpenEVV](openevv.md) requires explicit restricted inputs. Synthesis
runs locally, without a network service or runtime voice downloads. The OpenEVV profile enables BRLTTY console speech
and character feedback through Speech Dispatcher. The default RHVoice profile
retains braille-only console access.

## Service and client interface

`FMSpeech.service` runs Speech Dispatcher as the local `user` account.
Clients in that account use the Unix socket at
`/run/fm-speech/speechd.sock`. The login profile exports
`SPEECHD_ADDRESS=unix_socket:/run/fm-speech/speechd.sock`.
There is no TCP listener.

Applications should use the Speech Dispatcher client API for speech requests,
priorities and cancellation. The `spd-say` command is included for diagnostics.
For example, from the local account:

```sh
spd-say -w -l en "The speech service is ready."
spd-say -C
```

The first command uses the selected backend and waits for completion; the second cancels queued/current
speech and can be issued by another client.

Service configuration is in `/etc/openh432/speech/speechd.conf`; synthesis
configuration is in `/etc/RHVoice/RHVoice.conf`. The service uses a private
ALSA configuration at `/etc/openh432/speech/asound.conf`; it does not replace
the system-wide ALSA defaults.

## Audio and packaging

The voice package contains SLT's 16 kHz model. ALSA converts its mono output
to the board's 44.1 kHz, stereo S16_LE playback format. PortAudio uses ALSA;
PulseAudio and JACK are not part of this speech stack.

The service configures playback below the codec driver's enforced speaker
volume ceiling. It stops before the shutdown-sound service plays. The
current PCM path is exclusive: simultaneous speech, radio and other media
playback requires additional audio arbitration.

Engine and service recipes belong to this OS layer. English language data
and SLT belong to the
[asset layer](https://github.com/highenergymagic/meta-fractalmicro-assets).
Their source revisions are pinned independently. RHVoice is an HTS
statistical-parametric synthesizer, not a neural inference engine.

## Qualification

RHVoice requests and cancellation work through the local user account, but
live SLT playback breaks up and synthesis can be slower than real time on
this board. It is not qualified for continuous screen reading. First-audio latency and coexistence with suspend
and other playback remain unqualified.

Backend-specific target results and limitations for OpenEVV are recorded in
its [qualification section](openevv.md#target-qualification).
