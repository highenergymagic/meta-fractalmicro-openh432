# SPDX-License-Identifier: MIT
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'recipes-connectivity/wpa-supplicant'


class AkmCapability(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('WIFI_RX_NATIVE_CC'), 'requires pinned compiler')
    def test_alternatives_intersect_station_capabilities(self):
        patch = (DIR / 'files/0003-filter-alternative-akms-by-driver-capability.patch').read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        declarations, body = added.split('\tif (wpa_drv_get_capa', 1)
        body = '\tif (wpa_drv_get_capa' + body
        source = '''
#include <assert.h>
enum { WPA_IF_STATION };
enum { WPA_KEY_MGMT_PSK = 1, WPA_KEY_MGMT_PSK_SHA256 = 2,
       WPA_KEY_MGMT_SAE = 4, WPA_KEY_MGMT_SAE_EXT_KEY = 8 };
enum { WPA_DRIVER_CAPA_KEY_MGMT_WPA2_PSK = 16,
       WPA_DRIVER_CAPA_KEY_MGMT_PSK_SHA256 = 32,
       WPA_DRIVER_CAPA_KEY_MGMT_SAE = 64,
       WPA_DRIVER_CAPA_KEY_MGMT_SAE_EXT_KEY = 128 };
struct wpa_supplicant { unsigned int allowed_key_mgmts; };
struct wpa_driver_capa { unsigned int key_mgmt_iftype[1]; };
static unsigned int capability;
static int result;
static int wpa_drv_get_capa(struct wpa_supplicant *s, struct wpa_driver_capa *c)
{ (void)s; c->key_mgmt_iftype[0] = capability; return result; }
static void filter(struct wpa_supplicant *wpa_s) {
''' + declarations + body + '''
}
int main(void) {
    for (unsigned int profile = 0; profile < 16; profile++) {
        for (unsigned int cap = 0; cap < 16; cap++) {
            struct wpa_supplicant s = { profile };
            capability = cap << 4;
            result = 0;
            filter(&s);
            assert(s.allowed_key_mgmts == (profile & cap));
            s.allowed_key_mgmts = profile;
            result = -1;
            filter(&s);
            assert(s.allowed_key_mgmts == profile);
        }
    }
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / 'test.c'
            exe = Path(directory) / 'test'
            src.write_text(source)
            subprocess.run([os.environ['WIFI_RX_NATIVE_CC'], '-Wall', '-Wextra',
                            '-Werror', str(src), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)

    def test_selected_suite_is_not_replaced(self):
        patch = (DIR / 'files/0003-filter-alternative-akms-by-driver-capability.patch').read_text()
        self.assertNotIn('wpa_s->key_mgmt =', patch)
        self.assertIn('capa.key_mgmt_iftype[WPA_IF_STATION]', patch)
        self.assertIn('0003-filter-alternative-akms-by-driver-capability.patch',
                      (DIR / 'wpa-supplicant_%.bbappend').read_text())
