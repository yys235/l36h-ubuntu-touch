#!/usr/bin/env python3
"""Verify immutable local build inputs before extracting or compiling them."""
import argparse
import hashlib
import json
import pathlib
import re
import sys


def verify(manifest, directory):
    data = json.loads(pathlib.Path(manifest).read_text())
    if data.get('schema') != 1:
        raise ValueError('unsupported input manifest schema')
    records = data.get('files')
    if not isinstance(records, list) or not records:
        raise ValueError('files must be a non-empty list')
    root = pathlib.Path(directory).resolve(strict=True)
    seen = set()
    for record in records:
        name = record.get('name')
        if not isinstance(name, str) or not name or name in ('.', '..') or any(c in name for c in '/\\:\x00'):
            raise ValueError('unsafe input name')
        if name in seen:
            raise ValueError('duplicate input: ' + name)
        seen.add(name)
        expected_size, expected_sha = record.get('bytes'), record.get('sha256')
        if type(expected_size) is not int or expected_size <= 0:
            raise ValueError('invalid input size: ' + name)
        if not isinstance(expected_sha, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha):
            raise ValueError('invalid SHA256: ' + name)
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing input or symlink: ' + name)
        if path.stat().st_size != expected_size:
            raise ValueError('size mismatch: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != expected_sha:
            raise ValueError('SHA256 mismatch: ' + name)
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    try:
        count = verify(args.manifest, args.directory)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print('Input verification failed: ' + str(error), file=sys.stderr)
        return 1
    print(f'Verified {count} input(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
