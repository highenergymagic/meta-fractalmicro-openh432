# SPDX-License-Identifier: MIT
"""Restricted speech source and appliance playback invariants."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OpenEVVPolicy(unittest.TestCase):
    def test_optional_closed_input(self):
        recipe = (ROOT / "recipes-accessibility/openevv/openevv_0.0+git.bb").read_text()
        self.assertIn('LICENSE = "CLOSED"', recipe)
        self.assertIn("bb.parse.SkipRecipe", recipe)
        self.assertIn("RULES=c", recipe)
        self.assertIn("'SPEECHD_LIBS=-lspeechd_module'", recipe)
        self.assertNotIn("git://", recipe)
        image = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertNotIn(" openevv", image)

    def test_stream_overlap_is_in_frames(self):
        patch = (ROOT / "recipes-accessibility/speech-dispatcher/files/0003-alsa-overlap-units.patch").read_text()
        self.assertIn("+\t\tmin2 = ((min + period_size - 1) / period_size) * period_size;", patch)
        for rate in (8000, 11025, 16000, 22050, 44100, 48000):
            minimum = 20 * rate // 1000
            for period in (16, 32, 64, 128, 256, 1024):
                overlap = max(2 * period, ((minimum + period - 1) // period) * period)
                self.assertGreaterEqual(overlap, minimum)
                self.assertEqual(overlap % period, 0)

    def test_audio_fixes_are_applied(self):
        recipe = (ROOT / "recipes-accessibility/speech-dispatcher/speech-dispatcher_0.12.1.bb").read_text()
        self.assertIn("0003-alsa-overlap-units.patch", recipe)
        self.assertIn("0004-explicit-appliance-modules.patch", recipe)
