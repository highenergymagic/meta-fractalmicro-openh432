# SPDX-License-Identifier: MIT
"""Execute the scan-IE gate from the supplicant patch with native C."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "recipes-connectivity/wpa-supplicant"


class PassiveScan(unittest.TestCase):
    def test_patch_is_integrated(self):
        append = (RECIPE / "wpa-supplicant_%.bbappend").read_text()
        self.assertIn("0001-nl80211-no-probe-ies-for-passive-scan.patch", append)

    def test_actual_gate_preserves_active_ies_and_omits_passive_ies(self):
        patch = (RECIPE / "files/0001-nl80211-no-probe-ies-for-passive-scan.patch").read_text()
        condition = re.search(r"^\+\tif \(([^\n]+)\) \{", patch, re.M).group(1)
        source = '''
        #include <assert.h>
        struct scan { const void *extra_ies; unsigned int num_ssids; };
        static int emit(const struct scan *params) { return !!(CONDITION); }
        int main(void) {
            const char ies[13] = {0x7f, 11};
            struct scan p = {ies, 0};
            assert(!emit(&p));
            p.num_ssids = 1; assert(emit(&p));
            p.num_ssids = 4; assert(emit(&p));
            p.extra_ies = 0; assert(!emit(&p));
            p.num_ssids = 0; assert(!emit(&p));
            return 0;
        }
        '''.replace("CONDITION", condition)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "scan.c").write_text(source)
            subprocess.run([os.environ.get("BT_NATIVE_CC", "cc"), "-std=c99",
                            "-Wall", "-Wextra", "-Werror", str(path / "scan.c"),
                            "-o", str(path / "scan")], check=True)
            subprocess.run([str(path / "scan")], check=True)


if __name__ == "__main__":
    unittest.main()
