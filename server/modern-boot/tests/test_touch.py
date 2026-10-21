import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / 'enable-touch.py'
BOARD = '/ { compatible = "sony,xperia-yuga", "qcom,apq8064"; };\n' + '\t\tpm8921_l17: l17 {\n\t\t\tregulator-min-microvolt = <2000000>;\n\t\t\tregulator-max-microvolt = <2000000>;\n\t\t\tbias-pull-down;\n\t\t};\n'

class Touch(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('enable_touch', PATH)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_board_definition_preserved(self):
        result = self.mod.enable(BOARD)
        self.assertTrue(result.startswith(BOARD.replace('<2000000>', '<3000000>')))
        self.assertIn('touchscreen@2c', result)

    def test_other_board_refused(self):
        with self.assertRaises(ValueError):
            self.mod.enable(BOARD.replace('xperia-yuga', 'xperia-odin'))

    def test_existing_touch_or_supply_refused(self):
        for extra in ['touchscreen@2c {};', '&gsbi3 { status = "okay"; };']:
            with self.assertRaises(ValueError):
                self.mod.enable(BOARD + extra)

    def test_unknown_supply_voltage_refused(self):
        with self.assertRaises(ValueError):
            self.mod.enable(BOARD.replace('<2000000>', '<2800000>'))

    def test_bus_only_keeps_touch_supply_and_sensor_unmodified(self):
        result = self.mod.enable_bus(BOARD)
        self.assertTrue(result.startswith(BOARD))
        self.assertNotIn('touchscreen@2c', result)
        self.assertIn('&gsbi3_i2c', result)

    def test_bus_only_refuses_duplicate_bus_override(self):
        with self.assertRaises(ValueError):
            self.mod.enable_bus(BOARD + '&gsbi3 { status = "okay"; };')
