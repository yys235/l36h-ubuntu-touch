#!/bin/sh
# Sourced only by diagnostic PID1 after a validated RAM rootfs is ready.
handoff_probe() {
    [ "$$" -eq 1 ] || { echo 'Handoff must run as PID1'; return 1; }
    grep -q '^tmpfs /newroot tmpfs ' /proc/mounts || { echo 'Probe root is not a RAM mount'; return 1; }
    [ -s /newroot/root/.ssh/authorized_keys ] || { echo 'Installer public key missing'; return 1; }
    [ "$(chroot /newroot /bin/readlink -f /sbin/init)" = /usr/lib/systemd/systemd ] || return 1
    for name in proc sys dev run; do
        [ -d "/newroot/$name" ] || return 1
    done
    echo 'Switching real PID1 to Ubuntu26 systemd'
    ip link set lo up || return 1
    mount --move /proc /newroot/proc || return 1
    mount --move /sys /newroot/sys || return 1
    mount --move /dev /newroot/dev || return 1
    mount --move /run /newroot/run || return 1
    exec /bin/busybox switch_root /newroot /sbin/init
}
handoff_probe
