#!/bin/sh
# Receive one complete image from stdin; networking and mounting are separate.
set -eu
fail() { printf 'FAILED %s\n' "$1" >&2; exit 2; }
[ "$#" -eq 4 ] || fail arguments
directory=$1
name=$2
size=$3
expected=$4
case "$name" in rootfs.img|system.img) ;; *) fail filename ;; esac
case "$size" in ''|*[!0-9]*) fail size ;; esac
[ "$size" -gt 0 ] && [ "$size" -le 4294967296 ] || fail size
case "$expected" in *[!0-9a-f]*) fail hash ;; esac
[ "${#expected}" -eq 64 ] || fail hash
[ -d "$directory" ] || fail directory
directory=$(cd "$directory" && pwd -P)
target=$directory/$name
part=$target.part
[ ! -L "$target" ] && [ ! -L "$part" ] || fail symlink
[ ! -e "$target" ] || [ -f "$target" ] || fail target
[ ! -e "$part" ] || [ -f "$part" ] || fail partial
file_hash() { sha256sum "$1" | awk '{print $1}'; }
if [ -f "$target" ] && [ "$(wc -c < "$target" | tr -d ' ')" -eq "$size" ] && [ "$(file_hash "$target")" = "$expected" ]; then
    printf 'ALREADY_COMMITTED %s %s %s\n' "$name" "$size" "$expected"
    exit 0
fi
free_kib=$(df -Pk "$directory" | awk 'NR==2 {print $4}')
[ -n "$free_kib" ] && [ "$((free_kib * 1024))" -ge "$((size + 67108864))" ] || fail space
printf 'READY %s %s %s\n' "$name" "$size" "$expected"
# Read until EOF, with a one-byte overrun limit. Never count short pipe reads.
head -c "$((size + 1))" > "$part" || fail receive
actual=$(wc -c < "$part" | tr -d ' ')
[ "$actual" -eq "$size" ] || fail length
[ "$(file_hash "$part")" = "$expected" ] || fail checksum
sync
[ "$(file_hash "$part")" = "$expected" ] || fail readback
mv -f "$part" "$target"
sync
printf 'COMMITTED %s %s %s\n' "$name" "$size" "$expected"
