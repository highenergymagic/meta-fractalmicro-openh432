# SPDX-License-Identifier: MIT
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "recipes-core/openh432-udev-policy"


class UdevPolicy(unittest.TestCase):
    def test_udev_can_load_modalias_drivers(self):
        distro = (ROOT / "conf/distro/openh432.conf").read_text()
        options = next(line.split('"')[1].split() for line in distro.splitlines()
                       if line.startswith("PACKAGECONFIG:pn-systemd ="))
        self.assertIn("kmod", options)

    def test_early_coldplug_only_replays_local_accessibility(self):
        conf = (POLICY / "files/50-openh432-coldplug.conf").read_text()
        commands = [line for line in conf.splitlines() if line.startswith("ExecStart=")]
        self.assertEqual(commands[0], "ExecStart=")
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[1], "ExecStart=-udevadm trigger --action=add /sys/class/tty/ttyGS0")
        self.assertIn("--type=devices", commands[2])
        self.assertIn("--action=add", commands[1])
        for subsystem in ("input", "sound", "misc"):
            self.assertIn("--subsystem-match=" + subsystem, conf)
        self.assertNotIn("--subsystem-nomatch", conf)
        self.assertNotIn("--initialized", conf)
        self.assertNotIn("--settle", conf)

    def test_late_coldplug_preserves_all_device_subsystems(self):
        conf = (POLICY / "files/FMPeripheralColdplug.service").read_text()
        self.assertIn("After=FMAccessibility.target", conf)
        self.assertIn("--type=devices --action=add", conf)
        for exclusion in ("--subsystem-match", "--subsystem-nomatch", "--initialized", "--settle"):
            self.assertNotIn(exclusion, conf)
        self.assertIn("WantedBy=multi-user.target", conf)

    def test_readiness_is_not_process_creation_or_an_unbounded_wait(self):
        target = (POLICY / "files/FMAccessibility.target").read_text()
        self.assertIn("Wants=getty@tty1.service FMBraille.service", target)
        self.assertIn("After=getty@tty1.service FMBraille.service", target)
        self.assertNotIn("\nRequires=", target)
        braille = (ROOT / "recipes-accessibility/openh432-braille/files/FMBraille.service").read_text()
        self.assertIn("Type=notify", braille)
        self.assertIn("TimeoutStartSec=30s", braille)
        getty = (ROOT / "recipes-core/openh432-local-console/files/autologin.conf").read_text()
        self.assertIn("Type=simple", getty)

    def test_networking_waits_without_changing_shutdown_order(self):
        conf = (POLICY / "files/50-accessibility-first.conf").read_text()
        self.assertIn("After=FMAccessibility.target", conf)
        recipe = (POLICY / "openh432-udev-policy_1.0.bb").read_text()
        for unit in ("systemd-networkd.service", "FMRegulatory.service", "wpa_supplicant@wlan0.service"):
            self.assertIn(unit, recipe)
        self.assertNotIn("DefaultDependencies=no", conf)

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
