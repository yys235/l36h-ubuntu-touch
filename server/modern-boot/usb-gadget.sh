#!/bin/sh
set -eu
grep -q ' /sys/kernel/config configfs ' /proc/mounts || mount -t configfs configfs /sys/kernel/config
g=/sys/kernel/config/usb_gadget/yuga
if [ -d "$g" ]; then
    [ -n "$(cat "$g/UDC")" ] && exit 0
    echo 'Incomplete gadget already exists; refuse a second partial configuration' >&2
    exit 1
fi
mkdir "$g"
echo 0x18d1 >"$g/idVendor"
echo 0xd001 >"$g/idProduct"
echo 0x0200 >"$g/bcdUSB"
echo 0x0100 >"$g/bcdDevice"
echo 0xef >"$g/bDeviceClass"
echo 0x02 >"$g/bDeviceSubClass"
echo 0x01 >"$g/bDeviceProtocol"
mkdir "$g/strings/0x409"
echo yuga-modern-diag >"$g/strings/0x409/serialnumber"
echo Yuga >"$g/strings/0x409/manufacturer"
echo 'Yuga RAM diagnostic' >"$g/strings/0x409/product"
mkdir "$g/configs/c.1" "$g/configs/c.1/strings/0x409"
echo 'USB private diagnostic' >"$g/configs/c.1/strings/0x409/configuration"
echo 250 >"$g/configs/c.1/MaxPower"
mkdir "$g/functions/rndis.usb0"
echo 02:00:00:00:42:01 >"$g/functions/rndis.usb0/dev_addr"
echo 02:00:00:00:42:02 >"$g/functions/rndis.usb0/host_addr"
echo RNDIS >"$g/functions/rndis.usb0/os_desc/interface.rndis/compatible_id"
echo 5162001 >"$g/functions/rndis.usb0/os_desc/interface.rndis/sub_compatible_id"
echo MSFT100 >"$g/os_desc/qw_sign"
echo 0xcd >"$g/os_desc/b_vendor_code"
echo 1 >"$g/os_desc/use"
ln -s "$g/configs/c.1" "$g/os_desc/c.1"
ln -s "$g/functions/rndis.usb0" "$g/configs/c.1/rndis.usb0"
count=0
while :; do
    udc=$(ls /sys/class/udc | head -n 1)
    [ -n "$udc" ] && break
    count=$((count + 1))
    [ "$count" -lt 30 ] || { echo 'No UDC after 30 seconds' >&2; exit 1; }
    sleep 1
done
echo "$udc" >"$g/UDC"
ip link set usb0 up
ip addr replace 172.16.42.1/30 dev usb0
cat >/run/udhcpd.conf <<'EOF'
start 172.16.42.2
end 172.16.42.2
interface usb0
max_leases 1
lease_file /run/udhcpd.leases
pidfile /run/udhcpd.pid
option subnet 255.255.255.252
option lease 600
EOF
touch /run/udhcpd.leases
udhcpd /run/udhcpd.conf
