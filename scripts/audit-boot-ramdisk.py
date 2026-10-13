"""Inventory initramfs without exporting file contents or credential values."""
import argparse, gzip, hashlib, importlib.util, json, pathlib, struct
p = argparse.ArgumentParser()
p.add_argument('image', type=pathlib.Path)
p.add_argument('--output', type=pathlib.Path, required=True)
a = p.parse_args()
spec = importlib.util.spec_from_file_location('cpio', pathlib.Path(__file__).with_name('patch-halium-initrd.py'))
cpio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpio)
b = a.image.read_bytes()
assert b[:8] == b'ANDROID!'
ks, rs, page = (struct.unpack_from('<I', b, n)[0] for n in (8,16,36))
assert page == 2048
off = page + ((ks + page - 1) // page * page)
ramdisk = b[off:off + rs]
files = []
findings = []
for name, content, fields in cpio.read_entries(gzip.decompress(ramdisk)):
    assert not name.startswith('/') and '..' not in pathlib.PurePosixPath(name).parts
    files.append({'path':name, 'mode':oct(fields[1]), 'uid':fields[2], 'gid':fields[3], 'bytes':len(content), 'sha256':hashlib.sha256(content).hexdigest()})
    if b'PRIVATE KEY-----' in content:
        findings.append({'path':name,'kind':'private-key-marker'})
    if 'authorized_keys' in name or 'authorizedkeys' in name:
        findings.append({'path':name,'kind':'authorized-key-file'})
    if name.removeprefix('./') in ('etc/passwd','etc/shadow'):
        findings.append({'path':name,'kind':'account-file-requires-review'})
    if b'telnetd' in content and len(content) < 256000:
        findings.append({'path':name,'kind':'telnet-reference-requires-review'})
report = {'scope':'ramdisk-paths-metadata-hashes-and-limited-markers', 'image_sha256':hashlib.sha256(b).hexdigest(), 'ramdisk_sha256':hashlib.sha256(ramdisk).hexdigest(), 'files':files,'findings':findings,'full_security_review_complete':False}
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'entries':len(files),'findings':findings,'full_security_review_complete':False}))
