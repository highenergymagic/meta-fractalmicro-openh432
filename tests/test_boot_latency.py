# SPDX-License-Identifier: MIT
from pathlib import Path
import os
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class BootLatency(unittest.TestCase):
    def test_health_wait_is_not_a_multiuser_dependency(self):
        files = ROOT / "recipes-core/openh432-boot-success/files"
        service = (files / "FMMarkBootSuccessful.service").read_text()
        timer = (files / "FMMarkBootSuccessful.timer").read_text()
        self.assertIn("ExecStartPre=/bin/sleep 30", service)
        self.assertNotIn("WantedBy=multi-user.target", service)
        self.assertIn("Unit=FMMarkBootSuccessful.service", timer)
        self.assertIn("WantedBy=timers.target", timer)
        self.assertNotIn("After=multi-user.target", timer)

    def test_early_audio_is_bounded_and_handoff_waits(self):
        files = ROOT / "recipes-core/openh432-root-handoff/files"
        script = (files / "early-sound").read_text()
        subprocess.run(["sh", "-n", str(files / "early-sound")], check=True)
        self.assertIn("timeout -k 2 20", script)
        recipe = (files.parent / "openh432-root-handoff_1.0.bb").read_text()
        self.assertIn("coreutils", recipe)
        self.assertIn("killall aplay", script)
        self.assertIn("startup-sound.done", script)
        init = (files / "init").read_text()
        self.assertLess(init.index('wait "$early_sound"'), init.index("exec switch_root"))
        self.assertLess(init.index("openh432-early-sound"), init.index("ubiattach"))
        service = (ROOT / "recipes-core/openh432-system-sounds/files/FMBootSound.service").read_text()
        self.assertIn("ConditionPathExists=!/run/openh432-startup-sound.done", service)

    def test_gps_timer_keeps_uart_rule_without_early_activation(self):
        files = ROOT / "recipes-navigation/openh432-agps/files"
        rule = (files / "70-openh432-gps.rules").read_text()
        self.assertIn("e2900400.serial", rule)
        self.assertNotIn("SYSTEMD_WANTS", rule)
        timer = (files / "FMGPSStart.timer").read_text()
        self.assertIn("OnBootSec=90s", timer)
        self.assertIn("Unit=gpsd.service", timer)
        self.assertNotIn("After=multi-user.target", timer)

    def test_immutable_root_rejects_deferred_setup(self):
        recipe = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("check_no_deferred_postinsts", recipe)
        self.assertIn("bb.fatal", recipe)
        self.assertIn("postinsts", recipe)

    def test_early_sound_success_marker_and_failure_cleanup(self):
        original = (ROOT / "recipes-core/openh432-root-handoff/files/early-sound").read_text()
        for status in (0, 1, 124, 137):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                script = original.replace("/run/openh432-startup-sound.done", str(root / "done"))
                script = script.replace("/usr/libexec/fm-system-sound", str(root / "player"))
                (root / "script").write_text(script)
                for name, body in {
                    "timeout": 'echo "timeout $*" >> "$TEST_LOG"; case "$*" in *startup) exit "$TEST_STATUS";; *) exit 0;; esac',
                    "killall": 'echo "killall $*" >> "$TEST_LOG"',
                }.items():
                    file = root / name
                    file.write_text("#!/bin/sh\n" + body + "\n")
                    file.chmod(0o755)
                env = dict(os.environ, PATH=str(root) + ":" + os.environ["PATH"],
                           TEST_STATUS=str(status), TEST_LOG=str(root / "log"))
                result = subprocess.run(["sh", str(root / "script")], env=env,
                                        capture_output=True)
                self.assertEqual(result.returncode, status)
                self.assertEqual((root / "done").exists(), status == 0)
                log = (root / "log").read_text()
                self.assertEqual("killall aplay" in log, status != 0)
                self.assertEqual("player mute" in log, status != 0)
