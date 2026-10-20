import importlib.util,json,os,pathlib,subprocess,tempfile,unittest
from unittest import mock

MODULE=pathlib.Path(__file__).parent.parent/'firstboot/yuga_firstboot.py'
GOOD='port 22\npermitrootlogin without-password\npasswordauthentication no\nchallengeresponseauthentication no\npubkeyauthentication yes\nauthenticationmethods publickey\nallowusers root\n'

class Runtime(unittest.TestCase):
    def setUp(self):
        if not MODULE.exists(): self.fail('Firstboot runtime is not implemented')
        spec=importlib.util.spec_from_file_location('firstboot',MODULE)
        self.m=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=pathlib.Path(self.temp.name)
        self.data=self.base/'data'; self.root=self.base/'root'; self.ssh=self.base/'ssh'
        for p in [self.data,self.root,self.ssh]: p.mkdir(mode=0o700)
        self.state=self.data/'yuga-firstboot'; self.state.mkdir(mode=0o700)
        inputs=self.state/'input'; inputs.mkdir(mode=0o700)
        key=self.base/'installer'
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
        self.pub=inputs/'authorized_key'; self.pub.write_bytes(key.with_suffix('.pub').read_bytes()); self.pub.chmod(0o400)
        self.config=inputs/'config.json'; self.config.write_text('{"schema_version":1,"server_mode":false}\n'); self.config.chmod(0o400)
        device=self.base.stat().st_dev; self.dev=str(os.major(device))+':'+str(os.minor(device))
        self.mounts=''.join(str(i)+' 1 '+self.dev+' / '+str(p)+' rw,relatime - ext4 /dev/test rw\n' for i,p in enumerate([self.data,self.root,self.ssh],10))
    def initialize(self,**overrides):
        args=dict(userdata=self.data,root_directory=self.root,ssh_directory=self.ssh,mountinfo=self.mounts,sshd_configuration=GOOD)
        args.update(overrides); return self.m.initialize(**args)
    def test_creates_independent_identity_and_reboot_preserves_keys(self):
        first=self.initialize(); host=self.ssh/'ssh_host_ed25519_key'
        old=host.read_bytes(); self.assertTrue(first['initialized'])
        auth=self.root/'.ssh/authorized_keys'
        self.assertEqual(auth.read_bytes(),self.pub.read_bytes())
        self.assertEqual(auth.stat().st_mode & 0o777,0o600)
        self.assertEqual(auth.parent.stat().st_mode & 0o777,0o700)
        self.assertEqual((self.state/'status.json').stat().st_mode & 0o777,0o600)
        self.initialize(); self.assertEqual(host.read_bytes(),old)
    def test_second_device_gets_a_different_host_key(self):
        self.initialize(); first=(self.ssh/'ssh_host_ed25519_key.pub').read_bytes()
        other=self.base/'second-ssh'; other.mkdir(mode=0o700)
        self.m.ensure_host_key(other)
        self.assertNotEqual((other/'ssh_host_ed25519_key.pub').read_bytes(),first)
    def test_missing_persistent_mount_is_rejected_before_identity_writes(self):
        with self.assertRaisesRegex(ValueError,'mount'): self.initialize(mountinfo='')
        self.assertFalse((self.ssh/'ssh_host_ed25519_key').exists())
        self.assertFalse((self.state/'status.json').exists())
    def test_wrong_device_or_read_only_bind_is_rejected(self):
        for text in [self.mounts.replace(self.dev,'99:99',1),self.mounts.replace(' rw,relatime ',' ro,relatime ',1)]:
            with self.assertRaisesRegex(ValueError,'mount'): self.initialize(mountinfo=text)
        self.assertFalse((self.state/'status.json').exists())
    def test_invalid_key_is_rejected_before_identity_writes(self):
        self.pub.chmod(0o600); self.pub.write_text('command="id" ssh-ed25519 not-a-key\n')
        with self.assertRaisesRegex(ValueError,'public key'): self.initialize()
        self.assertEqual(list(self.ssh.iterdir()),[])
    def test_writable_input_or_symlink_is_rejected(self):
        self.pub.chmod(0o666)
        with self.assertRaisesRegex(ValueError,'permission'): self.initialize()
        self.pub.unlink(); self.pub.symlink_to(self.base/'installer.pub')
        with self.assertRaisesRegex(ValueError,'symlink'): self.initialize()
        self.assertFalse((self.state/'status.json').exists())
    def test_effective_password_auth_or_extra_port_prevents_initialization(self):
        for output in [GOOD.replace('passwordauthentication no','passwordauthentication yes'),GOOD+'port 2222\n',GOOD.replace('authenticationmethods publickey','authenticationmethods any')]:
            with self.assertRaisesRegex(ValueError,'SSH'): self.initialize(sshd_configuration=output)
        self.assertEqual(list(self.ssh.iterdir()),[])
    def test_success_marker_does_not_hide_a_missing_private_key(self):
        self.initialize(); (self.ssh/'ssh_host_ed25519_key').unlink()
        with self.assertRaisesRegex(ValueError,'identity'): self.initialize()
        self.assertFalse((self.ssh/'ssh_host_ed25519_key').exists())
    def test_reboot_keeps_administrator_managed_authorized_keys(self):
        self.initialize(); auth=self.root/'.ssh/authorized_keys'
        auth.write_text(self.pub.read_text()+'# administrator comment\n')
        before=auth.read_bytes(); self.initialize(); self.assertEqual(auth.read_bytes(),before)
    def test_existing_identity_is_preserved_and_initial_authorized_key_conflict_fails(self):
        self.m.ensure_host_key(self.ssh); before=(self.ssh/'ssh_host_ed25519_key').read_bytes()
        (self.root/'.ssh').mkdir(mode=0o700)
        auth=self.root/'.ssh/authorized_keys'; auth.write_text('# existing administrator state\n'); auth.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'authorized'): self.initialize()
        self.assertEqual((self.ssh/'ssh_host_ed25519_key').read_bytes(),before)
        self.assertFalse((self.state/'status.json').exists())
    def test_corrupt_or_inconsistent_marker_is_rejected(self):
        marker=self.state/'status.json'; marker.write_text('{bad'); marker.chmod(0o600)
        with self.assertRaises(ValueError): self.initialize()
        marker.unlink(); self.initialize(); saved=json.loads(marker.read_text()); saved['host_key_fingerprint']='SHA256:wrong'; marker.write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError,'identity'): self.initialize()
    def test_missing_input_after_success_is_not_bypassed(self):
        self.initialize(); self.config.unlink()
        with self.assertRaises((ValueError,OSError)): self.initialize()
    def test_marker_boolean_or_numeric_type_confusion_is_rejected(self):
        self.initialize(); marker=self.state/'status.json'; original=json.loads(marker.read_text())
        for field,value in [('schema_version',True),('server_mode',0)]:
            modified=dict(original); modified[field]=value; marker.write_text(json.dumps(modified))
            with self.assertRaises(ValueError): self.initialize()
    def test_marked_device_does_not_recreate_missing_authorized_keys(self):
        self.initialize(); auth=self.root/'.ssh/authorized_keys'; auth.unlink()
        with self.assertRaisesRegex(ValueError,'authorized'): self.initialize()
        self.assertFalse(auth.exists())
    def test_private_key_permissions_are_checked_even_with_marker(self):
        self.initialize(); (self.ssh/'ssh_host_ed25519_key').chmod(0o644)
        with self.assertRaisesRegex(ValueError,'permission'): self.initialize()
    def test_read_only_superblock_is_rejected_after_success(self):
        self.initialize()
        text=self.mounts.replace('/dev/test rw','/dev/test ro')
        with self.assertRaisesRegex(ValueError,'mount'): self.initialize(mountinfo=text)
    def test_failed_root_directory_sync_prevents_success_marker(self):
        original=os.fsync; root_info=self.root.stat()
        def disk_error_on_root(descriptor):
            info=os.fstat(descriptor)
            if (info.st_dev,info.st_ino)==(root_info.st_dev,root_info.st_ino):
                raise OSError('injected root directory sync I/O failure')
            return original(descriptor)
        with mock.patch.object(self.m.os,'fsync',side_effect=disk_error_on_root):
            with self.assertRaises(OSError): self.initialize()
        self.assertFalse((self.state/'status.json').exists())
        before=(self.ssh/'ssh_host_ed25519_key').read_bytes()
        self.initialize()
        self.assertEqual((self.ssh/'ssh_host_ed25519_key').read_bytes(),before)
        self.assertTrue((self.state/'status.json').is_file())

if __name__=='__main__': unittest.main()
