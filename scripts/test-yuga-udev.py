import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location('rules', pathlib.Path(__file__).with_name('generate-yuga-udev.py'))
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)

class RuleTests(unittest.TestCase):
    def test_preserves_ids_mode_and_full_device_path(self):
        result = rules.device_rule('/dev/input/event7 0660 system camera', {'system': 1000, 'camera': 1006})
        self.assertIn('ENV{DEVNAME}=="/dev/input/event7"', result)
        self.assertIn('OWNER="1000", GROUP="1006", MODE="0660"', result)

    def test_glob_preserved(self):
        self.assertIn('/dev/msm_camera/*', rules.device_rule('/dev/msm_camera/* 0660 system camera', {'system':1000,'camera':1006}))

    def test_unknown_identity_rejected(self):
        with self.assertRaises(ValueError):
            rules.device_rule('/dev/diag 0660 system missing', {'system':1000})

    def test_non_device_and_unsafe_line_rejected(self):
        for line in ['/sys/foo 0660 system system', '/dev/x 9999 system system', '/dev/x" 0660 system system']:
            with self.assertRaises(ValueError):
                rules.device_rule(line, {'system':1000})

    def test_sysfs_existing_attribute_adjustment(self):
        result = rules.sysfs_rule('/sys/devices/virtual/input/input* interval 0640 system system', {'system':1000})
        self.assertEqual(result, 'z /sys/devices/virtual/input/input*/interval 0640 1000 1000 - -')

    def test_sysfs_attribute_escape_rejected(self):
        with self.assertRaises(ValueError):
            rules.sysfs_rule('/sys/devices/foo ../escape 0660 system system', {'system':1000})

if __name__ == '__main__':
    unittest.main()
