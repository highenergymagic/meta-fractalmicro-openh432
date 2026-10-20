# SPDX-License-Identifier: MIT
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / 'recipes-accessibility/openh432-braille-progress/files'
SPEC = importlib.util.spec_from_file_location(
    'progress_recovery', ROOT / 'recipes-core/openh432-recovery/files/recovery-ui.py')
UI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UI)


class ProgressTests(unittest.TestCase):
    def test_native_frames_match_recovery(self):
        cc = os.environ.get('POWER_NATIVE_CC') or shutil.which('cc')
        self.assertTrue(cc, 'native compiler required')
        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / 'progress')
            subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(FILES / 'braille-progress.c'), '-o', binary], check=True)
            for value in range(100):
                result = subprocess.check_output([binary, '--frame', 'loading root', str(value)])
                self.assertEqual(result, UI.progress_frame('loading root', value))
            for label, value in [('x' * 29, '1'), ('UPPER', '1'), ('bad!', '1'),
                                 ('ok', '-1'), ('ok', '100'), ('ok', '1x')]:
                self.assertNotEqual(subprocess.run(
                    [binary, '--frame', label, value], capture_output=True).returncode, 0)

    def test_numeric_positions(self):
        result = UI.progress_frame('test', 42)
        self.assertEqual(result[29:], bytes((0x3c, 0x19, 0x03)))
        self.assertEqual(UI.progress_frame('test', 0)[30:], bytes((26, 26)))
        self.assertEqual(UI.progress_frame('test', 99)[30:], bytes((10, 10)))

    def test_boot_handoff_and_integration(self):
        recipe = (FILES.parent / 'openh432-braille-progress_1.0.bb').read_text()
        self.assertIn('ExecStartPre=-${libexecdir}/openh432/braille-progress finish', recipe)
        # Speech runs as user; only its short progress hook needs root.
        self.assertIn('ExecStartPost=-+${libexecdir}/openh432/braille-progress mark "speech ready" 7',
                      recipe)
        source = (FILES / 'braille-progress.c').read_text()
        self.assertIn('if (state.closed)', source)
        self.assertIn('state.closed = 1', source)
        self.assertIn('LOCK_EX | LOCK_NB', source)
        init = (ROOT / 'recipes-core/openh432-root-handoff/files/init').read_text()
        for step in range(6):
            self.assertRegex(init, r'braille-progress mark "[^"]+" ' + str(step))
        image = (ROOT / 'recipes-core/images/openh432-systembase-b.bb').read_text()
        self.assertIn('openh432-braille-progress-policy', image)


if __name__ == '__main__':
    unittest.main()
