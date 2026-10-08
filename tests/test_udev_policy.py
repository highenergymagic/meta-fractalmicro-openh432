# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "recipes-core/openh432-udev-policy"


class UdevPolicy(unittest.TestCase):
    def test_device_coldplug_preserves_all_device_subsystems(self):
        conf = (POLICY / "files/50-openh432-coldplug.conf").read_text()
        commands = [line for line in conf.splitlines() if line.startswith("ExecStart=")]
        self.assertEqual(commands[0], "ExecStart=")
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[1], "ExecStart=-udevadm trigger --action=add /sys/class/tty/ttyGS0")
        self.assertIn("--type=devices", commands[2])
        self.assertIn("--action=add", commands[1])
        self.assertNotIn("--subsystem-match", conf)
        self.assertNotIn("--subsystem-nomatch", conf)
        self.assertNotIn("--initialized", conf)
        self.assertNotIn("--settle", conf)

    def test_bounded_workers_do_not_change_event_timeouts(self):
        conf = (POLICY / "files/50-openh432-workers.conf").read_text()
        settings = [line for line in conf.splitlines() if line and not line.startswith("#")]
        self.assertEqual(settings, ["children_max=4"])

    def test_standard_image_and_machine_scoped_package(self):
        recipe = (POLICY / "openh432-udev-policy_1.0.bb").read_text()
        image = (ROOT / "recipes-core/images/openh432-systembase-b.bb").read_text()
        self.assertIn("openh432-udev-policy", image)
        self.assertIn('COMPATIBLE_MACHINE = "^h432b$"', recipe)
        self.assertIn('RDEPENDS:${PN} = "udev"', recipe)
        self.assertIn("/systemd-udev-trigger.service.d", recipe)
        self.assertIn("/udev/udev.conf.d", recipe)
        self.assertIn("ln -s /dev/null", recipe)
        self.assertIn("/75-probe_mtd.rules", recipe)
        self.assertNotIn("60-persistent-storage.rules", recipe)
