"""Exercise archive validation before a malformed initramfs can be flashed."""
import importlib.util
import pathlib
import stat
import struct
import unittest
import gzip
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'build-initramfs.py'


def arm_fixture():
    ident = b'\x7fELF\x01\x01\x01' + b'\0' * 9
    header = struct.pack('<16sHHIIIIIHHHHHH', ident, 2, 40, 1, 0x10000, 52, 0,
                         0x5000400, 52, 32, 1, 0, 0, 0)
    return header + struct.pack('<IIIIIIII', 1, 0, 0x10000, 0x10000, 84, 84, 5, 4096)


class Initramfs(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'initramfs builder not implemented')
        spec = importlib.util.spec_from_file_location('initramfs', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.entries = [('bin', b'', stat.S_IFDIR | 0o755),
                        ('bin/busybox', arm_fixture(), stat.S_IFREG | 0o755),
                        ('bin/sh', b'busybox', stat.S_IFLNK | 0o777),
                        ('init', b'#!/bin/sh\nexec /bin/sh\n', stat.S_IFREG | 0o755)]

    def test_valid_archive_is_newc_with_executable_init(self):
        archive = self.module.build_archive(self.entries)
        self.assertEqual(archive[:6], b'070701')
        self.assertIn(b'init\0', archive)
        self.assertIn(b'TRAILER!!!\0', archive)

    def test_duplicate_init_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.module.build_archive(self.entries + [self.entries[-1]])

    def test_parent_path_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unsafe archive path'):
            self.module.build_archive(self.entries + [('../escape', b'x', stat.S_IFREG | 0o644)])

    def test_symlink_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, 'symlink escapes'):
            self.module.build_archive(self.entries + [('bin/out', b'../../outside', stat.S_IFLNK | 0o777)])

    def test_non_executable_init_rejected(self):
        self.entries[-1] = ('init', self.entries[-1][1], stat.S_IFREG | 0o644)
        with self.assertRaisesRegex(ValueError, 'executable init'):
            self.module.build_archive(self.entries)

    def test_missing_shell_interpreter_rejected(self):
        with self.assertRaisesRegex(ValueError, 'interpreter'):
            self.module.build_archive([e for e in self.entries if e[0] != 'bin/sh'])

    def test_wrong_architecture_busybox_rejected(self):
        blob = bytearray(arm_fixture())
        blob[18:20] = struct.pack('<H', 62)
        self.entries[1] = ('bin/busybox', bytes(blob), stat.S_IFREG | 0o755)
        with self.assertRaisesRegex(ValueError, 'ARM ELF32'):
            self.module.build_archive(self.entries)

    def test_dynamic_busybox_rejected(self):
        blob = bytearray(arm_fixture())
        blob[52:56] = struct.pack('<I', 3)
        self.entries[1] = ('bin/busybox', bytes(blob), stat.S_IFREG | 0o755)
        with self.assertRaisesRegex(ValueError, 'static'):
            self.module.build_archive(self.entries)

    def test_cli_packages_executable_pid1_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            busybox = root/'busybox'
            busybox.write_bytes(arm_fixture())
            output = root/'initramfs.cpio.gz'
            result = subprocess.run([sys.executable, str(SCRIPT), '--busybox', str(busybox), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            entries = {name: (data, fields) for name, data, fields in self.module.newc.read_entries(gzip.decompress(output.read_bytes()))}
            self.assertIn('sbin/probe-handoff.sh', entries)
            self.assertTrue(entries['sbin/probe-handoff.sh'][1][1] & 0o111)


if __name__ == '__main__':
    unittest.main()
