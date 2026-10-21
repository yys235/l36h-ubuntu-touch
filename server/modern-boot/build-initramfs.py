#!/usr/bin/env python3
"""Package a static ARM diagnostic environment; no host root privileges needed."""
import argparse
import gzip
import importlib.util
import pathlib
import stat
import struct
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('newc', HERE.parents[1]/'scripts/patch-halium-initrd.py')
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)


def safe_name(name):
    path = pathlib.PurePosixPath(name)
    if not name or name.startswith('/') or '\\' in name or '\0' in name or '..' in path.parts or str(path) != name or name == '.':
        raise ValueError('unsafe archive path: ' + name)


def link_target(name, target):
    if not target or target.startswith('/') or '\\' in target or '\0' in target:
        raise ValueError('symlink escapes archive: ' + name)
    parts = list(pathlib.PurePosixPath(name).parent.parts)
    for component in target.split('/'):
        if component == '..':
            if not parts:
                raise ValueError('symlink escapes archive: ' + name)
            parts.pop()
        elif component not in ('', '.'):
            parts.append(component)
    return '/'.join(parts)


def static_arm(blob):
    if len(blob) < 52 or blob[:7] != b'\x7fELF\x01\x01\x01' or struct.unpack_from('<H', blob, 18)[0] != 40:
        raise ValueError('BusyBox must be an ARM ELF32 little-endian executable')
    if struct.unpack_from('<H', blob, 16)[0] not in (2, 3):
        raise ValueError('BusyBox is not executable ELF')
    offset = struct.unpack_from('<I', blob, 28)[0]
    size, count = struct.unpack_from('<HH', blob, 42)
    if size != 32 or not count or offset + size * count > len(blob):
        raise ValueError('invalid ELF program headers')
    if any(struct.unpack_from('<I', blob, offset + i * size)[0] == 3 for i in range(count)):
        raise ValueError('BusyBox must be static (PT_INTERP forbidden)')


def build_archive(entries):
    by_name = {}
    for name, content, mode in entries:
        safe_name(name)
        if name in by_name:
            raise ValueError('duplicate archive path: ' + name)
        if not isinstance(content, bytes) or stat.S_IFMT(mode) not in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK):
            raise ValueError('unsupported archive entry: ' + name)
        if stat.S_ISLNK(mode):
            link_target(name, content.decode())
        by_name[name] = (content, mode)
    init, mode = by_name.get('init', (b'', 0))
    if not stat.S_ISREG(mode) or not mode & 0o111 or not init.startswith(b'#!/bin/sh\n'):
        raise ValueError('expected executable init with /bin/sh interpreter')
    name = 'bin/sh'
    seen = set()
    while name in by_name and stat.S_ISLNK(by_name[name][1]):
        if name in seen:
            raise ValueError('interpreter symlink cycle')
        seen.add(name)
        name = link_target(name, by_name[name][0].decode())
    if name not in by_name or not stat.S_ISREG(by_name[name][1]) or not by_name[name][1] & 0o111:
        raise ValueError('missing executable shell interpreter')
    busybox, mode = by_name.get('bin/busybox', (b'', 0))
    if not stat.S_ISREG(mode) or not mode & 0o111:
        raise ValueError('missing executable BusyBox')
    static_arm(busybox)
    output = bytearray()
    for inode, (name, (content, mode)) in enumerate(sorted(by_name.items()), 1):
        output.extend(newc.encode_entry(name, content, [inode, mode, 0, 0, 1, 0, len(content), 0, 0, 0, 0, 0, 0]))
    output.extend(newc.encode_entry('TRAILER!!!', b'', [len(by_name)+1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]))
    return bytes(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--busybox', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    entries = [(name, b'', stat.S_IFDIR | (0o1777 if name == 'tmp' else 0o755))
               for name in ('bin', 'sbin', 'dev', 'proc', 'sys', 'run', 'tmp')]
    entries += [('bin/busybox', args.busybox.read_bytes(), stat.S_IFREG | 0o755),
                ('bin/sh', b'busybox', stat.S_IFLNK | 0o777)]
    for name, source in [('init', 'init'), ('sbin/usb-gadget.sh', 'usb-gadget.sh'),
                         ('sbin/collect-state.sh', 'collect-state.sh')]:
        entries.append((name, (HERE/source).read_bytes(), stat.S_IFREG | 0o755))
    payload = gzip.compress(build_archive(entries), mtime=0)
    with args.output.open('xb') as output:
        output.write(payload)
    print('Built diagnostic initramfs:', args.output.name, len(payload))


if __name__ == '__main__':
    main()
