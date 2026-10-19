# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "recipes-core/systemd/files/defer-resolver.py"
spec = importlib.util.spec_from_file_location("defer_resolver", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

UNIT = """[Unit]
DefaultDependencies=no
After=systemd-sysctl.service systemd-sysusers.service
Before=sysinit.target network.target nss-lookup.target shutdown.target initrd-switch-root.target
Conflicts=shutdown.target initrd-switch-root.target
[Service]
Type=notify-reload
ProtectSystem=strict
NoNewPrivileges=yes
PrivateDevices=yes
[Install]
WantedBy=sysinit.target
"""


class ResolverOrdering(unittest.TestCase):
    def test_only_startup_order_changes(self):
        result = module.defer_resolver(UNIT)
        old, new = UNIT.splitlines(), result.splitlines()
        self.assertEqual(len(old), len(new))
        self.assertEqual([i for i, pair in enumerate(zip(old, new))
                          if pair[0] != pair[1]], [2, 3])
        self.assertEqual(new[2], old[2] + " FMAccessibility.target")
        self.assertEqual(new[3], old[3].replace("sysinit.target ", ""))

    def test_upstream_ordering_changes_fail_closed(self):
        for text in (UNIT.replace("After=", "#After="),
                     UNIT.replace("Before=sysinit.target ", "Before="),
                     UNIT + "After=systemd-sysctl.service systemd-sysusers.service\n",
                     module.defer_resolver(UNIT)):
            with self.subTest(text=text), self.assertRaises(ValueError):
                module.defer_resolver(text)

    def test_recipe_only_rewrites_enabled_resolver(self):
        recipe = (SCRIPT.parent.parent / "systemd_%.bbappend").read_text()
        self.assertIn("'PACKAGECONFIG', 'resolved', 'true', 'false'", recipe)
        self.assertIn("do_install:append()", recipe)
        self.assertIn("${D}${systemd_system_unitdir}/systemd-resolved.service", recipe)
