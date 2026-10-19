# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'recipes-core/openh432-settings'


class SettingsContracts(unittest.TestCase):
    def test_native_transaction_vectors_are_run(self):
        recipe = (DIR / 'openh432-settings_1.0.bb').read_text()
        self.assertIn('BBCLASSEXTEND = "native"', recipe)
        self.assertIn('./settings-test', recipe)
        self.assertIn('-UNDEBUG', recipe)

    def test_service_uses_authenticated_uid_not_arguments(self):
        source = (DIR / 'files/settingsd.c').read_text()
        self.assertIn('sd_bus_query_sender_creds(m, SD_BUS_CREDS_EUID', source)
        self.assertIn('sd_bus_creds_get_euid', source)
        self.assertIn('uid == 1000', source)
        self.assertIn('SD_BUS_ERROR_ACCESS_DENIED', source)

    def test_private_shared_storage(self):
        unit = (DIR / 'files/FMSettings.service').read_text()
        self.assertIn('StateDirectory=fractalmicro/settings', unit)
        self.assertIn('StateDirectoryMode=0700', unit)
        self.assertIn('UMask=0077', unit)
        self.assertIn('ProtectSystem=strict', unit)
        store = (DIR / 'files/settings-store.c').read_text()
        self.assertIn('SQLITE_OPEN_NOFOLLOW', store)
        self.assertIn('PRAGMA synchronous=FULL', store)
        self.assertIn('BEGIN IMMEDIATE', store)
        self.assertIn('ROLLBACK', store)


if __name__ == '__main__':
    unittest.main()
