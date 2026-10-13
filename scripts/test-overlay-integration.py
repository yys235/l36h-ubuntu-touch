import pathlib, subprocess, tempfile, unittest
script=pathlib.Path(__file__).with_name('integrate-rootfs-overlay.py')
class Overlay(unittest.TestCase):
    def fixture(self, directory):
        root=directory/'system'; (root/'etc').mkdir(parents=True)
        (root/'etc/os-release').write_text('ID=ubuntu\nVERSION_ID=20.04\n')
        config=root/'var/lib/lxc/android/config'; config.parent.mkdir(parents=True)
        config.write_text('lxc.tty.max = 4\n')
        overlay=directory/'overlay'
        (overlay/'etc/systemd/system').mkdir(parents=True)
        (overlay/'etc/systemd/system/example.service').write_text('[Service]\n')
        (overlay/'userdata/yuga-port').mkdir(parents=True)
        (overlay/'userdata/yuga-port/bluetooth-init.sh').write_text('#!/bin/sh\n')
        return root,overlay,config
    def test_routes_userdata_outside_rootfs_and_patches_console(self):
        with tempfile.TemporaryDirectory() as name:
            d=pathlib.Path(name); root,overlay,config=self.fixture(d)
            data=d/'userdata-stage'
            subprocess.run(['python3',str(script),'--root',str(root),'--overlay',str(overlay),'--userdata',str(data)],check=True,capture_output=True)
            self.assertTrue((root/'etc/systemd/system/example.service').is_file())
            self.assertTrue((data/'yuga-port/bluetooth-init.sh').is_file())
            self.assertFalse((root/'userdata/yuga-port/bluetooth-init.sh').exists())
            self.assertIn('lxc.console.path = none',config.read_text())
    def test_symlink_escape_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as name:
            d=pathlib.Path(name); root,overlay,config=self.fixture(d)
            outside=d/'outside'; outside.mkdir(); (root/'etc/systemd').symlink_to(outside,target_is_directory=True)
            r=subprocess.run(['python3',str(script),'--root',str(root),'--overlay',str(overlay),'--userdata',str(d/'userdata-stage')],capture_output=True)
            self.assertNotEqual(r.returncode,0)
            self.assertFalse(list(outside.iterdir()))
            self.assertEqual(config.read_text(),'lxc.tty.max = 4\n')
    def test_existing_userdata_is_preserved(self):
        with tempfile.TemporaryDirectory() as name:
            d=pathlib.Path(name); root,overlay,config=self.fixture(d)
            data=d/'userdata-stage'; data.mkdir(); (data/'sentinel').write_bytes(b'keep')
            r=subprocess.run(['python3',str(script),'--root',str(root),'--overlay',str(overlay),'--userdata',str(data)],capture_output=True)
            self.assertNotEqual(r.returncode,0)
            self.assertEqual((data/'sentinel').read_bytes(),b'keep')
            self.assertEqual(config.read_text(),'lxc.tty.max = 4\n')
if __name__=='__main__': unittest.main()
