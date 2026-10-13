import pathlib, subprocess, tempfile, unittest
script=pathlib.Path(__file__).with_name('build-rootfs-image.py')
class ImageBuilder(unittest.TestCase):
    def test_small_ext4_image_has_old_kernel_features_and_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); stage=root/'stage'; (stage/'etc').mkdir(parents=True)
            (stage/'etc/os-release').write_text('ID=ubuntu\nVERSION_ID=20.04\n')
            (stage/'sbin').mkdir(); (stage/'sbin/init').write_bytes(b'test-init')
            image=root/'rootfs.img'
            subprocess.run(['python3',str(script),'--source',str(stage),'--output',str(image),'--size-mib','32'],check=True,capture_output=True)
            self.assertEqual(image.stat().st_size,32*1024**2)
            stats=subprocess.run(['debugfs','-R','stats',str(image)],check=True,capture_output=True,text=True).stdout
            line=next(x for x in stats.splitlines() if x.startswith('Filesystem features:'))
            self.assertFalse(set(line.split()[2:]) & {'64bit','metadata_csum','metadata_csum_seed','orphan_file','encrypt','casefold'})
            content=subprocess.run(['debugfs','-R','cat /sbin/init',str(image)],check=True,capture_output=True).stdout
            self.assertEqual(content,b'test-init')
if __name__=='__main__': unittest.main()
