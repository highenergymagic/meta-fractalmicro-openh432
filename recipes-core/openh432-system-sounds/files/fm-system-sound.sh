#!/bin/sh
# SPDX-License-Identifier: MIT
# Optional direct-ALSA bring-up policy, not a shared desktop audio mixer.
set -eu
marker=/run/fm-system-sound-active
mix() { amixer -q -c OpenH432 cset "name=$1" "$2"; }
mute() {
    mix 'Internal Speaker Switch' off || true
    mix 'Headphone Switch' off,off || true
    mix 'Speaker Switch' off,off || true
}
case "${1-}" in
    mute)
        [ -d "$marker" ] || exit 0
        mute
        rmdir "$marker"
        exit 0 ;;
    startup) name=startup ;;
    shutdown)
        state=$(systemctl is-system-running 2>/dev/null || true)
        [ "$state" = stopping ] || exit 0
        name=shutdown ;;
    *) echo 'Expected startup, shutdown or mute' >&2; exit 2 ;;
esac
[ -f /etc/openh432/system-sounds.enabled ] || exit 0
asset=/usr/share/openh432/sounds/$name.wav
[ -r "$asset" ] || exit 0
# The early cue can start before the card registers. Wait at most five seconds.
card=/proc/asound/OpenH432
n=0
while [ ! -e "$card" ] && [ "$n" -lt 50 ]; do
    sleep 0.1
    n=$((n + 1))
done
# Only opt in after verifying routing, PCM format, sample rate and safe level.
mkdir "$marker" 2>/dev/null || exit 0
cleanup() { mute; rmdir "$marker" 2>/dev/null || true; }
trap cleanup EXIT
trap 'exit 130' INT TERM
mute
mix 'Playback Volume' 255,255
mix 'Headphone Playback Volume' 45,45
mix 'Speaker Playback Volume' 45,45
mix 'Headphone Switch' on,on
mix 'Speaker Switch' on,on
mix 'Internal Speaker Switch' on
aplay -q -D hw:OpenH432,0 "$asset"
