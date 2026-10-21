#!/usr/bin/env python3
"""Check effective target sshd policy without assuming output keyword casing."""
import pathlib
import sys


def validate(text):
    fields = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            fields.setdefault(parts[0].casefold(), []).append(parts[1].strip())
    expected = {'port': ('22',), 'listenaddress': ('172.16.42.1:22',),
                'permitrootlogin': ('prohibit-password', 'without-password'),
                'passwordauthentication': ('no',), 'kbdinteractiveauthentication': ('no',),
                'pubkeyauthentication': ('yes',), 'authenticationmethods': ('publickey',)}
    for key, allowed in expected.items():
        values = fields.get(key, [])
        if len(values) != 1 or values[0] not in allowed:
            raise ValueError('unexpected effective SSH setting: '+key)


if __name__ == '__main__':
    try:
        validate(pathlib.Path(sys.argv[1]).read_text())
    except (OSError, ValueError, IndexError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    print('Effective ARM sshd USB/public-key-only policy verified')
