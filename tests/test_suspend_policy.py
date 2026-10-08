# SPDX-License-Identifier: MIT
import configparser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "recipes-core/openh432-suspend/files"

class SuspendPolicy(unittest.TestCase):
    def config(self, name):
        parser = configparser.ConfigParser()
        parser.read(FILES / name)
        return parser

    def test_only_power_key_requests_sleep(self):
        login = self.config("95-h432b-suspend.conf")["Login"]
        self.assertEqual(login["HandlePowerKey"], "suspend")
        self.assertEqual(login["HandlePowerKeyLongPress"], "suspend")
        for key in ("HandleSuspendKey", "HandleSuspendKeyLongPress",
                    "HandleHibernateKey", "HandleHibernateKeyLongPress",
                    "HandleLidSwitch", "HandleLidSwitchExternalPower",
                    "HandleLidSwitchDocked", "IdleAction"):
            self.assertEqual(login[key], "ignore")

    def test_standard_systembase_includes_policy(self):
        image = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("openh432-suspend", image)
        recipe = (FILES.parent / "openh432-suspend_1.0.bb").read_text()
        self.assertIn("logind.conf.d", recipe)
        self.assertIn("sleep.conf.d", recipe)

    def test_deep_sleep_not_hibernation(self):
        sleep = self.config("50-h432b-sleep.conf")["Sleep"]
        self.assertEqual(sleep["SuspendState"], "mem")
        self.assertEqual(sleep["MemorySleepMode"], "deep")
        self.assertEqual(sleep["AllowSuspend"], "yes")
        for key in ("AllowHibernation", "AllowHybridSleep", "AllowSuspendThenHibernate"):
            self.assertEqual(sleep[key], "no")

if __name__ == "__main__":
    unittest.main()
