# SPDX-License-Identifier: MIT
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "recipes-core/openh432-boot-success/files"

class BootSuccess(unittest.TestCase):
    def test_ubi_rules_are_packaged_for_ram_and_nand_images(self):
        recipe = (FILES.parent / "openh432-boot-success_1.0.bb").read_text()
        self.assertIn('PACKAGES =+ "${PN}-ubi-rules"', recipe)
        rules = next(l for l in recipe.splitlines() if l.startswith("FILES:${PN}-ubi-rules"))
        for name in ("59-openh432-managed-images.rules", "59-openh432-bootstate.rules"):
            self.assertIn(name, rules)
        self.assertIn("${PN}-ubi-rules", next(l for l in recipe.splitlines()
                                              if l.startswith("RDEPENDS:${PN} =")))
        ram = (ROOT / "recipes-core/images/openh432-ram-dev.bb").read_text()
        self.assertIn("openh432-boot-success-ubi-rules", ram)
        self.assertNotIn(" openh432-boot-success ", ram + " ")

    def test_environment_volumes_skip_filesystem_probing(self):
        rule = (FILES / "59-openh432-bootstate.rules").read_text()
        self.assertIn('SUBSYSTEM=="ubi"', rule)
        self.assertIn('ATTR{name}=="bootstate_a|bootstate_b"', rule)
        self.assertIn('ENV{UDEV_DISABLE_PERSISTENT_STORAGE_RULES_FLAG}="1"', rule)
        self.assertNotIn('OPTIONS+="ignore_device"', rule)
        recipe = (FILES.parent / "openh432-boot-success_1.0.bb").read_text()
        self.assertIn("file://59-openh432-bootstate.rules", recipe)
        self.assertIn("${nonarch_base_libdir}/udev/rules.d/59-openh432-bootstate.rules", recipe)

    def test_managed_images_avoid_discovery_not_integrity_checks(self):
        rule = (FILES / "59-openh432-managed-images.rules").read_text()
        self.assertIn('SUBSYSTEM=="ubi"', rule)
        self.assertIn('ATTR{name}=="kernel_a|kernel_b|recovery|systembase_a|systembase_b"', rule)
        self.assertIn('ENV{UDEV_DISABLE_PERSISTENT_STORAGE_RULES_FLAG}="1"', rule)
        self.assertNotIn('SUBSYSTEM=="block"', rule)
        init = (ROOT / "recipes-core/openh432-root-handoff/files/init").read_text()
        self.assertIn('ubiblock --create', init)
        self.assertIn('corrupted', init)
        self.assertIn('upd_marker', init)

    def test_shell_syntax(self):
        subprocess.run(["sh", "-n", str(FILES / "mark-good")], check=True)

    def test_unmanaged_boot_never_writes(self):
        script = (FILES / "mark-good").read_text()
        prefix = "cat() { printf '%s' 'console=ttyS0'; }; export -f cat\n"
        # POSIX sh does not export functions; sourced script shares this function.
        prefix = "cat() { printf '%s' 'console=ttyS0'; };\n"
        result = subprocess.run(["sh", "-c", prefix + script], capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_health_and_serial_gate(self):
        script = (FILES / "mark-good").read_text()
        for token in ("FMBraille.service", "getty@tty1.service", "NRestarts",
                      'uid" = 1000', "/dev/tty1", "systembase_$name",
                      "upd_marker", "corrupted", "--mark-good", '"$attempt"'):
            self.assertIn(token, script)
        self.assertNotIn("fw_setenv", script)
        unit = (FILES / "FMMarkBootSuccessful.service").read_text()
        self.assertIn("ExecStartPre=/bin/sleep 30", unit)
        self.assertIn("ConditionKernelCommandLine=rauc.slot", unit)
        self.assertNotIn("network-online", unit)

    def test_managed_root_slot_parser(self):
        init = (ROOT / "recipes-core/openh432-root-handoff/files/init").read_text()
        parser = init[init.index("slot=$(cat"):init.index("mtd=\n")]
        for args, expected in [
            ("console=ttyS0", "b"),
            ("rauc.slot=A", "a"),
            ("rauc.slot=B", "b"),
            ("rauc.slot=A rauc.slot=B", None),
            ("rauc.slot=A rauc.slot=A", None),
            ("rauc.slot=C", None),
            ("rauc.slot=", None),
        ]:
            prefix = "fail() { exit 1; }; cat() { case \"$1\" in /proc/cmdline) printf '%s' \"" + args + "\" ;; *) echo b ;; esac; };\n"
            result = subprocess.run(["sh", "-c", prefix + parser + "\nprintf '%s' \"$slot\""],
                                    capture_output=True, text=True)
            if expected is None:
                self.assertNotEqual(result.returncode, 0, args)
            else:
                self.assertEqual((result.returncode, result.stdout), (0, expected), args)

if __name__ == "__main__":
    unittest.main()
