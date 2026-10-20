import json,pathlib,subprocess,tempfile,unittest

SCRIPT=pathlib.Path(__file__).with_name('assemble-yuga-userdata.py')

class Assembly(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=pathlib.Path(self.temp.name)
        self.overlay=self.base/'overlay'; self.firstboot=self.base/'firstboot'; self.out=self.base/'out'
        (self.overlay/'yuga-port').mkdir(parents=True)
        (self.overlay/'yuga-port/bluetooth-init.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.firstboot/'yuga-firstboot/input').mkdir(parents=True)
        key=self.base/'key'
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
        (self.firstboot/'yuga-firstboot/input/authorized_key').write_bytes(key.with_suffix('.pub').read_bytes())
        (self.firstboot/'yuga-firstboot/input/config.json').write_text('{"schema_version":1,"server_mode":false}\n')
    def run_assembly(self):
        return subprocess.run(['python3',str(SCRIPT),'--overlay-data',str(self.overlay),'--firstboot-data',str(self.firstboot),'--output',str(self.out)],capture_output=True,text=True)
    def test_assembles_bluetooth_and_private_firstboot_inputs(self):
        r=self.run_assembly(); self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual((self.out/'yuga-port/bluetooth-init.sh').read_bytes(),(self.overlay/'yuga-port/bluetooth-init.sh').read_bytes())
        key=self.out/'yuga-firstboot/input/authorized_key'
        self.assertEqual(key.read_bytes(),(self.firstboot/'yuga-firstboot/input/authorized_key').read_bytes())
        self.assertEqual(key.stat().st_mode & 0o777,0o400)
        self.assertEqual((self.out/'yuga-port/bluetooth-init.sh').stat().st_mode & 0o777,0o755)
    def test_missing_bluetooth_payload_is_rejected_before_output(self):
        (self.overlay/'yuga-port/bluetooth-init.sh').unlink()
        r=self.run_assembly(); self.assertNotEqual(r.returncode,0); self.assertIn('bluetooth',r.stderr.lower()); self.assertFalse(self.out.exists())
    def test_unexpected_private_or_runtime_data_is_rejected(self):
        (self.firstboot/'status.json').write_text('{"old-device":true}')
        r=self.run_assembly(); self.assertNotEqual(r.returncode,0); self.assertIn('unexpected',r.stderr.lower()); self.assertFalse(self.out.exists())
    def test_symlink_payload_cannot_copy_external_files(self):
        key=self.firstboot/'yuga-firstboot/input/authorized_key'; key.unlink(); key.symlink_to(self.base/'key')
        r=self.run_assembly(); self.assertNotEqual(r.returncode,0); self.assertIn('symlink',r.stderr.lower()); self.assertFalse(self.out.exists())
    def test_existing_output_is_preserved(self):
        self.out.mkdir(); (self.out/'sentinel').write_text('keep')
        r=self.run_assembly(); self.assertNotEqual(r.returncode,0); self.assertIn('output',r.stderr.lower()); self.assertEqual((self.out/'sentinel').read_text(),'keep')
    def test_invalid_schema_does_not_produce_partial_payload(self):
        (self.firstboot/'yuga-firstboot/input/config.json').write_text('{"schema_version":true,"server_mode":"yes"}')
        r=self.run_assembly(); self.assertNotEqual(r.returncode,0); self.assertIn('schema',r.stderr.lower()); self.assertFalse(self.out.exists())

if __name__=='__main__': unittest.main()
