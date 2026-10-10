# SPDX-License-Identifier: MIT
"""Offline policy checks; fixture playback never accesses sound hardware."""
from pathlib import Path
import os
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "recipes-core/openh432-system-sounds/files"


class PowerSoundPolicy(unittest.TestCase):
    def test_power_actions_disabled(self):
        policy = (ROOT / "recipes-core/openh432-ram-policy/files/90-power-input-qualification.conf").read_text()
        self.assertIn("HandlePowerKey=ignore", policy)
        self.assertIn("HandlePowerKeyLongPress=ignore", policy)

    def test_opt_in_and_timeout(self):
        recipe = (FILES.parent / "openh432-system-sounds_1.0.bb").read_text()
        self.assertIn('SYSTEMD_AUTO_ENABLE:${PN} = "disable"', recipe)
        image = (ROOT / "recipes-core/images/openh432-ram-dev.bb").read_text()
        self.assertNotIn("openh432-system-sounds", image)
        self.assertIn("TimeoutStartSec=12s", (FILES / "FMBootSound.service").read_text())
        shutdown = (FILES / "FMShutdownSound.service").read_text()
        self.assertIn("TimeoutStopSec=12s", shutdown)
        self.assertIn("After=local-fs.target sound.target", shutdown)
        self.assertIn("RemainAfterExit=yes", shutdown)

    def run_player(self, mode, *, enabled=True, state="running", fail=False,
                   card="present"):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sounds").mkdir()
            for name in ("startup", "shutdown"):
                (root / "sounds" / (name + ".wav")).touch()
            if enabled:
                (root / "enabled").touch()
            script = (FILES / "fm-system-sound.sh").read_text()
            script = script.replace("/run/fm-system-sound-active", str(root / "active"))
            script = script.replace("/etc/openh432/system-sounds.enabled", str(root / "enabled"))
            script = script.replace("/usr/share/openh432/sounds", str(root / "sounds"))
            script = script.replace("/proc/asound/OpenH432", str(root / "card"))
            if card == "present":
                (root / "card").mkdir()
            (root / "player").write_text(script)
            for cmd, body in {
                "systemctl": 'echo "$STATE"; exit 1',
                "amixer": '[ -e "$CARD" ] || { echo "Invalid card number" >&2; exit 1; }\n'
                          'echo "mixer $*" >> "$LOG"',
                "aplay": 'echo "play $*" >> "$LOG"; exit "$FAIL"',
            }.items():
                path = root / cmd
                path.write_text("#!/bin/sh\n" + body + "\n")
                path.chmod(0o755)
            env = dict(os.environ, PATH=str(root) + ":" + os.environ["PATH"],
                       STATE=state, LOG=str(root / "log"), FAIL="1" if fail else "0",
                       CARD=str(root / "card"))
            if card == "late":
                # Register the card while the player is waiting for it.
                proc = subprocess.Popen(["sh", str(root / "player"), mode], env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                time.sleep(1)
                (root / "card").mkdir()
                out, err = proc.communicate(timeout=10)
                result = subprocess.CompletedProcess(proc.args, proc.returncode, out, err)
            else:
                result = subprocess.run(["sh", str(root / "player"), mode], env=env,
                                        capture_output=True, text=True)
            log = (root / "log").read_text() if (root / "log").exists() else ""
            self.assertFalse((root / "active").exists())
            return result.returncode, log

    def test_manual_stop_and_missing_optin_are_silent(self):
        for mode, enabled in (("shutdown", True), ("startup", False), ("mute", True)):
            rc, log = self.run_player(mode, enabled=enabled)
            self.assertEqual((rc, log), (0, ""))

    def test_start_and_shutdown_cleanup(self):
        for mode in ("startup", "shutdown"):
            rc, log = self.run_player(mode, state="stopping")
            self.assertEqual(rc, 0)
            self.assertEqual(log.count("play -q"), 1)
            self.assertIn("Speaker Playback Volume 45,45", log)
            self.assertTrue(log.rstrip().endswith("Speaker Switch off,off"))

    def test_waits_for_late_card_registration(self):
        rc, log = self.run_player("startup", card="late")
        self.assertEqual(rc, 0)
        self.assertEqual(log.count("play -q"), 1)

    def test_missing_card_wait_is_bounded(self):
        start = time.monotonic()
        rc, log = self.run_player("startup", card="absent")
        self.assertLess(time.monotonic() - start, 8)
        self.assertNotEqual(rc, 0)
        self.assertEqual(log.count("play -q"), 0)

    def test_playback_failure_still_mutes(self):
        rc, log = self.run_player("startup", fail=True)
        self.assertEqual(rc, 1)
        self.assertTrue(log.rstrip().endswith("Speaker Switch off,off"))


if __name__ == "__main__":
    unittest.main()
