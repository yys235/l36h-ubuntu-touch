#!/bin/bash
# Build matched ARMv7 kernel/DTB/modules. Never accesses a phone or block device.
set -euo pipefail
if [ "$#" -ne 3 ]; then
    echo 'usage: build-kernel.sh SOURCE CONFIG OUTPUT' >&2
    exit 2
fi
source_dir=$(realpath "$1")
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
config=$(realpath "$2")
mkdir -p "$3"
output=$(realpath "$3")
build="$output/build"
mkdir -p "$build"
cp "$config" "$build/.config"
export ARCH=arm LLVM=1
export KBUILD_BUILD_USER=yuga-builder KBUILD_BUILD_HOST=ci
export KBUILD_BUILD_TIMESTAMP='2026-10-20 00:00:00 +0000'
export KCONFIG_NOTIMESTAMP=1
python3 "$script_dir/adjust-source.py" "$source_dir"
python3 "$script_dir/trace-firmware.py" "$source_dir"
python3 "$script_dir/trace-touch.py" "$source_dir"
make -C "$source_dir" O="$build" olddefconfig
settings="$source_dir/scripts/config"
for option in DEVTMPFS DEVTMPFS_MOUNT CGROUPS MEMCG CGROUP_PIDS NAMESPACES \
    FHANDLE INOTIFY_USER SIGNALFD TIMERFD EPOLL UNIX SYSFS PROC_FS \
    BLK_DEV_INITRD RD_GZIP ARM_APPENDED_DTB ARM_ATAG_DTB_COMPAT \
    ARM_ATAG_DTB_COMPAT_CMDLINE_EXTEND CONFIGFS_FS USB_GADGET USB_CONFIGFS \
    USB_CONFIGFS_RNDIS USB_CONFIGFS_ECM USB_LIBCOMPOSITE USB_U_ETHER \
    USB_F_RNDIS USB_F_ECM; do
    "$settings" --file "$build/.config" --enable "$option"
done
# Keep optional hardware probes out of early boot; load after USB logging is ready.
for option in RMI4_CORE RMI4_I2C QCOM_PM8XXX_XOADC SENSORS_IIO_HWMON; do
    "$settings" --file "$build/.config" --module "$option"
done
"$settings" --file "$build/.config" --disable LOCALVERSION_AUTO
"$settings" --file "$build/.config" --set-str LOCALVERSION '-yuga-modern-probe'
make -C "$source_dir" O="$build" olddefconfig
for option in DEVTMPFS CGROUPS FHANDLE INOTIFY_USER SIGNALFD TIMERFD EPOLL \
    UNIX SYSFS PROC_FS BLK_DEV_INITRD RD_GZIP ARM_APPENDED_DTB ARM_ATAG_DTB_COMPAT \
    CONFIGFS_FS USB_GADGET USB_CONFIGFS USB_CONFIGFS_RNDIS USB_F_RNDIS; do
    if ! grep -qx "CONFIG_${option}=y" "$build/.config"; then
        echo "Required built-in kernel option not enabled: CONFIG_${option}" >&2
        exit 1
    fi
done
for option in RMI4_CORE RMI4_I2C QCOM_PM8XXX_XOADC SENSORS_IIO_HWMON; do
    if ! grep -qx "CONFIG_${option}=m" "$build/.config"; then
        echo "Diagnostic hardware driver must be modular: CONFIG_${option}" >&2
        exit 1
    fi
done
make -C "$source_dir" O="$build" -j"${BUILD_JOBS:-2}" \
    zImage qcom/qcom-apq8064-sony-xperia-lagan-yuga.dtb modules
make -C "$source_dir" O="$build" INSTALL_MOD_PATH="$output/modules" \
    INSTALL_MOD_STRIP=1 modules_install
python3 "$script_dir/verify-modules.py" --directory "$output/modules"
cp "$build/arch/arm/boot/zImage" "$output/zImage"
cp "$build/arch/arm/boot/dts/qcom/qcom-apq8064-sony-xperia-lagan-yuga.dtb" "$output/yuga.dtb"
cp "$build/.config" "$output/kernel.config"
cp "$build/include/config/kernel.release" "$output/kernel.release"
cp "$source_dir/arch/arm/boot/dts/qcom/qcom-apq8064-sony-xperia-lagan-yuga.dts" "$output/yuga.dts"
fdtget -t s "$output/yuga.dtb" / compatible | tee "$output/dtb-compatible.txt"
grep -qw 'sony,xperia-yuga' "$output/dtb-compatible.txt"
tar --sort=name --mtime='2026-10-20 00:00:00Z' --owner=0 --group=0 --numeric-owner \
    -C "$output/modules" -cJf "$output/modules.tar.xz" .
python3 - "$output" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
names = ['zImage', 'yuga.dtb', 'yuga.dts', 'kernel.config', 'kernel.release', 'dtb-compatible.txt', 'modules.tar.xz']
files = {}
for name in names:
    path = root / name
    files[name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
data = {'schema': 1, 'purpose': 'RAM diagnostic kernel, not a validated complete OS',
        'source_commit': '9e4514751f87a2f2034c6707396794a74337866c',
        'kernel_release': (root/'kernel.release').read_text().strip(), 'files': files}
(root/'build-manifest.json').write_text(json.dumps(data, indent=2)+'\n')
PY
