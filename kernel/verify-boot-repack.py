"""Verify legacy Android boot repacking without flashing or exposing cmdline."""
import argparse, gzip, hashlib, importlib.util, pathlib, struct, tempfile
parser = argparse.ArgumentParser()
parser.add_argument('image', type=pathlib.Path)
parser.add_argument('builder', type=pathlib.Path)
args = parser.parse_args()
b = args.image.read_bytes()
assert b[:8] == b'ANDROID!'
u32 = lambda offset: struct.unpack_from('<I', b, offset)[0]
ks, rs, page = u32(8), u32(16), u32(36)
assert page == 2048
assert u32(24) == 0 and u32(40) == 0, 'Unsupported second stage or DT payload'
aligned = lambda n: (n + page - 1) // page * page
kernel = b[page:page + ks]
ramdisk = b[page + aligned(ks):page + aligned(ks) + rs]
assert len(kernel) == ks and len(ramdisk) == rs
spec = importlib.util.spec_from_file_location('mkboot', args.builder)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as name:
    root = pathlib.Path(name)
    (root / 'zImage').write_bytes(kernel)
    (root / 'initrd.gz').write_bytes(ramdisk)
    module.build(str(args.image), str(root / 'zImage'), str(root / 'initrd.gz'), str(root / 'repacked.img'))
    assert (root / 'repacked.img').read_bytes() == b, 'Repacked image differs'
print('BYTE_IDENTICAL_BOOT_REPACK', hashlib.sha256(b).hexdigest())
raw = gzip.decompress(ramdisk)
for marker in (b'PRIVATE KEY-----', b'authorized_keys', b'authorizedkeys', b'ssh_host_', b'dropbear_ed25519_host_key'):
    print('RAMDISK_SENSITIVE_MARKER', marker.decode(), marker in raw)
print('Marker scan is preliminary; complete file/content audit still required.')
