# SPDX-License-Identifier: MIT
"""Offline speech image, ownership and audio contracts."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "recipes-accessibility/openh432-speech"
FILES = POLICY / "files"


class SpeechPolicy(unittest.TestCase):
    def test_standard_systembase_includes_speech(self):
        image = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("openh432-speech", image)
        recipe = (POLICY / "openh432-speech_1.0.bb").read_text()
        for package in ("rhvoice", "rhvoice-slt", "speech-dispatcher"):
            self.assertIn(package, recipe)
        self.assertIn('SYSTEMD_AUTO_ENABLE:${PN} = "enable"', recipe)

    def test_local_unprivileged_service(self):
        unit = (FILES / "FMSpeech.service").read_text()
        for value in ("User=user", "Group=user", "SupplementaryGroups=audio",
                      "RuntimeDirectoryMode=0700", "UMask=0077",
                      "NoNewPrivileges=yes", "-c unix_socket",
                      "-S /run/fm-speech/speechd.sock",
                      "After=sound.target FMShutdownSound.service"):
            self.assertIn(value, unit)
        self.assertNotIn("inet_socket", unit)
        self.assertIn("ALSA_CONFIG_PATH=/etc/openh432/speech/asound.conf", unit)

    def test_voice_and_engine_pins(self):
        recipe = (ROOT / "recipes-accessibility/rhvoice/rhvoice_1.18.3.bb").read_text()
        self.assertRegex(recipe, r'SRCREV = "[0-9a-f]{40}"')
        self.assertNotIn("AUTOREV", recipe)
        for disabled in ("-DWITH_DATA=OFF", "-DBUILD_UTILS=OFF",
                         "-DWITH_PULSE=OFF", "-DWITH_LIBAO=OFF"):
            self.assertIn(disabled, recipe)
        dispatcher = (ROOT / "recipes-accessibility/speech-dispatcher/speech-dispatcher_0.12.1.bb").read_text()
        self.assertIn("--without-espeak --without-espeak-ng", dispatcher)
        self.assertIn("--disable-python", dispatcher)

    def test_alsa_conversion_and_volume(self):
        alsa = (FILES / "asound.conf").read_text()
        for setting in ('type plug', 'card OpenH432', 'device 0',
                        'rate 44100', 'channels 2', 'format S16_LE'):
            self.assertIn(setting, alsa)
        script = (FILES / "speech-audio").read_text()
        self.assertIn("unset ALSA_CONFIG_PATH", script)
        for control in ("Headphone", "Speaker"):
            self.assertIn(f"mix '{control} Playback Volume' 45,45", script)
        subprocess.run(["sh", "-n", str(FILES / "speech-audio")], check=True)

    def test_profile_selected_console_speech(self):
        config = (ROOT / "recipes-accessibility/openh432-braille/files/brltty.conf").read_text()
        self.assertNotRegex(config, r"(?m)^speech-driver")
        policy = ROOT / "recipes-accessibility/openh432-braille"
        recipe = (policy / "openh432-braille_1.0.bb").read_text()
        self.assertIn('if [ "${OPENH432_SPEECH_BACKEND}" = openevv ]', recipe)
        speech = (policy / "files/brltty-speech.conf").read_text()
        for value in ("speech-driver sd", "Autospawn=no", "Module=openevv",
                      "unix_socket:/run/fm-speech/speechd.sock"):
            self.assertIn(value, speech)
        self.assertIn("autospeak yes", (policy / "files/brltty.prefs").read_text())
        unit = (policy / "files/speech.conf").read_text()
        self.assertIn("After=FMSpeech.service", unit)
        self.assertNotIn("Requires=", unit)
        self.assertIn('AddModule "rhvoice" "sd_rhvoice"', (FILES / "speechd.conf").read_text())
