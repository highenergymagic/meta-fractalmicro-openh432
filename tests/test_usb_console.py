# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "recipes-core/openh432-ram-policy/files/serial-getty@ttyGS0.service"


class USBConsolePolicy(unittest.TestCase):
    def setUp(self):
        self.settings = {}
        for line in UNIT.read_text().splitlines():
            if line and not line.startswith(("#", "[")):
                key, value = line.split("=", 1)
                self.settings.setdefault(key, []).append(value)

    def test_disconnected_gadget_cannot_reset_shared_console(self):
        self.assertEqual(self.settings["TTYReset"], ["no"])
        self.assertEqual(self.settings["TTYVHangup"], ["no"])

    def test_gadget_does_not_own_local_console(self):
        self.assertEqual(self.settings["TTYPath"], ["/dev/ttyGS0"])
        for option in ("StandardInput", "StandardOutput", "StandardError"):
            self.assertEqual(self.settings[option], ["tty"])
        self.assertEqual(self.settings["Type"], ["simple"])

    def test_usb_service_has_no_local_login_dependency(self):
        for key in ("Requires", "Wants", "After", "Before", "BindsTo"):
            for value in self.settings.get(key, []):
                self.assertNotIn("getty@tty1", value)
                self.assertNotIn("FMBraille", value)


if __name__ == "__main__":
    unittest.main()
