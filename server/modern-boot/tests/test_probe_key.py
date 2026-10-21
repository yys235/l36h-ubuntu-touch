import base64
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1]/'prepare-probe-key.py'


class ProbeKey(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def run_key(self, content):
        source, output = self.root/'input.pub', self.root/'authorized_key'
        if content is not None:
            source.write_bytes(content)
        result = subprocess.run([sys.executable, str(SCRIPT), '--public-key', str(source),
                                 '--output', str(output)], capture_output=True, text=True)
        return result, output

    def test_valid_ed25519_public_key_is_preserved(self):
        blob = struct.pack('>I', 11)+b'ssh-ed25519'+struct.pack('>I', 32)+bytes(range(32))
        key = b'ssh-ed25519 '+base64.b64encode(blob)+b' installer\n'
        result, output = self.run_key(key)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), key)

    def test_missing_key_refused(self):
        result, output = self.run_key(None)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(output.exists())

    def test_private_key_refused_without_echoing_it(self):
        secret = b'-----BEGIN OPENSSH PRIVATE KEY-----\nPRIVATE_PAYLOAD\n'
        result, output = self.run_key(secret)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(output.exists())
        self.assertNotIn('PRIVATE_PAYLOAD', result.stderr+result.stdout)

    def test_two_keys_are_refused(self):
        result, output = self.run_key(b'ssh-ed25519 AAAA one\nssh-ed25519 AAAA two\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
