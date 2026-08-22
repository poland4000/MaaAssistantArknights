#!/usr/bin/env bash
# Self-contained MaaLinux bundle launcher (MaaCore + maa-cli + GUI in one dir).
#
# Points maa-cli's data/config/cache dirs at the bundle so it uses the bundled
# MaaResource (which carries the platform_diff/pc pack for the X11 window
# controller), the bundled libMaaCore.so, and a dedicated writable config dir.
#
# Usage:  ./launcher.sh [maagui|maagui2]   (default: maagui2)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"

export MAA_DATA_DIR="$HERE"
export MAA_CACHE_DIR="$HERE/cache"
export MAA_CONFIG_DIR="$HERE/config"
export MAA_LOG_DIR="$HERE/log"
export LD_LIBRARY_PATH="$HERE/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$HERE:$PATH"

GUI="${1:-maagui2}"
if [ "$GUI" != "maagui" ] && [ "$GUI" != "maagui2" ]; then
    echo "unknown GUI '$GUI' (expected maagui or maagui2)" >&2
    exit 1
fi

cd "$HERE/gui"
exec python3 -m "$GUI" "${@:2}"