#!/bin/sh
set -eu
if [ -r /etc/hermes-server.env ]; then
    . /etc/hermes-server.env
fi
CARD=${HERMES_CARD:-/userdata/tf-card}
BASE=${HERMES_BASE:-"$CARD/hermes"}
if [ -z "${HERMES_CARD_UUID:-}" ]; then
    echo 'Set HERMES_CARD_UUID for your own ext4 card in /etc/hermes-server.env' >&2
    exit 72
fi
mountpoint -q "$CARD" || { echo 'Hermes card is not mounted' >&2; exit 72; }
EXPECTED_DEVICE=$(blkid -U "$HERMES_CARD_UUID") || exit 72
/usr/bin/python3 -c 'import os,sys; sys.exit(0 if os.stat(sys.argv[1]).st_dev == os.stat(sys.argv[2]).st_rdev else 1)' "$CARD" "$EXPECTED_DEVICE" || {
    echo 'Mounted filesystem does not match the configured card' >&2
    exit 72
}
export HOME="$BASE/home" HERMES_HOME="$BASE/home"
export TMPDIR="$BASE/tmp" PIP_CACHE_DIR="$BASE/cache" XDG_CACHE_HOME="$BASE/cache"
export LD_LIBRARY_PATH="$BASE/native/lib"
export PATH="$BASE/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HERMES_NODE="$BASE/native/node-v20.20.2-linux-armv7l/bin/node"
export HERMES_TUI_DIR="$BASE/tui"
cd "$BASE/source"
exec "$BASE/venv/bin/hermes" "$@"
