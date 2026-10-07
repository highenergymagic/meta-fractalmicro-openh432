# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "recipes-connectivity/openh432-wifi"
START = (DIR / "files/openh432-wifi-start").read_text()
UNIT = (DIR / "files/FMWiFi.service").read_text()
RECIPE = (DIR / "openh432-wifi_1.0.bb").read_text()


class WifiRuntime(unittest.TestCase):
    def test_firmware_optional_and_service_enabled(self):
        self.assertIn("ConditionPathExists=/lib/firmware/h432b/rtl8712s.bin", UNIT)
        self.assertIn('SYSTEMD_AUTO_ENABLE = "enable"', RECIPE)
        self.assertIn("iw wireless-regdb-static busybox", RECIPE)
        base = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("openh432-wifi", base)

    def test_ordered_one_shot_initialization(self):
        stages = ["$found/sample", "$found/power_init",
                  "$found/firmware_load", "$found/power_ack",
                  "$found/network_start", "iw reg reload", "iw reg set",
                  "ip link set wlan0 up"]
        positions = [START.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('[ "$(cat "$found/result")" = idle ]', START)
        self.assertIn('check_result firmware_result', START)
        self.assertIn('check_result power_ack_result', START)
        self.assertNotIn("iw dev wlan0 scan", START)

    def test_bounded_wait_and_no_credential_policy(self):
        self.assertIn('"$n" -lt 30', START)
        self.assertIn('"$n" -lt 10', START)
        self.assertIn("TimeoutStartSec=60", UNIT)
        self.assertNotIn("Restart=", UNIT)
        self.assertNotIn("ssid", START)
        self.assertNotIn("psk", START)

    def test_standard_supplicant_and_networkd_integration(self):
        network = (DIR / "files/20-wireless.network").read_text()
        dropin = (DIR / "files/10-openh432.conf").read_text()
        self.assertIn("wpa-supplicant wpa-supplicant-cli", RECIPE)
        self.assertIn("After=FMWiFi.service", dropin)
        self.assertIn("ConditionPathExists=/etc/wpa_supplicant/wpa_supplicant-wlan0.conf", dropin)
        self.assertIn("Name=wlan0", network)
        self.assertIn("DHCP=yes", network)
        self.assertIn("RouteMetric=2048", network)
        self.assertNotIn("ssid=", network)
        self.assertNotIn("psk=", dropin)


if __name__ == "__main__":
    unittest.main()
