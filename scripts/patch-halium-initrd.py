"""Preserve upstream newc entries, add the verified yuga USB recovery fix."""
import gzip
import hashlib
import pathlib

ANCHOR = b'    write $ANDROID_USB/functions       $USB_FUNCTIONS\n'
INSERT = b'    [ -e $ANDROID_USB/f_rndis/wceis ] && write $ANDROID_USB/f_rndis/wceis 1\n'

def patch_telnet(content):
    if content.count(ANCHOR) != 1 or INSERT in content:
        raise ValueError('Unexpected or already patched upstream telnet script')
    return content.replace(ANCHOR, INSERT + ANCHOR)

def read_entries(archive):
    offset = 0
    while offset < len(archive):
        if archive[offset:offset+6] != b'070701':
            raise ValueError('Expected newc header')
        fields = [int(archive[offset+6+i*8:offset+14+i*8], 16) for i in range(13)]
        encoded = archive[offset+110:offset+110+fields[11]]
        if not encoded.endswith(b'\0'):
            raise ValueError('Invalid cpio name')
        name = encoded[:-1].decode()
        start = (offset + 110 + fields[11] + 3) & ~3
        content = archive[start:start+fields[6]]
        if len(content) != fields[6]:
            raise ValueError('Truncated payload')
        offset = (start+fields[6]+3) & ~3
        yield name, content, fields
        if name == 'TRAILER!!!':
            if archive[offset:].strip(b'\0'):
                raise ValueError('Unexpected trailing data')
            return
    raise ValueError('Missing trailer')

def encode_entry(name, content, fields):
    fields = list(fields)
    encoded = name.encode() + b'\0'
    fields[6], fields[11] = len(content), len(encoded)
    result = b'070701' + b''.join(f'{value:08x}'.encode() for value in fields) + encoded
    result += b'\0' * (-len(result) % 4)
    result += content
    return result + b'\0' * (-len(result) % 4)

def patch_archive(archive, helper):
    entries = list(read_entries(archive))
    if any(name.lstrip('./') == 'sbin/reboot-bootloader' for name, _, _ in entries):
        raise ValueError('Helper already exists')
    matches = sum(name.removeprefix('./') == 'scripts/panic/telnet' for name, _, _ in entries)
    if matches != 1:
        raise ValueError('Expected exactly one panic telnet script')
    output = bytearray()
    for name, content, fields in entries:
        if name.removeprefix('./') == 'scripts/panic/telnet':
            content = patch_telnet(content)
        if name == 'TRAILER!!!':
            inode = max(item[2][0] for item in entries) + 1
            output.extend(encode_entry('sbin/reboot-bootloader', helper, [inode, 0o100755, 0, 0, 1, 0, len(helper), 0, 0, 0, 0, 0, 0]))
        output.extend(encode_entry(name, content, fields))
    return bytes(output)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=pathlib.Path, required=True)
    parser.add_argument('--helper', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    source, target = args.source, args.output
    if target.exists():
        raise SystemExit('Output already exists; choose a new file')
    payload = patch_archive(gzip.decompress(source.read_bytes()), args.helper.read_bytes())
    target.write_bytes(gzip.compress(payload, mtime=0))
    print(target.name, target.stat().st_size, hashlib.sha256(target.read_bytes()).hexdigest())
