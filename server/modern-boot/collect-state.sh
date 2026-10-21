#!/bin/sh
echo YUGA_MODERN_RAM_DIAGNOSTIC_V1
uname -a
cat /proc/uptime /proc/meminfo /proc/mounts /proc/partitions
echo INPUT
cat /proc/bus/input/devices
echo FRAMEBUFFER_AND_DRM
ls -l /sys/class/graphics /sys/class/drm
echo USB
ls -l /sys/class/udc
cat /sys/class/udc/*/state 2>/dev/null
ip addr
echo STORAGE
for path in /sys/class/block/mmcblk*; do
    echo "$path"
    cat "$path/size" "$path/uevent"
done
echo POWER_AND_TEMPERATURE
for path in /sys/class/power_supply/*/uevent /sys/class/thermal/thermal_zone*/temp; do
    [ -f "$path" ] && { echo "$path"; cat "$path"; }
done
echo INIT
cat /run/init.log
echo KERNEL_LOG
dmesg
