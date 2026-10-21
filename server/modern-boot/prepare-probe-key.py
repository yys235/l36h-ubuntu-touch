#!/usr/bin/env python3
"""Validate and copy a single installer public key; never handles private keys."""
import argparse
import base64
import pathlib
import struct
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-key', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        data = args.public_key.read_bytes()
        lines = data.strip().splitlines()
        if len(lines) != 1:
            raise ValueError('expected one public key')
        parts = lines[0].split()
        if len(parts) < 2 or parts[0] != b'ssh-ed25519':
            raise ValueError('expected Ed25519 public key')
        blob = base64.b64decode(parts[1], validate=True)
        if len(blob) != 51 or blob[:4] != struct.pack('>I', 11) or blob[4:15] != b'ssh-ed25519' or blob[15:19] != struct.pack('>I', 32):
            raise ValueError('invalid Ed25519 public key encoding')
        with args.output.open('xb') as output:
            output.write(lines[0]+b'\n')
    except (OSError, ValueError) as error:
        print('Public key preparation failed: '+str(error), file=sys.stderr)
        return 1
    print('Installer public key validated')
    return 0


if __name__ == '__main__':
    sys.exit(main())
