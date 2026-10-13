"""Stage the official system/ archive with Unix metadata, without following links."""
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile


def extract_rootfs(archive, destination, progress=False, resume=False):
    destination = Path(destination)
    if resume and (not destination.is_dir() or destination.is_symlink()):
        raise ValueError('Resume requires an existing, ordinary staging directory')
    destination.mkdir(parents=True, exist_ok=resume)
    root = destination.resolve()
    directories, hardlinks, symlinks = [], [], []
    count = size = 0

    def target_path(name):
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] != 'system':
            raise ValueError(f'Invalid rootfs path: {name}')
        target = destination.joinpath(*relative.parts)
        if not target.parent.resolve().is_relative_to(root):
            raise ValueError(f'Path escapes staging: {name}')
        return target

    def attributes(target, member, symlink=False):
        os.chown(target, member.uid, member.gid, follow_symlinks=not symlink)
        if not symlink:
            target.chmod(member.mode & 0o7777)
        for key, value in member.pax_headers.items():
            if key.startswith('SCHILY.xattr.'):
                os.setxattr(target, key.removeprefix('SCHILY.xattr.'),
                            value.encode('utf-8', 'surrogateescape'), follow_symlinks=not symlink)
            elif key.startswith('LIBARCHIVE.xattr.'):
                raise ValueError(f'Unsupported encoded xattr: {key}')
        if not symlink:
            os.utime(target, (member.mtime, member.mtime))

    with tarfile.open(archive, mode='r|*') as bundle:
        for member in bundle:
            target = target_path(member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                directories.append((target, member))
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                if resume:
                    if target.is_symlink() or not target.is_file():
                        raise ValueError(f'Missing regular file for resume: {member.name}')
                    with bundle.extractfile(member) as source, target.open('rb') as existing:
                        while block := source.read(1024 * 1024):
                            if existing.read(len(block)) != block:
                                raise ValueError(f'Resume content mismatch: {member.name}')
                        if existing.read(1):
                            raise ValueError(f'Resume length mismatch: {member.name}')
                    inode = target.stat()
                    if (inode.st_uid, inode.st_gid, stat.S_IMODE(inode.st_mode)) != (member.uid, member.gid, member.mode & 0o7777):
                        raise ValueError(f'Resume metadata mismatch: {member.name}')
                else:
                    with bundle.extractfile(member) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output)
                    attributes(target, member)
                count += 1
                size += member.size
                if progress and count % 5000 == 0:
                    print(f'EXTRACT_PROGRESS files={count} bytes={size}', file=sys.stderr, flush=True)
            elif member.islnk():
                hardlinks.append((target, target_path(member.linkname), member))
            elif member.issym():
                symlinks.append((target, member))
            else:
                raise ValueError(f'Unsupported special file: {member.name}')
    for target, original, member in hardlinks:
        if not original.is_file() or original.is_symlink():
            raise ValueError(f'Invalid hardlink: {member.name}')
        inode = original.stat()
        if (inode.st_uid, inode.st_gid, stat.S_IMODE(inode.st_mode)) != (member.uid, member.gid, member.mode & 0o7777):
            raise ValueError(f'Conflicting hardlink attributes: {member.name}')
        target.parent.mkdir(parents=True, exist_ok=True)
        if resume and target.exists():
            if target.is_symlink() or target.stat().st_ino != original.stat().st_ino:
                raise ValueError(f'Resume hardlink mismatch: {member.name}')
        else:
            os.link(original, target)
    # Create links last. Absolute links are correct inside the phone rootfs,
    # but no extraction write may follow them on the build computer.
    for target, member in sorted(symlinks, key=lambda item: len(item[0].parts)):
        if not target.parent.resolve().is_relative_to(root):
            raise ValueError(f'Symlink parent escapes staging: {member.name}')
        if target.is_symlink() and os.readlink(target) == member.linkname:
            attributes(target, member, symlink=True)
            continue
        if target.is_symlink():
            target.unlink()  # Archive overlays replace the link itself, never its referent.
        if target.is_dir() and not target.is_symlink():
            wrappers = list(target.rglob('*'))
            if all(path.is_dir() and not path.is_symlink() for path in wrappers):
                # Preserve empty wrapper subdirectories in the phone namespace.
                link = PurePosixPath(member.linkname)
                canonical = (destination / 'system' / str(link).lstrip('/')
                             if link.is_absolute() else target.parent / str(link)).resolve()
                if not canonical.is_relative_to(root):
                    raise ValueError(f'Alias target escapes staging: {member.name}')
                canonical.mkdir(parents=True, exist_ok=True)
                for wrapper in wrappers:
                    (canonical / wrapper.relative_to(target)).mkdir(parents=True, exist_ok=True)
                for wrapper in sorted(wrappers, key=lambda path: len(path.parts), reverse=True):
                    wrapper.rmdir()
                target.rmdir()
        if target.exists() or target.is_symlink():
            raise ValueError(f'Symlink collides with extracted path: {member.name}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(member.linkname)
        attributes(target, member, symlink=True)
    for target, member in reversed(directories):
        if not target.is_symlink() and target.resolve() == target.absolute():
            attributes(target, member)
    return {'regular_files': count, 'regular_bytes': size, 'symlinks': len(symlinks),
            'hardlinks': len(hardlinks)}


if __name__ == '__main__':
    arguments = [argument for argument in sys.argv[1:] if argument != '--resume']
    print(json.dumps(extract_rootfs(*arguments, progress=True, resume='--resume' in sys.argv[1:]), indent=2))
