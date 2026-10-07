# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "recipes-connectivity/openh432-bluetooth"
class Bluetooth(unittest.TestCase):
    def test_factory_transport(self):
        text = (RECIPE / "files/FMBluetoothTransport.service").read_text()
        self.assertIn("Requires=dev-ttySAC0.device", text)
        self.assertIn("ExecStartPre=/bin/sleep 5", text)
        self.assertIn("/dev/ttySAC0 bcsp 1382400 noflow", text)
        self.assertIn("Restart=no", text)
        self.assertNotIn("ttySAC1", text)
    def test_manual_first_qualification(self):
        self.assertIn('SYSTEMD_AUTO_ENABLE = "disable"',
                      (RECIPE / "openh432-bluetooth_1.0.bb").read_text())
        self.assertIn("openh432-bluetooth", (ROOT /
                      "recipes-core/images/openh432-systembase-b.bb").read_text())
        self.assertIn("deprecated", (ROOT /
                      "recipes-connectivity/bluez5/bluez5_%.bbappend").read_text())
