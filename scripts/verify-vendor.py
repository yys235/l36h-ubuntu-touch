"""Verify checked-out device blobs against the saved GitHub commit tree."""
import hashlib
import json
from pathlib import Path

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--manifest', type=Path, required=True)
args = parser.parse_args()
tree = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
assert not tree.get('truncated', False)
root = args.root
count = size = 0
for entry in tree['tree']:
    if entry['type'] != 'blob' or not entry['path'].startswith(('yuga/', 'fusion3-common/')):
        continue
    path = root / entry['path']
    data = path.read_bytes()
    assert len(data) == entry['size'], path
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert actual == entry['sha'], path
    count += 1
    size += len(data)
assert count > 0
print(f'VENDOR_VERIFIED files={count} bytes={size}')
