"""Only the expected Yuga USB mode can be changed by a diagnostic build."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'adjust-source.py'


class SourceAdjustment(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'Source adjustment is not implemented')
        spec = importlib.util.spec_from_file_location('adjust_source', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_usb_diagnostic_uses_fixed_peripheral_role(self):
        original = '&usb1 {\n\tdr_mode = "otg";\n\tstatus = "okay";\n};\n'
        self.assertEqual(self.module.peripheral_role(original),
                         '&usb1 {\n\tdr_mode = "peripheral";\n\tstatus = "okay";\n};\n')

    def test_unknown_board_layout_rejected(self):
        with self.assertRaisesRegex(ValueError, 'expected exactly one'):
            self.module.peripheral_role('&usb2 { dr_mode = "otg"; };')

    def test_duplicate_usb_node_rejected(self):
        node = '&usb1 {\n\tdr_mode = "otg";\n\tstatus = "okay";\n};\n'
        with self.assertRaisesRegex(ValueError, 'expected exactly one'):
            self.module.peripheral_role(node + node)


if __name__ == '__main__':
    unittest.main()
