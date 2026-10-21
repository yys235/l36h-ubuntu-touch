#!/usr/bin/env python3
"""Build yuga boot image: header from base, new kernel + ramdisk."""
import struct, hashlib, sys, os, pathlib

def u32(buf, off): return struct.unpack_from('<I', buf, off)[0]

def build(base_path, kernel_path, ramdisk_path, out_path, cmdline_extra=""):
    base = pathlib.Path(base_path).read_bytes()
    assert base[:8] == b'ANDROID!', 'not an android boot image'
    page = u32(base, 36)
    assert page == 2048, f'unexpected page {page}'
    old_ksize, old_rsize = u32(base, 8), u32(base, 16)
    # base cmdline = part1(64..576) + part2(608..1632)
    def cstr(b, o, n):
        seg = b[o:o+n]
        z = seg.find(b'\x00')
        return seg[:z if z >= 0 else n].decode('ascii', 'replace')
    cmdline = cstr(base, 64, 512) + cstr(base, 608, 1024)
    # drop pmos-specific uuid params
    keep = [t for t in cmdline.split() if not t.startswith(('pmos_boot_uuid=', 'pmos_root_uuid='))]
    cmdline = ' '.join(keep)
    for extra in cmdline_extra.split():
        if extra not in cmdline.split():
            cmdline += ' ' + extra
    cmd = cmdline.encode('ascii')
    assert len(cmd) <= 1536, 'cmdline too long'

    kernel = pathlib.Path(kernel_path).read_bytes()
    ramdisk = pathlib.Path(ramdisk_path).read_bytes() if ramdisk_path else b''

    align = lambda s: (s + page - 1) // page * page
    out = bytearray(base[:page])  # keep header page
    # sizes
    struct.pack_into('<I', out, 8, len(kernel))
    struct.pack_into('<I', out, 16, len(ramdisk))
    # cmdline fields: zero both, then write split
    out[64:576] = b'\x00' * 512
    out[608:1632] = b'\x00' * 1024
    out[64:64+len(cmd[:512])] = cmd[:512]
    if len(cmd) > 512:
        out[608:608+len(cmd[512:])] = cmd[512:]
    # id: sha1(kernel, u32 ksize, ramdisk, u32 rsize, b'', u32 0)
    h = hashlib.sha1()
    for section, size in ((kernel, len(kernel)), (ramdisk, len(ramdisk)), (b'', 0), (b'', 0)):
        h.update(section)
        h.update(struct.pack('<I', size))
    out[576:608] = b'\x00' * 32
    out[576:596] = h.digest()  # sha1 is 20 bytes; id field is 32

    off_k = page
    off_r = off_k + align(len(kernel))
    out += kernel
    out += b'\x00' * (align(len(kernel)) - len(kernel))
    out += ramdisk
    out += b'\x00' * (align(len(ramdisk)) - len(ramdisk))
    if os.path.exists(out_path): os.remove(out_path)
    pathlib.Path(out_path).write_bytes(bytes(out))
    print(f'OK out={out_path} size={len(out)} kernel={len(kernel)} ramdisk={len(ramdisk)}')
    print('boot command line preserved; not printed')

if __name__ == '__main__':
    base, kernel, ramdisk, out = sys.argv[1:5]
    extra = sys.argv[5] if len(sys.argv) > 5 else ''
    build(base, kernel, ramdisk, out, extra)
