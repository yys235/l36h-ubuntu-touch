#!/bin/sh
# Xperia Z SMD transport; BlueZ owns power and discovery policy.
set -eu
le=/sys/module/bluetooth/parameters/enable_le
smd=/sys/module/hci_smd/parameters/hcismd_set
test -w "$le" && test -w "$smd"
printf Y > "$le"
if [ ! -d /sys/class/bluetooth/hci0 ]; then
    printf 1 > "$smd"
fi
count=0
while [ ! -d /sys/class/bluetooth/hci0 ]; do
    count=$((count + 1))
    if [ "$count" -ge 30 ]; then
        echo 'Yuga Bluetooth controller did not appear' >&2
        exit 1
    fi
    sleep 1
done
echo 'Yuga SMD controller available; BLE enabled'
