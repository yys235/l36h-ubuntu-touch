#!/usr/bin/env python3
"""Configure a credential-free Ubuntu26.10 RAM network probe staging root."""
import argparse
import pathlib
import shlex


def contained(root, relative):
    path = root/relative
    if not path.resolve().is_relative_to(root):
        raise ValueError('Configuration path escapes staging root')
    return path


def configure(root):
    root = pathlib.Path(root).resolve()
    if root == root.parent or not root.is_dir():
        raise ValueError('A staging directory is required')
    release = contained(root, 'usr/lib/os-release').read_text()
    for key, expected in [('ID', 'ubuntu'), ('VERSION_ID', '26.10')]:
        values = [shlex.split(line.split('=', 1)[1]) for line in release.splitlines()
                  if line.startswith(key+'=')]
        if values != [[expected]]:
            raise ValueError('Expected Ubuntu26.10 staging root')
    files = {
        'etc/ssh/sshd_config.d/10-yuga-probe.conf': '''Port 22
ListenAddress 0.0.0.0
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
''',
        'etc/NetworkManager/conf.d/90-yuga-probe.conf': '''[main]
dns=default
rc-manager=file

[keyfile]
unmanaged-devices=interface-name:usb0

[device]
wifi.scan-rand-mac-address=no
''',
        'etc/systemd/system/yuga-probe.target.d/20-network.conf': '''[Unit]
Wants=NetworkManager.service
After=NetworkManager.service
''',
        'etc/resolv.conf': '# NetworkManager will populate DNS after connection.\n',
    }
    destinations = [(contained(root, name), text) for name, text in files.items()]
    for path, text in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())
        path.chmod(0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=pathlib.Path)
    args = parser.parse_args()
    configure(args.root)
    print('Generic network probe configuration installed; no credentials embedded')


if __name__ == '__main__':
    main()
