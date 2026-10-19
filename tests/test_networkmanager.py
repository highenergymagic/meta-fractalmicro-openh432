# SPDX-License-Identifier: MIT
from pathlib import Path
import configparser
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'recipes-connectivity/openh432-networkmanager'


class NetworkManagerPolicy(unittest.TestCase):
    def test_shared_profiles_and_no_probe(self):
        cfg = configparser.ConfigParser()
        cfg.read(DIR / 'files/20-openh432.conf')
        self.assertEqual(cfg['keyfile']['path'], '/var/lib/NetworkManager/system-connections')
        self.assertEqual(cfg['main']['dns'], 'systemd-resolved')
        self.assertEqual(cfg['main']['auth-polkit'], 'true')
        self.assertFalse(cfg['connectivity'].getboolean('enabled'))
        self.assertEqual(cfg['connectivity']['uri'], '')

    def test_radio_defaults(self):
        cfg = configparser.ConfigParser()
        cfg.read(DIR / 'files/20-openh432.conf')
        self.assertEqual(cfg['device-h432b-radio']['match-device'], 'driver:rtl8712s')
        self.assertEqual(cfg['device-h432b-radio']['wifi.scan-rand-mac-address'], 'no')
        self.assertEqual(cfg['connection-h432b-radio']['wifi.cloned-mac-address'], 'permanent')
        self.assertEqual(cfg['connection-h432b-radio']['wifi.powersave'], '2')

    def test_single_owner_without_online_boot_gate(self):
        recipe = (DIR / 'openh432-networkmanager_1.0.bb').read_text()
        for name in ('systemd-networkd.service', 'systemd-networkd.socket',
                     'wpa_supplicant@wlan0.service', 'NetworkManager-wait-online.service'):
            self.assertIn(name, recipe)
        unit = (DIR / 'files/50-openh432.service.conf').read_text()
        self.assertIn('After=FMAccessibility.target FMRegulatory.service', unit)
        self.assertNotIn('network-online', unit)
        base = (ROOT / 'recipes-core/images/openh432-systembase-b.bb').read_text()
        self.assertIn('openh432-networkmanager', base)
        self.assertIn('OPENH432_NETWORK_PACKAGE = "networkmanager-daemon"', base)
        self.assertNotIn('openh432-wired-policy', base)

    def test_appliance_account_authorization(self):
        rule = (DIR / 'files/50-openh432-network.rules').read_text()
        self.assertIn('subject.user !== "user"', rule)
        self.assertNotIn('subject.active', rule)
        self.assertIn('allowed.indexOf(action.id)', rule)
        self.assertNotIn('action.id.indexOf', rule)

    def test_minimal_build(self):
        recipe = (ROOT / 'recipes-connectivity/networkmanager/networkmanager_%.bbappend').read_text()
        self.assertIn('PACKAGECONFIG = "systemd wifi nmcli readline polkit gnutls"', recipe)


if __name__ == '__main__':
    unittest.main()
