# SPDX-License-Identifier: MIT
"""Recovery remains independent of the root image and bounds hostless failures."""
from pathlib import Path
import subprocess
import tempfile
import unittest

FILES = Path(__file__).resolve().parents[1] / "recipes-core/openh432-root-handoff/files"


class Recovery(unittest.TestCase):
    def run_recovery(self, connected):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "run").mkdir()
            (root / "udc/controller").mkdir(parents=True)
            (root / "udc/controller/state").write_text(connected)
            script = (FILES / "initramfs-recovery").read_text()
            script = script.replace("/run/", str(root / "run") + "/")
            script = script.replace("/sys/class/udc/", str(root / "udc") + "/")
            script = script.replace("/dev/ttyGS0", "/dev/null")
            script = script.replace("set -eu", """set -eu
sleep() { echo WAIT; }
dmesg() { echo kernel-evidence; }
setsid() { printf '%s\\n' "$*" > """ + str(root / "shell") + "; }")
            result = subprocess.run(["sh", "-c", script, "recovery", "mapping failed"],
                                    capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "run/openh432-handoff-error").read_text(),
                             "mapping failed\n")
            self.assertIn("kernel-evidence", (root / "run/openh432-handoff-dmesg.log").read_text())
            return result.stdout, (root / "shell").exists()

    def test_no_host_returns_to_fallback_after_bounded_wait(self):
        output, shell = self.run_recovery("not attached")
        self.assertEqual(output.count("WAIT"), 10)
        self.assertFalse(shell)

    def test_configured_host_gets_independent_shell(self):
        output, shell = self.run_recovery("configured")
        self.assertTrue(shell)
        self.assertNotIn("WAIT", output)

    def test_handoff_retains_errors_and_restores_init_stdio(self):
        init = (FILES / "init").read_text()
        self.assertIn('openh432-initramfs-recovery "$*"', init)
        self.assertIn('exec >/run/openh432-handoff.log 2>&1', init)
        self.assertIn('exec 1>&3 2>&4 3>&- 4>&-', init)
        for name in ("init", "initramfs-recovery"):
            subprocess.run(["sh", "-n", str(FILES / name)], check=True)
