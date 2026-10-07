# SPDX-License-Identifier: MIT
from pathlib import Path
import json
import unittest
ROOT=Path(__file__).resolve().parents[1]
FILES=ROOT/"recipes-navigation/openh432-agps/files"
class GpsServiceTests(unittest.TestCase):
    def test_optional_ordering(self):
        s=(FILES/"gpsd.service").read_text()
        self.assertIn("Wants=agps-data-upload.service",s)
        self.assertIn("After=agps-data-upload.service",s)
        self.assertNotIn("Requires=agps",s)
        self.assertNotIn("network-online.target",s)
        self.assertIn("TimeoutStartSec=80",(FILES/"agps-data-upload.service").read_text())
    def test_local_readonly(self):
        s=(FILES/"openh432-agps.py").read_text()
        self.assertIn('["/usr/sbin/gpsd","-N","-b","-s","9600"',s)
        self.assertNotIn('"-G"',s)
        self.assertIn("LOCK_EX|fcntl.LOCK_NB",s)
        self.assertIn("serial.lock",s)
    def test_proxy_only(self):
        s=(FILES/"openh432-agps.py").read_text()
        self.assertNotIn("mediatek.com",s)
        self.assertIn("ProxyHandler({})",s)
        self.assertIn("NoRedirect()",s)
        self.assertIn("response.read(limit+1)",s)
    def test_no_generic_activation(self):
        s=(ROOT/"recipes-navigation/gpsd/gpsd_%.bbappend").read_text()
        self.assertIn("ln -s /dev/null",s)
        self.assertIn('SYSTEMD_AUTO_ENABLE = "disable"',s)
        self.assertIn("e2900400.serial",(FILES/"70-openh432-gps.rules").read_text())
    def test_base_install(self):
        s=(ROOT/"recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("gpsd gps-utils openh432-agps",s)
if __name__=="__main__":
    unittest.main()
