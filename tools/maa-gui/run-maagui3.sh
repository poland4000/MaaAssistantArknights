#!/usr/bin/env bash
# Launch MaaGui3 (Linux GUI for MaaAssistantArknights via maa-cli, WPF-1:1 layout)
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found" >&2
    exit 1
fi

if ! python3 -c "import PySide6" 2>/dev/null; then
    echo "PySide6 is missing. Install it with:" >&2
    echo "  pip install --user PySide6" >&2
    exit 1
fi

if ! command -v maa >/dev/null 2>&1; then
    echo "maa-cli not found in PATH. See https://github.com/MaaAssistantArknights/maa-cli" >&2
    exit 1
fi

exec python3 -m maagui3 "$@"
