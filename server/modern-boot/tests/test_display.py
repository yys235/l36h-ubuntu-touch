import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
BOARD = '/ { compatible = "sony,xperia-yuga", "qcom,apq8064"; };\n' + '\t\tpm8921_l29: l29 {\n\t\t\tregulator-min-microvolt = <2000000>;\n\t\t\tregulator-max-microvolt = <2000000>;\n\t\t\tbias-pull-down;\n\t\t};\n'


class Display(unittest.TestCase):
    def setUp(self):
        path = HERE / 'install-display.py'
        self.assertTrue(path.exists(), 'modern Yuga display source integration is missing')
        spec = importlib.util.spec_from_file_location('display', path)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_only_display_supply_and_graph_added(self):
        result = self.mod.enable_board(BOARD)
        self.assertTrue(result.startswith(BOARD.replace('<2000000>', '<1800000>')))
        self.assertIn('compatible = "sharp,ls050t3sx01"', result)
        self.assertIn('reset-gpios = <&pm8921_gpio 25 GPIO_ACTIVE_LOW>', result)
        self.assertIn('dcdc-en-gpios = <&pm8921_gpio 24 GPIO_ACTIVE_HIGH>', result)
        self.assertIn('gpios = <&pm8921_gpio 26 GPIO_ACTIVE_HIGH>', result)
        self.assertIn('vddio-supply = <&pm8921_l29>', result)
        self.assertIn('vdda-supply = <&pm8921_l2>', result)
        self.assertNotIn('avdd-supply', result)
        self.assertNotIn('pm8921_lvs7', result)

    def test_unknown_board_voltage_or_existing_wiring_refused(self):
        for source in [BOARD.replace('xperia-yuga', 'xperia-odin'),
                       BOARD.replace('<2000000>', '<2800000>'),
                       BOARD + '&dsi0 {};', BOARD + '&gsbi1 {};',
                       BOARD + 'panel@0 {};', BOARD + '&mdp {};']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.mod.enable_board(source)

    def test_unknown_source_rejected_without_partial_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            board = root / self.mod.BOARD_PATH
            board.parent.mkdir(parents=True)
            board.write_text(BOARD)
            with self.assertRaises(ValueError):
                self.mod.install(root)
            self.assertEqual(board.read_text(), BOARD)
            self.assertFalse((root / 'drivers/gpu/drm/panel/panel-sharp-ls050t3sx01.c').exists())

    @unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
    def test_lm3533_board_register_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / 'lm3533-contract'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(HERE / 'tests/test_lm3533_board.c'), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)])
            self.assertEqual(result.returncode, 0, 'LM3533 Sony board register contract failed')


if __name__ == '__main__':
    unittest.main()
