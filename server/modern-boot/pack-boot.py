#!/usr/bin/env python3
"""Pack and independently validate a Yuga diagnostic boot image."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import struct
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CMDLINE = 'console=ttyMSM0,115200,n8 fw_devlink=permissive yuga_probe=modern-v1'
CAPACITY = 20 * 1024 * 1024
spec = importlib.util.spec_from_file_location('mkboot', HERE.parents[1]/'kernel/mkboot.py')
mkboot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mkboot)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def align(value):
    return (value + 2047) & ~2047


def check_header(blob):
    if len(blob) < 2048 or blob[:8] != b'ANDROID!':
        raise ValueError('invalid Android boot magic or truncated header')
    for offset, expected in [(12, 0x80208000), (20, 0x82200000), (28, 0x81100000),
                             (32, 0x80200100), (36, 2048)]:
        if struct.unpack_from('<I', blob, offset)[0] != expected:
            raise ValueError('unexpected boot address/page size')
    if struct.unpack_from('<I', blob, 24)[0] or struct.unpack_from('<I', blob, 40)[0]:
        raise ValueError('unexpected second stage or separate DTB section')


def check_dtb(blob):
    if len(blob) < 40:
        raise ValueError('truncated DTB header')
    magic, total, tree_off, strings_off, _, version, _, _, strings_size, tree_size = struct.unpack_from('>10I', blob)
    if magic != 0xd00dfeed or total != len(blob) or version < 17:
        raise ValueError('invalid DTB magic, length or version')
    if tree_off < 40 or tree_off + tree_size > total or strings_off < 40 or strings_off + strings_size > total:
        raise ValueError('invalid DTB bounds')
    strings = blob[strings_off:strings_off+strings_size]
    pos, end, depth, matched = tree_off, tree_off+tree_size, 0, False
    try:
        while pos < end:
            token = struct.unpack_from('>I', blob, pos)[0]
            pos += 4
            if token == 1:
                terminator = blob.index(b'\0', pos, end)
                pos = (terminator + 4) & ~3
                depth += 1
            elif token == 2:
                depth -= 1
                if depth < 0:
                    raise ValueError('invalid DTB nesting')
            elif token == 3:
                length, name_offset = struct.unpack_from('>II', blob, pos)
                pos += 8
                if pos + length > end or name_offset >= len(strings):
                    raise ValueError('invalid DTB property bounds')
                name_end = strings.index(b'\0', name_offset)
                if depth == 1 and strings[name_offset:name_end] == b'compatible':
                    matched = b'sony,xperia-yuga' in blob[pos:pos+length].split(b'\0')
                pos = (pos + length + 3) & ~3
            elif token == 4:
                continue
            elif token == 9:
                if depth != 0:
                    raise ValueError('unclosed DTB node')
                if not matched:
                    raise ValueError('DTB is not a Sony Yuga board')
                return
            else:
                raise ValueError('unknown DTB token')
    except (struct.error, IndexError) as error:
        raise ValueError('malformed DTB') from error
    raise ValueError('DTB lacks complete tree')


def check_zimage(blob):
    if len(blob) < 48 or struct.unpack_from('<I', blob, 36)[0] != 0x016f2818:
        raise ValueError('invalid ARM zImage magic')


def make_boot(base, kernel, dtb, ramdisk, cmdline=CMDLINE):
    check_header(base)
    check_zimage(kernel)
    check_dtb(dtb)
    command = cmdline.encode('ascii')
    if len(command) >= 1536 or b'\0' in command:
        raise ValueError('invalid boot command line length/content')
    if not ramdisk.startswith(b'\x1f\x8b'):
        raise ValueError('expected gzip diagnostic ramdisk')
    clean = bytearray(base[:2048])
    clean[64:576] = bytes(512)
    clean[608:1632] = bytes(1024)
    clean[64:64+len(command[:512])] = command[:512]
    clean[608:608+len(command[512:])] = command[512:]
    appended = kernel + bytes(-len(kernel) % 4) + dtb
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        for name, content in [('base', clean), ('kernel', appended), ('ramdisk', ramdisk)]:
            (root/name).write_bytes(content)
        with contextlib.redirect_stdout(io.StringIO()):
            mkboot.build(str(root/'base'), str(root/'kernel'), str(root/'ramdisk'), str(root/'boot.img'))
        image = (root/'boot.img').read_bytes()
    metadata = {'schema': 1, 'kind': 'yuga-modern-ram-diagnostic', 'bytes': len(image),
                'sha256': digest(image), 'boot_capacity': CAPACITY, 'cmdline': cmdline,
                'kernel': {'bytes': len(kernel), 'sha256': digest(kernel)},
                'dtb': {'bytes': len(dtb), 'sha256': digest(dtb)},
                'ramdisk': {'bytes': len(ramdisk), 'sha256': digest(ramdisk)},
                'base_sha256': digest(base)}
    verify_image(image, metadata)
    return image, metadata


def verify_image(image, metadata):
    if metadata.get('schema') != 1 or metadata.get('kind') != 'yuga-modern-ram-diagnostic':
        raise ValueError('unexpected diagnostic manifest')
    if len(image) != metadata['bytes'] or len(image) > CAPACITY or metadata['boot_capacity'] != CAPACITY:
        raise ValueError('image size/capacity mismatch')
    if digest(image) != metadata['sha256']:
        raise ValueError('image SHA256 mismatch')
    check_header(image)
    ksize, rsize = struct.unpack_from('<I', image, 8)[0], struct.unpack_from('<I', image, 16)[0]
    roff = 2048 + align(ksize)
    if roff + align(rsize) != len(image):
        raise ValueError('image layout length mismatch')
    kernel_size = metadata['kernel']['bytes']
    dtb_offset = 2048 + ((kernel_size + 3) & ~3)
    if ksize != ((kernel_size+3) & ~3) + metadata['dtb']['bytes'] or rsize != metadata['ramdisk']['bytes']:
        raise ValueError('component length mismatch')
    for name, data in [('kernel', image[2048:2048+kernel_size]),
                       ('dtb', image[dtb_offset:2048+ksize]),
                       ('ramdisk', image[roff:roff+rsize])]:
        if digest(data) != metadata[name]['sha256']:
            raise ValueError(name + ' SHA256 mismatch')
    check_zimage(image[2048:2048+kernel_size])
    check_dtb(image[dtb_offset:2048+ksize])
    actual_cmd = image[64:576].split(b'\0', 1)[0] + image[608:1632].split(b'\0', 1)[0]
    if actual_cmd.decode('ascii') != metadata['cmdline']:
        raise ValueError('command line mismatch')
    boot_id = hashlib.sha1()
    for content in [image[2048:2048+ksize], image[roff:roff+rsize], b'', b'']:
        boot_id.update(content)
        boot_id.update(struct.pack('<I', len(content)))
    if image[576:596] != boot_id.digest():
        raise ValueError('Android boot ID mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'kernel', 'dtb', 'ramdisk', 'kernel-manifest', 'output'):
        parser.add_argument('--'+name, type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(args.output.suffix+'.json').exists():
        parser.error('output already exists; choose a new path')
    kernel, dtb = args.kernel.read_bytes(), args.dtb.read_bytes()
    build = json.loads(args.kernel_manifest.read_text())
    for name, blob in [('zImage', kernel), ('yuga.dtb', dtb)]:
        expected = build['files'][name]
        if len(blob) != expected['bytes'] or digest(blob) != expected['sha256']:
            raise ValueError('mismatched kernel build artifact: '+name)
    image, metadata = make_boot(args.base.read_bytes(), kernel, dtb, args.ramdisk.read_bytes())
    metadata['kernel_release'] = build['kernel_release']
    metadata['source_commit'] = build['source_commit']
    if 'dtb_derivation' in build:
        metadata['dtb_derivation'] = build['dtb_derivation']
    with args.output.open('xb') as output:
        output.write(image)
    args.output.with_suffix(args.output.suffix+'.json').write_bytes((json.dumps(metadata, indent=2)+'\n').encode())
    print(args.output.name, len(image), metadata['sha256'])


if __name__ == '__main__':
    main()
