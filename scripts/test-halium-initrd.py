import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).with_name('patch-halium-initrd.py')
spec = importlib.util.spec_from_file_location('patcher', path)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)

class PatchTests(unittest.TestCase):
    def test_usb_order_and_other_script_unchanged(self):
        source = b'prefix\n    write $ANDROID_USB/functions       $USB_FUNCTIONS\n    write $ANDROID_USB/enable          1\nsuffix\n'
        result = patcher.patch_telnet(source)
        self.assertLess(result.index(b'f_rndis/wceis'), result.index(b'$ANDROID_USB/functions'))
        self.assertIn(b'[ -e $ANDROID_USB/f_rndis/wceis ]', result)
        self.assertEqual(result.replace(patcher.INSERT, b''), source)

    def test_unexpected_upstream_rejected(self):
        with self.assertRaises(ValueError):
            patcher.patch_telnet(b'changed upstream')

    def test_archive_preserves_other_entries(self):
        entries = [('init', b'original', 0o100755), ('scripts/panic/telnet', patcher.ANCHOR, 0o100755), ('TRAILER!!!', b'', 0)]
        original = b''.join(patcher.encode_entry(name, content, [i, mode, 0, 0, 1, 0, len(content), 0, 0, 0, 0, len(name.encode())+1, 0]) for i, (name, content, mode) in enumerate(entries))
        modified = patcher.patch_archive(original, b'helper')
        parsed = list(patcher.read_entries(modified))
        self.assertEqual(parsed[0][1], b'original')
        helpers = [entry for entry in parsed if entry[0] == 'sbin/reboot-bootloader']
        self.assertEqual(len(helpers), 1)
        self.assertEqual(helpers[0][1], b'helper')
        self.assertEqual(helpers[0][2][1], 0o100755)

if __name__ == '__main__':
    unittest.main()
