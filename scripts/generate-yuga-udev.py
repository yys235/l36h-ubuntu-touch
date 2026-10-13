"""Translate Sony device-node permissions using Android's numeric identities.

Sysfs attributes use separate tmpfiles adjustments to existing paths only.
"""
import pathlib
import re

def device_rule(line, identities):
    fields = line.split()
    if len(fields) != 4:
        raise ValueError('Expected device, mode, owner and group')
    node, mode, owner, group = fields
    if not re.fullmatch(r'/dev/[a-zA-Z0-9_./:*?\[\]-]+', node) or '..' in node.split('/'):
        raise ValueError('Invalid device node')
    if not re.fullmatch(r'0[0-7]{3}', mode):
        raise ValueError('Invalid permission mode')
    try:
        uid, gid = identities[owner], identities[group]
    except KeyError as error:
        raise ValueError('Unknown Android identity: ' + str(error)) from error
    return f'ACTION=="add|change", ENV{{DEVNAME}}=="{node}", OWNER="{uid}", GROUP="{gid}", MODE="{mode}"'

def sysfs_rule(line, identities):
    fields = line.split()
    if len(fields) != 5:
        raise ValueError('Expected sysfs directory, attribute, mode, owner and group')
    directory, attribute, mode, owner, group = fields
    if not re.fullmatch(r'/sys/[a-zA-Z0-9_./:*?\[\]-]+', directory) or '..' in directory.split('/'):
        raise ValueError('Invalid sysfs directory')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', attribute):
        raise ValueError('Invalid sysfs attribute')
    if not re.fullmatch(r'0[0-7]{3}', mode):
        raise ValueError('Invalid mode')
    try:
        uid, gid = identities[owner], identities[group]
    except KeyError as error:
        raise ValueError('Unknown Android identity') from error
    # Lowercase z changes existing nodes; it does not create or recurse.
    return f'z {directory}/{attribute} {mode} {uid} {gid} - -'

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--identities', type=pathlib.Path, required=True)
    parser.add_argument('--ueventd', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    header = args.identities.read_text()
    identities = {name.lower(): int(value) for name, value in re.findall(r'^#define AID_(\w+)\s+(\d+)\b', header, re.M)}
    source = args.ueventd
    output = ['# Generated from the audited Sony fusion3-common ueventd.qcom.rc.',
              '# Numeric UID/GID preserve Android identities across Ubuntu account names.',
              '# Device nodes only; sysfs adjustments are in yuga-sysfs.conf.']
    pending = []
    for line in source.read_text().splitlines():
        if line.startswith('/dev/'):
            output.append(device_rule(line, identities))
        elif line.startswith('/sys/'):
            pending.append(line)
    destination = args.output / 'usr/lib/lxc-android-config/70-yuga.rules'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('\n'.join(output) + '\n')
    sysfs_destination = args.output / 'usr/lib/tmpfiles.d/yuga-sysfs.conf'
    sysfs_destination.parent.mkdir(parents=True, exist_ok=True)
    sysfs_destination.write_text('# Sony sysfs permissions; adjust existing attributes only.\n' + '\n'.join(sysfs_rule(line, identities) for line in pending) + '\n')
    print('DEVICE_RULES', len(output)-3, 'SYSFS_ADJUSTMENTS', len(pending))
