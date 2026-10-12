# SPDX-License-Identifier: MIT
from pathlib import Path
import configparser
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WatchdogPolicy(unittest.TestCase):
    def test_runtime_only_systemd_policy(self):
        base = ROOT / 'recipes-core/openh432-watchdog'
        conf = configparser.ConfigParser()
        conf.read(base / 'files/60-openh432-watchdog.conf')
        self.assertEqual(conf['Manager']['RuntimeWatchdogSec'], '30s')
        self.assertEqual(conf['Manager']['RebootWatchdogSec'], '0')
        self.assertEqual(conf['Manager']['KExecWatchdogSec'], '0')
        recipe = (base / 'openh432-watchdog_1.0.bb').read_text()
        self.assertIn('${libdir}/systemd/system.conf.d', recipe)
        image = (ROOT / 'recipes-core/images/openh432-systembase-b.bb').read_text()
        self.assertIn(' openh432-watchdog', image)


if __name__ == '__main__':
    unittest.main()
