#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 4 ]]; then
    echo 'Usage: build-kernel.sh SOURCE OUTPUT GCC49_ROOT PYTHON2_BIN_DIRECTORY' >&2
    exit 2
fi
source_dir=$(realpath "$1")
output_dir=$(realpath -m "$2")
toolchain_dir=$(realpath "$3")
python_bin=$(realpath "$4")
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
test -f "$source_dir/Makefile"
test -x "$toolchain_dir/bin/arm-linux-androideabi-gcc"
test -x "$python_bin/python"
"$python_bin/python" -c 'import sys; assert sys.version_info[:3] == (2,7,18)'
"$toolchain_dir/bin/arm-linux-androideabi-gcc" -dumpversion | grep -Eq '^4\.9([.]|$)'
if [[ -e "$output_dir/.config" ]]; then
    echo 'Output already contains a config; use a new output directory.' >&2
    exit 1
fi
mkdir -p "$output_dir"
cp "$script_dir/yuga-final.config" "$output_dir/.config"
export PATH="$python_bin:$PATH"
make -C "$source_dir" O="$output_dir" ARCH=arm \
    CROSS_COMPILE="$toolchain_dir/bin/arm-linux-androideabi-" \
    CC="$toolchain_dir/bin/arm-linux-androideabi-gcc" \
    -j"${JOBS:-2}" zImage
sha256sum "$output_dir/arch/arm/boot/zImage" "$output_dir/.config"
