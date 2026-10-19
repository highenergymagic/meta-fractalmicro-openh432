# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'recipes-connectivity/wpa-supplicant'


class ScanCapability(unittest.TestCase):
    def test_automatic_ies_follow_advertised_capability(self):
        patch = (DIR / 'files/0002-scan-honor-zero-probe-ie-capability.patch').read_text()
        self.assertIn('tb[NL80211_ATTR_MAX_SCAN_IE_LEN] &&', patch)
        self.assertIn('nla_get_u16(tb[NL80211_ATTR_MAX_SCAN_IE_LEN]) == 0', patch)
        self.assertIn('wpa_s->drv_flags2 & WPA_DRIVER_FLAGS2_NO_SCAN_IES', patch)
        self.assertIn('wpa_supplicant_extra_ies', patch)
        for token in ('rtl8712', 'wlan0', 'h432b', 'params->extra_ies = NULL'):
            self.assertNotIn(token, patch)
        self.assertIn('0002-scan-honor-zero-probe-ie-capability.patch',
                      (DIR / 'wpa-supplicant_%.bbappend').read_text())
