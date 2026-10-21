import importlib.util
import pathlib
import struct
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / 'verify-modules.py'

class Modules(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('module_verifier', PATH)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def elf(self):
        blob = bytearray(160)
        blob[:7] = b'\x7fELF\x01\x01\x01'
        struct.pack_into('<HHI', blob, 16, 1, 40, 1)
        struct.pack_into('<I', blob, 32, 80)
        struct.pack_into('<HHHHHH', blob, 40, 52, 0, 0, 40, 2, 1)
        struct.pack_into('<IIIIIIIIII', blob, 120, 0, 3, 0, 0, 52, 16, 0, 0, 1, 0)
        return bytes(blob)

    def test_valid_arm_relocatable(self):
        self.mod.validate_elf(self.elf())

    def test_truncated_section_table_refused(self):
        with self.assertRaisesRegex(ValueError, 'section table'):
            self.mod.validate_elf(self.elf()[:100])

    def test_wrong_architecture_refused(self):
        blob = bytearray(self.elf())
        struct.pack_into('<H', blob, 18, 62)
        with self.assertRaisesRegex(ValueError, 'ARM'):
            self.mod.validate_elf(bytes(blob))

    def test_section_content_beyond_file_refused(self):
        blob = bytearray(self.elf())
        struct.pack_into('<I', blob, 140, 999)
        with self.assertRaisesRegex(ValueError, 'section content'):
            self.mod.validate_elf(bytes(blob))
