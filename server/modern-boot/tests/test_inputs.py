"""Corrupt/missing inputs must never reach a boot build."""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'verify-inputs.py'


class Inputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.payload = self.root / 'kernel.tar.gz'
        self.payload.write_bytes(b'fixed kernel source input')
        self.record = {'name': self.payload.name, 'bytes': self.payload.stat().st_size,
                       'sha256': hashlib.sha256(self.payload.read_bytes()).hexdigest()}

    def check(self, records=None):
        manifest = self.root / 'inputs.json'
        manifest.write_text(json.dumps({'schema': 1, 'files': [self.record] if records is None else records}))
        return subprocess.run([sys.executable, str(SCRIPT), '--manifest', str(manifest),
                               '--directory', str(self.root)], capture_output=True, text=True)

    def test_fixed_content_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Verified 1 input', result.stdout)

    def test_same_length_tamper_rejected(self):
        self.payload.write_bytes(b'X' * self.record['bytes'])
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('SHA256 mismatch', result.stderr)

    def test_wrong_length_rejected(self):
        self.payload.write_bytes(b'short')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('size mismatch', result.stderr)

    def test_missing_input_rejected(self):
        self.payload.unlink()
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('missing input', result.stderr)

    def test_parent_escape_rejected(self):
        self.record['name'] = '../kernel.tar.gz'
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('unsafe input name', result.stderr)

    def test_duplicate_name_rejected(self):
        result = self.check([self.record, self.record])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('duplicate input', result.stderr)

    def test_empty_manifest_rejected(self):
        result = self.check([])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('non-empty', result.stderr)


if __name__ == '__main__':
    unittest.main()
