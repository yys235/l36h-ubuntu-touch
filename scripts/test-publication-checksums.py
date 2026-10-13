import hashlib, pathlib, subprocess, tempfile, unittest
script = pathlib.Path(__file__).with_name('verify-publication.py')
class Checksums(unittest.TestCase):
    def test_match_then_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            data = root / 'payload'
            data.write_bytes(b'known input')
            sums = root / 'SHA256SUMS'
            sums.write_text(hashlib.sha256(data.read_bytes()).hexdigest()+'  payload\n')
            command = ['python3',str(script),'--root',str(root),'--checksums',str(sums)]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            data.write_bytes(b'changed')
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,1)
    def test_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            sums = root/'SHA256SUMS'
            sums.write_text('0'*64+'  ../outside\n')
            self.assertNotEqual(subprocess.run(['python3',str(script),'--root',str(root),'--checksums',str(sums)],capture_output=True).returncode,0)
if __name__=='__main__': unittest.main()
