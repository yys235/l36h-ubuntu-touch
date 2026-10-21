"""A corrupt/mismatched boot must fail before reaching fastboot."""
import importlib.util
import pathlib
import struct
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]


def dtb_fixture():
    compatible = b'sony,xperia-yuga\0qcom,apq8064\0'
    tree = struct.pack('>I', 1) + b'\0'*4
    tree += struct.pack('>III', 3, len(compatible), 0) + compatible
    tree += b'\0' * (-len(tree) % 4)
    tree += struct.pack('>II', 2, 9)
    strings = b'compatible\0'
    return struct.pack('>10I', 0xd00dfeed, 56+len(tree)+len(strings), 56,
                       56+len(tree), 40, 17, 16, 0, len(strings), len(tree)) + b'\0'*16 + tree + strings


class Boot(unittest.TestCase):
    def setUp(self):
        path = HERE/'pack-boot.py'
        self.assertTrue(path.is_file(), 'modern boot packer not implemented')
        spec = importlib.util.spec_from_file_location('bootpack', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.base = bytearray(2048)
        self.base[:8] = b'ANDROID!'
        struct.pack_into('<10I', self.base, 8, 1, 0x80208000, 1, 0x82200000,
                         0, 0x81100000, 0x80200100, 2048, 0, 0)
        self.base[64:64+len(b'androidboot.hardware=qcom')] = b'androidboot.hardware=qcom'
        self.kernel = bytearray(64)
        struct.pack_into('<I', self.kernel, 36, 0x016f2818)
        self.ramdisk = b'\x1f\x8btest-fixture'

    def pack(self, dtb=None, cmdline=None):
        args = {} if cmdline is None else {'cmdline': cmdline}
        return self.module.make_boot(bytes(self.base), bytes(self.kernel),
                                     dtb_fixture() if dtb is None else dtb, self.ramdisk, **args)

    def test_pack_then_verify_addresses_and_clean_cmdline(self):
        image, manifest = self.pack()
        self.module.verify_image(image, manifest)
        self.assertEqual(struct.unpack_from('<I', image, 12)[0], 0x80208000)
        self.assertNotIn(b'androidboot.hardware', image[:2048])
        self.assertIn(b'yuga_probe=modern-v1', image[:2048])

    def test_wrong_base_magic_rejected(self):
        self.base[:8] = b'NOTBOOT!'
        with self.assertRaisesRegex(ValueError, 'magic'):
            self.pack()

    def test_wrong_load_address_rejected(self):
        struct.pack_into('<I', self.base, 20, 0x82000000)
        with self.assertRaisesRegex(ValueError, 'address'):
            self.pack()

    def test_overlong_command_line_rejected(self):
        with self.assertRaisesRegex(ValueError, 'command line'):
            self.pack(cmdline='x'*1537)

    def test_wrong_board_dtb_rejected(self):
        wrong = dtb_fixture().replace(b'sony,xperia-yuga', b'sony,xperia-xxxx')
        with self.assertRaisesRegex(ValueError, 'Yuga'):
            self.pack(dtb=wrong)

    def test_truncated_dtb_rejected(self):
        with self.assertRaisesRegex(ValueError, 'DTB'):
            self.pack(dtb=dtb_fixture()[:-10])

    def test_post_pack_corruption_rejected(self):
        image, manifest = self.pack()
        damaged = bytearray(image)
        damaged[2050] ^= 1
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            self.module.verify_image(bytes(damaged), manifest)

    def test_truncated_image_rejected(self):
        image, manifest = self.pack()
        with self.assertRaises(ValueError):
            self.module.verify_image(image[:-1], manifest)


if __name__ == '__main__':
    unittest.main()
