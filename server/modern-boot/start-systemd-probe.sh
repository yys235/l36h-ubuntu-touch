#!/bin/sh
# Execute from the private USB diagnostic shell. All staging stays in RAM.
set -eu
[ "$#" -eq 4 ] || { echo 'usage: start-systemd-probe.sh ROOTFS_URL SHA256 PUBLIC_KEY_URL SHA256' >&2; exit 2; }
root_url=$1
root_sha=$2
key_url=$3
key_sha=$4
for url in "$root_url" "$key_url"; do
    case "$url" in http://172.16.42.2:8990/*) ;; *) echo 'Expected private USB host payload URL' >&2; exit 1;; esac
done
for checksum in "$root_sha" "$key_sha"; do
    [ "${#checksum}" -eq 64 ] || { echo 'Expected SHA256' >&2; exit 1; }
    case "$checksum" in *[!0-9a-f]*) echo 'Invalid SHA256' >&2; exit 1;; esac
done
[ ! -e /newroot ] || { echo 'Probe root already exists; refuse reuse' >&2; exit 1; }
wget -O /tmp/ubuntu26-probe.tar.gz "$root_url"
echo "$root_sha  /tmp/ubuntu26-probe.tar.gz" | sha256sum -c -
wget -O /run/installer-authorized-key "$key_url"
echo "$key_sha  /run/installer-authorized-key" | sha256sum -c -
mkdir /newroot
mount -t tmpfs -o size=768m,mode=0755 tmpfs /newroot
tar -xzf /tmp/ubuntu26-probe.tar.gz -C /newroot
rm /tmp/ubuntu26-probe.tar.gz
grep -qx 'VERSION_ID="26.10"' /newroot/etc/os-release
[ ! -L /newroot/root/.ssh ] || { echo 'Unexpected SSH directory symlink' >&2; exit 1; }
mkdir -p /newroot/root/.ssh /newroot/run/sshd /run/sshd
chmod 700 /newroot/root/.ssh
cp /run/installer-authorized-key /newroot/root/.ssh/authorized_keys
chmod 600 /newroot/root/.ssh/authorized_keys
chroot /newroot /usr/bin/ssh-keygen -lf /root/.ssh/authorized_keys
chroot /newroot /usr/bin/ssh-keygen -A
chroot /newroot /usr/sbin/sshd -t
[ "$(chroot /newroot /bin/readlink -f /sbin/init)" = /usr/lib/systemd/systemd ]
chroot /newroot /usr/lib/systemd/systemd --version >/run/probe-preflight-systemd.txt
touch /run/yuga-probe-ready
echo 'Validated RAM rootfs ready; diagnostic PID1 will hand off within10 seconds'
