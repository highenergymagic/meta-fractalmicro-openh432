# SPDX-License-Identifier: MIT
"""Capabilities must be supplied, not hidden behind boot-log suppression."""
import configparser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootCapabilities(unittest.TestCase):
    def test_signed_regulatory_database_is_available_before_switch_root(self):
        recipe = (ROOT / "recipes-core/images/openh432-early-b.bb").read_text()
        self.assertIn("wireless-regdb-static", recipe)

    def test_network_identity_is_not_dependent_on_enumeration_or_dhcp(self):
        for path in ("recipes-core/openh432-device-policy/files/20-wired.network",
                     "recipes-connectivity/openh432-wifi/files/20-wireless.network"):
            config = configparser.ConfigParser()
            config.read(ROOT / path)
            self.assertNotIn("Name", config["Match"])
            self.assertEqual(config["DHCPv4"]["UseHostname"], "no")
            self.assertEqual(config["DHCPv6"]["UseHostname"], "no")
        self.assertEqual(config["Match"]["Type"], "wlan")
        self.assertEqual(config["DHCPv4"]["RouteMetric"], "2048")

    def test_optional_brltty_probes_keep_real_errors(self):
        recipe = (ROOT / "recipes-accessibility/brltty/brltty_%.bbappend").read_text()
        self.assertIn("0002-linux-optional-probes.patch", recipe)
        patch = (ROOT / "recipes-accessibility/brltty/files/0002-linux-optional-probes.patch").read_text()
        self.assertIn("errno == ENOENT", patch)
        self.assertIn("errno == ENOTTY", patch)
        self.assertIn('logSystemError("ioctl[VT_GETCONSIZECSRPOS]")', patch)
        self.assertIn('return 0;', patch)


if __name__ == "__main__":
    unittest.main()
