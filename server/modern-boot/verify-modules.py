#!/usr/bin/env python3
"""Reject malformed ARM modules before they reach a hardware probe."""
import argparse
import pathlib
import struct
import subprocess


def validate_elf(blob):
    if len(blob) < 52 or blob[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('Expected ARM ELF32 little-endian module')
    kind, machine = struct.unpack_from('<HH', blob, 16)
    if kind != 1 or machine != 40:
        raise ValueError('Expected ARM relocatable module')
    offset = struct.unpack_from('<I', blob, 32)[0]
    header_size, _, _, stride, count, strings = struct.unpack_from('<HHHHHH', blob, 40)
    if header_size != 52 or stride != 40 or not count or offset < 52 or offset + count * stride > len(blob) or strings >= count:
        raise ValueError('Invalid ELF section table bounds')
    for index in range(count):
        fields = struct.unpack_from('<IIIIIIIIII', blob, offset + index * stride)
        section_type, start, size = fields[1], fields[4], fields[5]
        if section_type not in (0, 8) and (start > len(blob) or start + size > len(blob)):
            raise ValueError('Invalid ELF section content bounds')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=pathlib.Path)
    args = parser.parse_args()
    paths = sorted(p for p in args.directory.rglob('*') if p.name.endswith(('.ko', '.ko.zst')))
    if not paths:
        raise SystemExit('No kernel modules found')
    for path in paths:
        blob = subprocess.run(['zstd', '-dc', str(path)], check=True, capture_output=True).stdout if path.suffix == '.zst' else path.read_bytes()
        try:
            validate_elf(blob)
        except ValueError as error:
            raise SystemExit(f'{path}: {error}') from error
    print(f'Validated ARM ELF structure of {len(paths)} modules')


if __name__ == '__main__':
    main()
