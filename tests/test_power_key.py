# SPDX-License-Identifier: MIT
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "recipes-core/openh432-power-key/files"

class PowerKeyTests(unittest.TestCase):
    def test_daemon_startup_failures_and_stop_races(self):
        cc = os.environ.get("POWER_NATIVE_CC") or shutil.which("cc")
        if not cc:
            self.skipTest("native C compiler unavailable")
        with tempfile.TemporaryDirectory() as directory:
            target = str(Path(directory) / "daemon-test")
            wraps = ("open", "close", "fcntl", "clock_gettime", "ioctl", "write", "read", "poll")
            subprocess.run([cc, "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-Wno-unused-parameter", "-I", str(ROOT / "tests/power-key-stubs"),
                            str(ROOT / "tests/test-power-key-daemon.c"), "-o", target,
                            *("-Wl,--wrap=" + name for name in wraps)], check=True)
            for scenario in range(5):
                with self.subTest(scenario=scenario):
                    subprocess.run([target, str(scenario)], check=True, timeout=5)

    def test_native_gesture_state_machine(self):
        cc = os.environ.get("POWER_NATIVE_CC") or shutil.which("cc")
        if not cc:
            self.skipTest("native C compiler unavailable")
        with tempfile.TemporaryDirectory() as directory:
            target = str(Path(directory) / "gesture")
            subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(FILES), str(ROOT / "tests/test-power-gesture.c"),
                            "-o", target], check=True)
            subprocess.run([target], check=True)

    def test_logind_owns_power_transition(self):
        source = (FILES / "openh432-power-key.c").read_text()
        for text in ('"handle-power-key"', '"Inhibit"', '"PrepareForSleep"',
                     '"PowerOff"', '"Suspend"', "F_DUPFD_CLOEXEC", "EVIOCSCLOCKID",
                     "SYN_DROPPED", "SND_BELL"):
            self.assertIn(text, source)
        self.assertNotIn("/sys/power/state", source)
        self.assertNotIn("/dev/mem", source)
        self.assertIn("ev.input_event_sec", source)
        self.assertNotIn("ev.time.", source)  # ARM32 with 64-bit libc time.

    def test_service_and_device_identity(self):
        unit = (FILES / "FMPowerKey.service").read_text()
        self.assertIn("Requires=systemd-logind.service", unit)
        self.assertIn("BindsTo=", unit)
        self.assertIn("Restart=on-failure", unit)
        rules = (FILES / "75-h432b-power-key.rules").read_text()
        self.assertIn('ATTRS{name}=="H432B power switch"', rules)
        self.assertIn('ATTRS{name}=="pwm-beeper"', rules)

    def test_standard_image_includes_countdown(self):
        image = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("openh432-power-key", image)

if __name__ == "__main__":
    unittest.main()
