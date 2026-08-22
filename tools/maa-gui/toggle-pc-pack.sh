#!/usr/bin/env bash
# Toggle the platform_diff/pc override pack on/off.
#
# The pc pack carries PC-captured templates (main-menu entries, raid/challenge
# switch, Infrast facilities) that are required by the X11 window controller.
# They were tuned on an HDR display; on regular SDR screens the default
# (Android-tuned) templates may match better, so you can drop the pack and let
# MAA fall back to defaults.
#
# Usage:  toggle-pc-pack.sh [on|off]      (no arg = print current state)
#
# Works both from a repo checkout (resource/platform_diff/...) and from the
# self-contained bundle (MaaResource/resource/platform_diff/...). Disabling
# moves the pack aside (kept, not deleted); re-enabling restores it.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

# locate the platform_diff root: bundle layout first, then repo checkout
# (script lives in tools/maa-gui/ in the repo, at the bundle root in the zip)
REPO_ROOT="$(dirname "$(dirname "$HERE")")"
ROOT=""
for cand in \
    "$HERE/MaaResource/resource/platform_diff" \
    "$HERE/resource/platform_diff" \
    "$REPO_ROOT/resource/platform_diff"; do
    if [ -d "$cand" ]; then
        ROOT="$cand"
        break
    fi
done
if [ -z "$ROOT" ]; then
    echo "error: cannot find resource/platform_diff under $HERE" >&2
    exit 1
fi

PC="$ROOT/pc"
DISABLED="$ROOT/.pc-disabled"

if [ $# -gt 1 ]; then
    echo "usage: $0 [on|off]" >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    if [ -d "$DISABLED" ]; then
        echo "pc pack: OFF (default templates in use)"
    else
        echo "pc pack: ON (X11 window-controller templates in use)"
    fi
    exit 0
fi

case "$1" in
    on)
        if [ -d "$DISABLED" ]; then
            mv "$DISABLED" "$PC"
            echo "pc pack: ON — window-controller templates restored"
        else
            echo "pc pack: already ON"
        fi
        ;;
    off)
        if [ -d "$PC" ]; then
            mv "$PC" "$DISABLED"
            echo "pc pack: OFF — default (Android-tuned) templates are used now"
        else
            echo "pc pack: already OFF"
        fi
        ;;
    *)
        echo "usage: $0 [on|off]" >&2
        exit 1
        ;;
esac