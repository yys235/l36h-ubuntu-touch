#!/bin/bash
# Run in disposable Linux CI, not on Windows or the phone.
set -euo pipefail
[ "$#" -eq 1 ] || { echo 'usage: build-systemd-probe.sh OUTPUT' >&2; exit 2; }
[ "$(id -u)" -eq 0 ] || { echo 'Run in disposable CI as root' >&2; exit 1; }
here=$(cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$1"
output=$(realpath "$1")
root="$output/root"
[ ! -e "$root" ] || { echo 'Refuse existing rootfs staging directory' >&2; exit 1; }
mkdir "$root" "$output/inputs"
python3 - "$here/probe-rootfs.json" "$output/inputs" <<'PY'
import json, pathlib, shutil, sys, urllib.request
metadata = json.loads(pathlib.Path(sys.argv[1]).read_text())
for item in metadata['files']:
    with urllib.request.urlopen(item['url'], timeout=180) as source, (pathlib.Path(sys.argv[2])/item['name']).open('xb') as target:
        shutil.copyfileobj(source, target)
PY
python3 "$here/verify-inputs.py" --manifest "$here/probe-rootfs.json" --directory "$output/inputs"
gpgv --status-fd 1 --keyring /usr/share/keyrings/ubuntu-archive-keyring.gpg \
    "$output/inputs/SHA256SUMS.gpg" "$output/inputs/SHA256SUMS" >"$output/base-signature.log"
grep -q 'VALIDSIG 843938DF228D22F7B3742BC0D94AA3F0EFE21092 ' "$output/base-signature.log"
tar --numeric-owner -xzf "$output/inputs/ubuntu-base-26.10-base-armhf.tar.gz" -C "$root"
cp /usr/bin/qemu-arm-static "$root/usr/bin/qemu-arm-static"
update-binfmts --enable qemu-arm
chroot "$root" /bin/true
mkdir -p "$root/proc" "$root/dev" "$root/run" "$root/etc/apt/sources.list.d"
for node in null:1:3 zero:1:5 random:1:8 urandom:1:9; do
    IFS=: read -r name major minor <<<"$node"
    [ -e "$root/dev/$name" ] || mknod -m 666 "$root/dev/$name" c "$major" "$minor"
done
cp -L /etc/resolv.conf "$root/etc/resolv.conf"
printf '#!/bin/sh\nexit 101\n' >"$root/usr/sbin/policy-rc.d"
chmod 755 "$root/usr/sbin/policy-rc.d"
cat >"$root/etc/apt/sources.list.d/ubuntu.sources" <<'EOF'
Types: deb
URIs: http://ports.ubuntu.com/ubuntu-ports
Suites: stonking stonking-updates stonking-security
Components: main universe
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
# Repository authenticity is checked by apt signatures; no trusted=yes bypass.
mount -t proc proc "$root/proc"
cleanup() { mountpoint -q "$root/proc" && umount "$root/proc" || true; }
trap cleanup EXIT
chroot "$root" /usr/bin/env DEBIAN_FRONTEND=noninteractive /bin/sh -ec '
    test "$(dpkg --print-architecture)" = armhf
    apt-get update
    apt-get install --yes --no-install-recommends systemd-sysv udev openssh-server busybox-static iproute2 ca-certificates dbus
    apt-get clean
' >"$output/packages-and-apt.log" 2>&1
chroot "$root" /usr/bin/dpkg-query -W '-f=${binary:Package}\t${Version}\t${Architecture}\n' >"$output/package-versions.tsv"
mkdir -p "$root/etc/ssh/sshd_config.d" "$root/etc/systemd/system/ssh.service.d" "$root/etc/systemd/journald.conf.d" "$root/usr/local/sbin"
cat >"$root/etc/ssh/sshd_config.d/10-yuga-probe.conf" <<'EOF'
Port 22
ListenAddress 172.16.42.1
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
EOF
cat >"$root/etc/systemd/system/ssh.service.d/10-yuga-hostkeys.conf" <<'EOF'
[Service]
ExecStartPre=
ExecStartPre=/usr/bin/ssh-keygen -A
ExecStartPre=/usr/sbin/sshd -t
EOF
printf '[Journal]\nStorage=volatile\nRuntimeMaxUse=8M\n' >"$root/etc/systemd/journald.conf.d/10-yuga-probe.conf"
install -m 644 "$here/probe/yuga-probe.target" "$root/etc/systemd/system/yuga-probe.target"
install -m 644 "$here/probe/yuga-probe-report.service" "$root/etc/systemd/system/yuga-probe-report.service"
install -m 755 "$here/probe/yuga-probe-report.sh" "$root/usr/local/sbin/yuga-probe-report.sh"
ln -sfn yuga-probe.target "$root/etc/systemd/system/default.target"
mkdir -p "$root/run/sshd"
chroot "$root" /usr/bin/ssh-keygen -q -t ed25519 -N '' -f /tmp/probe-test-host
chroot "$root" /usr/sbin/sshd -T -h /tmp/probe-test-host >"$output/arm-sshd-effective.conf"
grep -qx 'port 22' "$output/arm-sshd-effective.conf"
grep -qx 'passwordauthentication no' "$output/arm-sshd-effective.conf"
grep -qx 'authenticationmethods publickey' "$output/arm-sshd-effective.conf"
chroot "$root" /usr/lib/systemd/systemd --version >"$output/arm-systemd-version.txt"
chroot "$root" /bin/readlink -f /sbin/init >"$output/arm-init-path.txt"
grep -qx '/usr/lib/systemd/systemd' "$output/arm-init-path.txt"
# Remove all CI-generated host identity and emulator files before packaging.
find "$root/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' -delete
rm -f "$root/tmp/probe-test-host" "$root/tmp/probe-test-host.pub" "$root/usr/bin/qemu-arm-static" "$root/usr/sbin/policy-rc.d"
rm -f "$root/var/lib/systemd/random-seed"
: >"$root/etc/machine-id"
rm -f "$root/var/lib/dbus/machine-id"
ln -s /etc/machine-id "$root/var/lib/dbus/machine-id"
find "$root/var/lib/apt/lists" -type f -delete
cleanup
trap - EXIT
tar --numeric-owner -C "$root" -czf "$output/ubuntu26-systemd-probe.tar.gz" .
python3 - "$output" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1]); path = root/'ubuntu26-systemd-probe.tar.gz'
digest = hashlib.sha256()
with path.open('rb') as stream:
    while chunk := stream.read(1024*1024): digest.update(chunk)
metadata = {'schema':1, 'purpose':'ARMhf Ubuntu26.10 RAM probe; actual PID1 hardware verification pending',
            'file':path.name, 'bytes':path.stat().st_size, 'sha256':digest.hexdigest(),
            'authorized_keys':'Not embedded; validated installer public key must be supplied at runtime',
            'host_private_keys':'Not embedded; generated on the phone'}
(root/'probe-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata))
PY
