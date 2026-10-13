import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('receive-ut-image.sh')

class ReceiverTests(unittest.TestCase):
    def run_receiver(self, directory, data, expected=None, name='rootfs.img', digest=None):
        expected = data if expected is None else expected
        digest = hashlib.sha256(expected).hexdigest() if digest is None else digest
        return subprocess.run(['sh', str(SCRIPT), str(directory), name, str(len(expected)), digest], input=data, capture_output=True)

    def test_complete_binary_file_commits(self):
        with tempfile.TemporaryDirectory() as d:
            payload = bytes(range(256)) * 4097
            result = self.run_receiver(d, payload)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((Path(d)/'rootfs.img').read_bytes(), payload)
            self.assertIn(b'COMMITTED rootfs.img', result.stdout)

    def test_truncated_stream_preserves_existing_image(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'rootfs.img'; target.write_bytes(b'old image')
            result=self.run_receiver(d,b'ab',expected=b'abcdef')
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(target.read_bytes(),b'old image')

    def test_fragmented_stream_preserves_every_byte(self):
        with tempfile.TemporaryDirectory() as d:
            payload=bytes(range(256))*2049+b'last byte'
            digest=hashlib.sha256(payload).hexdigest()
            process=subprocess.Popen(['sh',str(SCRIPT),d,'system.img',str(len(payload)),digest],
                                     stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertIn(b'READY system.img',process.stdout.readline())
            for offset in range(0,len(payload),257):
                process.stdin.write(payload[offset:offset+257]); process.stdin.flush()
            process.stdin.close(); process.stdin=None
            stdout,stderr=process.communicate(timeout=30)
            self.assertEqual(process.returncode,0,stderr)
            self.assertIn(b'COMMITTED system.img',stdout)
            self.assertEqual((Path(d)/'system.img').read_bytes(),payload)

    def test_symlink_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            sentinel=Path(d)/'sentinel'; sentinel.write_bytes(b'preserve')
            (Path(d)/'rootfs.img').symlink_to(sentinel)
            result=self.run_receiver(d,b'abc')
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(sentinel.read_bytes(),b'preserve')

    def test_wrong_hash_preserves_existing_image(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'rootfs.img'; target.write_bytes(b'old image')
            result=self.run_receiver(d,b'abcdef',digest='0'*64)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(target.read_bytes(),b'old image')

    def test_oversized_stream_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            result=self.run_receiver(d,b'abcdefEXTRA',expected=b'abcdef')
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((Path(d)/'rootfs.img').exists())

    def test_retry_overwrites_partial_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_receiver(d,b'ab',expected=b'abcdef')
            result=self.run_receiver(d,b'abcdef')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((Path(d)/'rootfs.img').read_bytes(),b'abcdef')

    def test_repeat_verified_image_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_receiver(d,b'abcdef')
            result=self.run_receiver(d,b'',expected=b'abcdef')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(b'ALREADY_COMMITTED',result.stdout)

    def test_invalid_filename_cannot_write_outside_directory(self):
        with tempfile.TemporaryDirectory() as d:
            result=self.run_receiver(d,b'abc',name='../escape.img')
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(list(Path(d).iterdir()),[])

if __name__=='__main__': unittest.main()
