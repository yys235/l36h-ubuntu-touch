"""Check filesystem attributes and reject archives that could escape staging."""
import io
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile
import unittest

from extract_touch_rootfs import extract_rootfs


class RootfsExtractionTests(unittest.TestCase):
    def archive(self, path, entries):
        with tarfile.open(path, 'w') as archive:
            for name, data, kind, link in entries:
                entry = tarfile.TarInfo(name)
                entry.type, entry.linkname = kind, link
                entry.mode = 0o4755 if kind in (tarfile.REGTYPE, tarfile.LNKTYPE) else 0o755
                entry.uid = entry.gid = 32011
                entry.size = len(data) if kind == tarfile.REGTYPE else 0
                archive.addfile(entry, io.BytesIO(data) if entry.isfile() else None)

    def test_attributes_survive_into_ext4(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            archive, stage = root / 'source.tar', root / 'stage'
            self.archive(archive, [
                ('system/usr/bin/app', b'phone executable\n', tarfile.REGTYPE, ''),
                ('system/bin/link', b'', tarfile.SYMTYPE, '/usr/bin/app'),
                ('system/usr/bin/hard', b'', tarfile.LNKTYPE, 'system/usr/bin/app'),
            ])
            extract_rootfs(archive, stage)
            app = stage / 'system/usr/bin/app'
            self.assertEqual(app.read_bytes(), b'phone executable\n')
            self.assertEqual((app.stat().st_uid, app.stat().st_gid), (32011, 32011))
            self.assertEqual(stat.S_IMODE(app.stat().st_mode), 0o4755)
            self.assertEqual((stage / 'system/bin/link').readlink(), Path('/usr/bin/app'))
            self.assertEqual(app.stat().st_ino, (stage / 'system/usr/bin/hard').stat().st_ino)
            image = root / 'filesystem.img'
            subprocess.run(['mke2fs', '-q', '-t', 'ext4', '-b', '4096',
                            '-O', '^64bit,^metadata_csum,^metadata_csum_seed,^orphan_file',
                            '-d', str(stage / 'system'), str(image), '8192'], check=True)
            report = subprocess.run(['debugfs', '-R', 'stat /usr/bin/app', str(image)],
                                    capture_output=True, text=True, check=True).stdout
            self.assertRegex(report, r'Mode:\s+04755')
            self.assertRegex(report, r'User:\s+32011\s+Group:\s+32011')
            filesystem = subprocess.run(['dumpe2fs', '-h', str(image)], capture_output=True,
                                        text=True, check=True).stdout
            features = next(line for line in filesystem.splitlines()
                            if line.startswith('Filesystem features:')).split()[2:]
            self.assertFalse(set(features) & {'64bit', 'metadata_csum', 'metadata_csum_seed', 'orphan_file'})
            subprocess.run(['e2fsck', '-fn', str(image)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            archive = root / 'source.tar'
            self.archive(archive, [('system/../../outside', b'x', tarfile.REGTYPE, '')])
            with self.assertRaises(ValueError):
                extract_rootfs(archive, root / 'stage')
            self.assertFalse((root / 'outside').exists())

    def test_symlink_parent_cannot_redirect_writes(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            outside = root / 'outside'
            outside.mkdir()
            archive = root / 'source.tar'
            self.archive(archive, [
                ('system/escape', b'', tarfile.SYMTYPE, str(outside)),
                ('system/escape/payload', b'x', tarfile.REGTYPE, ''),
            ])
            with self.assertRaises(ValueError):
                extract_rootfs(archive, root / 'stage')
            self.assertFalse((outside / 'payload').exists())

    def test_existing_directory_is_protected(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            archive = root / 'source.tar'
            self.archive(archive, [])
            with self.assertRaises(FileExistsError):
                extract_rootfs(archive, root)

    def test_usrmerge_alias_replaces_empty_wrapper_directory(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            archive = root / 'source.tar'
            self.archive(archive, [
                ('system/lib', b'', tarfile.DIRTYPE, ''),
                ('system/lib/modules', b'', tarfile.DIRTYPE, ''),
                ('system/usr/lib/real', b'library', tarfile.REGTYPE, ''),
                ('system/lib/link', b'', tarfile.SYMTYPE, 'real'),
                ('system/./lib', b'', tarfile.SYMTYPE, 'usr/lib'),
            ])
            extract_rootfs(archive, root / 'stage')
            self.assertTrue((root / 'stage/system/lib').is_symlink())
            self.assertEqual((root / 'stage/system/usr/lib/link').read_bytes(), b'library')
            self.assertTrue((root / 'stage/system/usr/lib/modules').is_dir())

    def test_identical_alias_entries_are_idempotent(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            archive = root / 'source.tar'
            self.archive(archive, [
                ('system/usr/lib/real', b'library', tarfile.REGTYPE, ''),
                ('system/lib', b'', tarfile.SYMTYPE, 'usr/lib'),
                ('system/./lib', b'', tarfile.SYMTYPE, 'usr/lib'),
            ])
            extract_rootfs(archive, root / 'stage')
            self.assertEqual((root / 'stage/system/lib/real').read_bytes(), b'library')

    def test_later_symlink_definition_wins(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            archive = root / 'source.tar'
            self.archive(archive, [
                ('system/etc/mtab', b'', tarfile.SYMTYPE, '../proc/self/mounts'),
                ('system/./etc/mtab', b'', tarfile.SYMTYPE, '/proc/mounts'),
            ])
            extract_rootfs(archive, root / 'stage')
            self.assertEqual((root / 'stage/system/etc/mtab').readlink(), Path('/proc/mounts'))

    def test_resume_requires_identical_regular_file_contents(self):
        with tempfile.TemporaryDirectory(prefix='ut-rootfs-test-') as tmp:
            root = Path(tmp)
            archive, stage = root / 'source.tar', root / 'stage'
            self.archive(archive, [('system/app', b'original', tarfile.REGTYPE, '')])
            extract_rootfs(archive, stage)
            extract_rootfs(archive, stage, resume=True)
            (stage / 'system/app').write_bytes(b'modified')
            with self.assertRaises(ValueError):
                extract_rootfs(archive, stage, resume=True)


if __name__ == '__main__':
    unittest.main()
