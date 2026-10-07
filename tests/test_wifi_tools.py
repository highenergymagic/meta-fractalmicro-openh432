# SPDX-License-Identifier: MIT
"""Wireless tools archive contracts; not a hardware acceptance test."""
from pathlib import Path
import unittest

RECIPE = (Path(__file__).resolve().parents[1] /
          "recipes-core/images/openh432-wifi-tools.bb").read_text()


class WifiTools(unittest.TestCase):
    def test_modern_signed_regulatory_database(self):
        self.assertIn('IMAGE_INSTALL = "iw wireless-regdb-static"', RECIPE)
        self.assertNotIn("wpa-supplicant", RECIPE)

    def test_fixed_image_metadata_and_compression(self):
        for line in (
            'REPRODUCIBLE_TIMESTAMP_ROOTFS = "${SOURCE_DATE_EPOCH}"',
            'IMAGE_VERSION_SUFFIX = "-${SOURCE_DATE_EPOCH}"',
            'XZ_THREADS = "1"',
            'NO_RECOMMENDATIONS = "1"',
        ):
            self.assertIn(line, RECIPE)

    def test_not_a_bootable_image_or_firmware_distribution(self):
        self.assertIn('IMAGE_FSTYPES = "tar.xz"', RECIPE)
        self.assertNotIn("linux-firmware", RECIPE)
        self.assertNotIn("SRC_URI", RECIPE)


if __name__ == "__main__":
    unittest.main()
