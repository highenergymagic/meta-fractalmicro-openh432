# SPDX-License-Identifier: MIT
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "recipes-connectivity/openh432-wifi"
SCRIPT = DIR / "files/openh432-wifi-regulatory"
START = SCRIPT.read_text()
UNIT = (DIR / "files/FMRegulatory.service").read_text()
RECIPE = (DIR / "openh432-wifi_1.0.bb").read_text()


class WifiRuntime(unittest.TestCase):
    def test_policy_is_not_hardware_initialization(self):
        self.assertIn('SYSTEMD_SERVICE:${PN} = "FMRegulatory.service"', RECIPE)
        self.assertIn('SYSTEMD_AUTO_ENABLE = "enable"', RECIPE)
        self.assertIn("iw wireless-regdb-static busybox", RECIPE)
        base = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("openh432-wifi", base)
        for old in ("/sys/", "initialize", "modprobe", "ip link", "scan", "firmware"):
            self.assertNotIn(old, START)
        self.assertNotIn("FMWiFi", RECIPE)

    def test_regulatory_precedes_supplicant_and_waits_for_netdev(self):
        dropin = (DIR / "files/10-openh432.conf").read_text()
        self.assertIn("Requires=FMRegulatory.service", dropin)
        self.assertIn("After=FMRegulatory.service sys-subsystem-net-devices-wlan0.device", dropin)
        self.assertIn("BindsTo=sys-subsystem-net-devices-wlan0.device", dropin)
        self.assertIn("ConditionPathExists=/etc/wpa_supplicant/wpa_supplicant-wlan0.conf", dropin)
        self.assertIn("Before=wpa_supplicant@wlan0.service", UNIT)
        self.assertIn("TimeoutStartSec=15", UNIT)
        self.assertNotIn("Restart=", UNIT)
        self.assertNotIn("psk", START + dropin)

    def test_standard_networkd_policy(self):
        network = (DIR / "files/20-wireless.network").read_text()
        self.assertIn("wpa-supplicant wpa-supplicant-cli", RECIPE)
        self.assertIn("Type=wlan", network)
        self.assertNotIn("Name=wlan0", network)
        self.assertIn("DHCP=yes", network)
        self.assertIn("RouteMetric=2048", network)
        self.assertNotIn("ssid=", network)

    def run_policy(self, country, reply="NZ", fail_set=False):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            iw = directory / "iw"
            iw.write_text("#!/bin/sh\n"
                          "printf '%s\\n' \"$*\" >> \"$CALLS\"\n"
                          "if [ \"$2\" = set ]; then exit \"$FAIL_SET\"; fi\n"
                          "printf 'country %s: DFS-UNSET\\n' \"$REPLY\"\n")
            iw.chmod(0o755)
            delay = directory / "sleep"
            delay.write_text("#!/bin/sh\nexit 0\n")
            delay.chmod(0o755)
            calls = directory / "calls"
            environment = dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}",
                               WIFI_COUNTRY=country, REPLY=reply,
                               FAIL_SET=str(int(fail_set)), CALLS=str(calls))
            process = subprocess.run(["sh", str(SCRIPT)], env=environment,
                                     capture_output=True, text=True, timeout=5)
            return process, calls.read_text().splitlines() if calls.exists() else []

    def test_country_success(self):
        result, calls = self.run_policy("NZ")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["reg set NZ", "reg get"])

    def test_invalid_country_never_calls_iw(self):
        for country in ("nz", "NZZ", "N Z", "N;", "01"):
            with self.subTest(country=country):
                result, calls = self.run_policy(country)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_set_failure_stops(self):
        result, calls = self.run_policy("NZ", fail_set=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ["reg set NZ"])

    def test_confirmation_is_bounded(self):
        result, calls = self.run_policy("NZ", reply="00")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls.count("reg get"), 10)
        self.assertIn("regulatory setup failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
