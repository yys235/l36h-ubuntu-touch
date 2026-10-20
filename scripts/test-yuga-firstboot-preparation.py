import json,os,pathlib,shutil,subprocess,tempfile,unittest

SCRIPT=pathlib.Path(__file__).with_name('prepare-yuga-firstboot.py')
OVERLAY=SCRIPT.parent.parent/'overlay/etc/systemd/system'

class Preparation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=pathlib.Path(self.temp.name); self.root=self.base/'rootfs'
        for name in ['etc/ssh/sshd_config.d','etc/systemd/system','lib/systemd/system','root','usr/lib']:
            (self.root/name).mkdir(parents=True,exist_ok=True)
        (self.root/'etc/os-release').write_text('ID=ubuntu\nVERSION_ID="20.04"\n')
        (self.root/'etc/ssh/sshd_config').write_text('Include /etc/ssh/sshd_config.d/*.conf\nUsePAM yes\n')
        (self.root/'lib/systemd/system/ssh.service').write_text('[Service]\nExecStart=/usr/sbin/sshd -D\n')
        for name in ['yuga-wlan-init.service','yuga-backlight-interface.service','yuga-server-awake.service']:
            shutil.copyfile(OVERLAY/name,self.root/'etc/systemd/system'/name)
        self.key=self.base/'installer-key'
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(self.key)],check=True)
        self.pub=self.key.with_suffix('.pub'); self.data=self.base/'userdata-out'
    def run_prepare(self,*extra,key=None,root=None):
        return subprocess.run(['python3',str(SCRIPT),'--root',str(root or self.root),'--userdata',str(self.data),'--public-key',str(key or self.pub),*extra],capture_output=True,text=True)
    def assert_rejected(self,result,message):
        self.assertNotEqual(result.returncode,0)
        self.assertIn(message,result.stderr.lower())
        self.assertFalse(self.data.exists())
        self.assertFalse((self.root/'etc/ssh/sshd_config.d/00-yuga-bootstrap.conf').exists())
    def test_installs_separate_key_payload_and_enables_required_services(self):
        r=self.run_prepare(); self.assertEqual(r.returncode,0,r.stderr)
        target=self.data/'yuga-firstboot/input/authorized_key'
        self.assertEqual(target.read_bytes(),self.pub.read_bytes())
        self.assertEqual(target.stat().st_mode & 0o777,0o400)
        self.assertEqual(json.loads((target.parent/'config.json').read_text()),{'schema_version':1,'server_mode':False})
        for name in ['ssh.service','yuga-wlan-init.service','yuga-backlight-interface.service']:
            self.assertTrue((self.root/'etc/systemd/system/multi-user.target.wants'/name).is_symlink())
        self.assertFalse((self.root/'etc/systemd/system/multi-user.target.wants/yuga-server-awake.service').exists())
        self.assertFalse((self.root/'etc/systemd/system/sleep.target').is_symlink())
        self.assertTrue((self.root/'usr/lib/yuga-firstboot/yuga_firstboot.py').is_file())
    def test_server_mode_enables_awake_and_masks_all_sleep_targets(self):
        r=self.run_prepare('--server-mode'); self.assertEqual(r.returncode,0,r.stderr)
        for name in ['sleep.target','suspend.target','hibernate.target','hybrid-sleep.target']:
            self.assertEqual(os.readlink(self.root/'etc/systemd/system'/name),'/dev/null')
        self.assertTrue((self.root/'etc/systemd/system/multi-user.target.wants/yuga-server-awake.service').is_symlink())
    def test_private_key_is_rejected_before_any_writes(self):
        self.assert_rejected(self.run_prepare(key=self.key),'public key')
    def test_multiple_keys_and_authorized_key_options_are_rejected(self):
        text=self.pub.read_text()
        for value in [text+text,'command="id" '+text,'ssh-ed25519 not-a-real-key\n','\n'+text,text+'\n']:
            self.pub.write_text(value)
            self.assert_rejected(self.run_prepare(),'public key')
    def test_key_symlink_is_rejected(self):
        link=self.base/'key-link'; link.symlink_to(self.pub)
        self.assert_rejected(self.run_prepare(key=link),'public key')
    def test_host_root_is_rejected(self):
        self.assert_rejected(self.run_prepare(root=pathlib.Path('/')),'staging')
    def test_existing_userdata_is_not_overwritten(self):
        self.data.mkdir(); sentinel=self.data/'sentinel'; sentinel.write_text('keep')
        r=self.run_prepare(); self.assertNotEqual(r.returncode,0); self.assertIn('userdata',r.stderr.lower())
        self.assertEqual(sentinel.read_text(),'keep')
        self.assertFalse((self.root/'etc/ssh/sshd_config.d/00-yuga-bootstrap.conf').exists())
    def test_symlink_ancestor_cannot_redirect_installed_files(self):
        outside=self.base/'outside'; (self.root/'usr/lib').rename(outside)
        (self.root/'usr/lib').symlink_to(outside,target_is_directory=True)
        self.assert_rejected(self.run_prepare(),'symlink')
        self.assertEqual(list(outside.iterdir()),[])
    def test_unexpected_ssh_fragment_is_rejected(self):
        (self.root/'etc/ssh/sshd_config.d/000-existing.conf').write_text('PasswordAuthentication yes\n')
        self.assert_rejected(self.run_prepare(),'ssh')
    def test_source_host_identity_is_rejected(self):
        (self.root/'etc/ssh/ssh_host_ed25519_key').write_text('not-for-publication')
        self.assert_rejected(self.run_prepare(),'identity')
    def test_existing_ssh_service_override_is_rejected(self):
        (self.root/'etc/systemd/system/ssh.service').write_text('[Service]\nExecStart=/usr/sbin/sshd -o PasswordAuthentication=yes\n')
        self.assert_rejected(self.run_prepare(),'ssh')
    def test_existing_ssh_service_dropin_is_rejected(self):
        directory=self.root/'etc/systemd/system/ssh.service.d'; directory.mkdir()
        (directory/'99-local.conf').write_text('[Service]\nExecStart=\nExecStart=/bin/false\n')
        self.assert_rejected(self.run_prepare(),'ssh')
    def test_official_os_release_relative_link_inside_staging_is_supported(self):
        metadata=self.root/'etc/os-release'; (self.root/'usr/lib/os-release').write_bytes(metadata.read_bytes())
        metadata.unlink(); metadata.symlink_to('../usr/lib/os-release')
        r=self.run_prepare(); self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue((self.data/'yuga-firstboot/input/authorized_key').is_file())
    def test_os_release_link_outside_staging_is_rejected(self):
        outside=self.base/'outside-release'; outside.write_text('VERSION_ID=20.04\n')
        metadata=self.root/'etc/os-release'; metadata.unlink(); metadata.symlink_to(outside)
        self.assert_rejected(self.run_prepare(),'metadata')
    def test_exact_official_password_disabled_fragment_is_accepted(self):
        (self.root/'etc/ssh/sshd_config.d/50-lxc-android-config.conf').write_text('PasswordAuthentication=no\n')
        r=self.run_prepare(); self.assertEqual(r.returncode,0,r.stderr)
    def test_modified_official_ssh_fragment_is_rejected(self):
        (self.root/'etc/ssh/sshd_config.d/50-lxc-android-config.conf').write_text('PasswordAuthentication=yes\n')
        self.assert_rejected(self.run_prepare(),'ssh')
    def test_merged_usr_readonly_service_alias_is_supported(self):
        (self.root/'lib/systemd').rename(self.root/'usr/lib/systemd')
        (self.root/'lib').rmdir(); (self.root/'lib').symlink_to('usr/lib')
        r=self.run_prepare(); self.assertEqual(r.returncode,0,r.stderr)
    def test_readonly_service_alias_outside_image_is_rejected(self):
        outside=self.base/'outside-lib'; (self.root/'lib').rename(outside)
        (self.root/'lib').symlink_to(outside)
        self.assert_rejected(self.run_prepare(),'service')

if __name__=='__main__': unittest.main()
