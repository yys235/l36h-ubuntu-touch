#!/bin/sh
exec >/run/yuga-probe-state.txt 2>&1
echo YUGA_UBUNTU26_SYSTEMD_PROBE
date -u
uname -a
cat /etc/os-release
echo REAL_PID1
readlink -f /proc/1/exe
cat /proc/1/comm
systemctl --version
systemctl is-system-running
systemctl --failed --no-pager
cat /proc/mounts
ip addr
ss -lntp
