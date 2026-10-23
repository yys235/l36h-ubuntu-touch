#!/usr/bin/env python3
"""Check effective target sshd policy without assuming output keyword casing."""
import argparse
import pathlib
import sys


def validate(text, listen_address='172.16.42.1:22'):
    fields = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            fields.setdefault(parts[0].casefold(), []).append(parts[1].strip())
    expected = {'port': ('22',), 'listenaddress': (listen_address,),
                'permitrootlogin': ('prohibit-password', 'without-password'),
                'passwordauthentication': ('no',), 'kbdinteractiveauthentication': ('no',),
                'pubkeyauthentication': ('yes',), 'authenticationmethods': ('publickey',)}
    for key, allowed in expected.items():
        values = fields.get(key, [])
        if len(values) != 1 or values[0] not in allowed:
            raise ValueError('unexpected effective SSH setting: '+key)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=pathlib.Path)
    parser.add_argument('--network', action='store_true')
    args = parser.parse_args()
    try:
        validate(args.path.read_text(), '0.0.0.0:22' if args.network else '172.16.42.1:22')
    except (OSError, ValueError, IndexError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    print('Effective ARM sshd listener/public-key-only policy verified')
