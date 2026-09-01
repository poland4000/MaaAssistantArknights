#!/usr/bin/env bash
# Run the Arknights PC client inside an isolated display server so it can
# never steal focus from the desktop compositor.
#
#   gamescope (default)  — nested microcompositor, GPU-accelerated, viewable as
#                          a normal window on the desktop. The game is a client
#                          of gamescope's own X server; its window-activation
#                          requests never reach KWin/GNOME, so synthetic MAA
#                          input cannot raise or focus it on your desktop.
#   --hidden             — same gamescope session, but with the headless
#                          backend: no window on the desktop at all (still
#                          GPU-composited, MAA still controls it). Switch
#                          visible <-> hidden by --stop + relaunching.
#   --xvfb               — virtual framebuffer (software rendering, no GPU).
#                          No window, works with no graphical session.
#
# The game runs through GE-Proton with its Steam compat prefix by default
# (auto-detected), exactly like launching it from Steam — same settings and
# login. --plain-wine uses the system wine + ~/.wine instead.
#
# The script resolves the display the game runs on and prints the exact
# `window_name` to use in your maa-cli profile (":<N>:Arknights"). With
# --profile NAME it rewrites that value in ~/.config/maa/profiles/NAME.toml.
#
# Usage: arknights-isolated.sh [options]
#   --exe PATH          game executable (default $ARKNIGHTS_EXE or
#                       ~/arknights/YostarGames/Arknights_EN/Arknights.exe)
#   --res WxH           game/nested resolution (default 1280x720 — MAA native)
#   --scale WxH         gamescope output window size (default = --res)
#   --hidden            headless gamescope: no desktop window, GPU still used
#   --no-force-fullscreen  let the WM size the window (client area may come
#                       out smaller than the nested display)
#   --xvfb              Xvfb instead of gamescope (software rendering)
#   --display N         Xvfb display number (default 79)
#   --proton NAME       GE/other Proton in Steam compatibilitytools.d
#                       (default: newest GE-Proton*)
#   --compat-data PATH  Steam compat prefix (default: auto-detect the prefix
#                       containing the Arknights registry key)
#   --plain-wine        bypass Proton: system wine + ~/.wine
#   --keep-res          don't write the Unity Screenmanager registry keys
#   --wsi-layer         keep the Gamescope WSI layer (direct scanout, few ms
#                       lower latency, HDR passthrough). Default OFF because
#                       with it on the game presents via a private protocol
#                       and MAA's window screencap sees only black pixels.
#   --profile NAME      update window_name in ~/.config/maa/profiles/NAME.toml
#   --no-wait           don't wait for the game window to appear
#   --stop              stop the running isolated instance
#   --status            show state of the running instance
#
# Note: keep the gamescope window unminimized while automating (same rule as
# the plain windowed game: a minimized game stops rendering and screencap
# fails). Being covered by other windows is fine.

set -euo pipefail

GAME_EXE="${ARKNIGHTS_EXE:-$HOME/arknights/YostarGames/Arknights_EN/Arknights.exe}"
STEAM_DIR="${STEAM_DIR:-$HOME/.local/share/Steam}"
RES="1280x720"
OUT_RES=""
MODE="gamescope"     # gamescope | xvfb
HIDDEN=0
FORCE_FULLSCREEN=1   # force the game window to exactly the nested size; the
                     # WM-managed fallback insets the client (1278x699 at
                     # 1280x720), which breaks MAA's exact-16:9 requirement
XVFB_DISPLAY=79
RUNNER="auto"        # auto | proton | wine
PROTON_NAME="${PROTON_NAME:-}"
PROTON_DIR=""
COMPAT_DATA="${COMPAT_DATA:-}"
KEEP_RES=0
WSI_LAYER=0
PROFILE=""
WAIT=1
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/maa"
STATE_FILE="$STATE_DIR/isolated-game.env"
GAME_TITLE="Arknights"

die() { echo "error: $*" >&2; exit 1; }
info() { echo "[isolated-game] $*"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --exe)      GAME_EXE="$2"; shift 2 ;;
        --res)      RES="$2"; shift 2 ;;
        --scale)    OUT_RES="$2"; shift 2 ;;
        --hidden)   HIDDEN=1; shift ;;
        --no-force-fullscreen) FORCE_FULLSCREEN=0; shift ;;
        --xvfb)     MODE="xvfb"; shift ;;
        --display)  XVFB_DISPLAY="$2"; shift 2 ;;
        --proton)   shift; RUNNER="proton"; if [[ -n "${1:-}" && "${1:-}" != -* ]]; then PROTON_NAME="$1"; shift; fi ;;
        --compat-data) COMPAT_DATA="$2"; shift 2 ;;
        --plain-wine) RUNNER="wine"; shift ;;
        --keep-res) KEEP_RES=1; shift ;;
        --wsi-layer) WSI_LAYER=1; shift ;;
        --profile)  PROFILE="$2"; shift 2 ;;
        --no-wait)  WAIT=0; shift ;;
        --stop)     MODE="stop"; shift ;;
        --status)   MODE="status"; shift ;;
        -h|--help)  grep '^#' "$0" | cut -c3-; exit 0 ;;
        *)          die "unknown option: $1" ;;
    esac
done

[[ -f "$GAME_EXE" ]] || die "game executable not found: $GAME_EXE"
[[ -d "$STEAM_DIR" ]] || die "Steam directory not found: $STEAM_DIR"
RES_W="${RES%x*}"; RES_H="${RES#*x}"
[[ "$RES_W" =~ ^[0-9]+$ && "$RES_H" =~ ^[0-9]+$ ]] || die "bad --res: $RES"

load_state() { [[ -f "$STATE_FILE" ]] && source "$STATE_FILE" || return 1; }
pid_alive() { [[ -n "${1:-}" ]] && kill -0 "$1" 2>/dev/null; }

running() {
    load_state || return 1
    pid_alive "${GAMESCOPE_PID:-}" && return 0
    pid_alive "${XVFB_PID:-}" && return 0
    return 1
}

# ---------------------------------------------------------------------------
if [[ "$MODE" == "status" ]]; then
    if running; then
        echo "mode:     $RUNNER_USED ($MODE_HINT$([ "${HIDDEN_USED:-0}" -eq 1 ] && echo ", hidden"))"
        echo "display:  $ISOLATED_DISPLAY"
        echo "game res: $GAME_RES"
        echo "profile window_name: \"$ISOLATED_DISPLAY:$GAME_TITLE\""
    else
        echo "not running"
        [[ -f "$STATE_FILE" ]] && rm -f "$STATE_FILE"
        exit 1
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
if [[ "$MODE" == "stop" ]]; then
    if ! running; then
        info "not running"
        exit 0
    fi
    info "stopping isolated instance (display $ISOLATED_DISPLAY)…"
    # wineserver is a native binary — never invoke it through wine
    if [[ -n "${WINESERVER_BIN:-}" && -x "${WINESERVER_BIN:-}" ]]; then
        WINEPREFIX="$WINEPREFIX_USED" "$WINESERVER_BIN" -k 2>/dev/null || true
    fi
    for sig in TERM KILL; do
        for p in "${GAMESCOPE_PID:-}" "${XVFB_PID:-}"; do
            pid_alive "$p" && kill -"$sig" "$p" 2>/dev/null || true
        done
        sleep 1
        pid_alive "${GAMESCOPE_PID:-}" || pid_alive "${XVFB_PID:-}" || break
    done
    rm -f "$STATE_FILE"
    info "stopped"
    exit 0
fi

# ---------------------------------------------------------------------------
# Runner selection: GE-Proton + Steam prefix (default) or plain wine
if running; then
    info "already running (display $ISOLATED_DISPLAY, state $STATE_FILE)"
    info "profile window_name: \"$ISOLATED_DISPLAY:$GAME_TITLE\""
    exit 0
fi
rm -f "$STATE_FILE"
mkdir -p "$STATE_DIR"

TOOLS_DIR="$STEAM_DIR/compatibilitytools.d"
if [[ "$RUNNER" != "wine" && -d "$TOOLS_DIR" ]]; then
    if [[ -z "$PROTON_NAME" ]]; then
        # newest GE-Proton* by version sort
        PROTON_NAME="$(ls -1 "$TOOLS_DIR" 2>/dev/null | command grep '^GE-Proton' | sort -V | tail -1 || true)"
    fi
    [[ -n "$PROTON_NAME" && -x "$TOOLS_DIR/$PROTON_NAME/proton" ]] || true
fi

if [[ "$RUNNER" == "auto" ]]; then
    if [[ -n "${PROTON_NAME:-}" && -x "$TOOLS_DIR/$PROTON_NAME/proton" ]]; then
        RUNNER="proton"
    else
        RUNNER="wine"
    fi
fi

if [[ "$RUNNER" == "proton" ]]; then
    PROTON_DIR="$TOOLS_DIR/$PROTON_NAME"
    [[ -x "$PROTON_DIR/proton" ]] || die "proton not found: $PROTON_DIR (list: $(ls "$TOOLS_DIR" 2>/dev/null | tr '\n' ' '))"
    [[ -x "$PROTON_DIR/files/bin/wine" ]] || die "proton wine missing: $PROTON_DIR/files/bin/wine"
    if [[ -z "$COMPAT_DATA" ]]; then
        # auto-detect: the Steam prefix that has the game's registry key,
        # newest first (multiple installs / leftover prefixes)
        for d in $(ls -dt "$STEAM_DIR"/steamapps/compatdata/*/ 2>/dev/null); do
            if command grep -q 'Yostar' "$d/pfx/user.reg" 2>/dev/null; then
                COMPAT_DATA="${d%/}"
                break
            fi
        done
    fi
    [[ -d "$COMPAT_DATA/pfx" ]] || die "Steam compat prefix with Arknights not found under $STEAM_DIR/steamapps/compatdata (pass --compat-data PATH)"
    WINEPREFIX_USED="$COMPAT_DATA/pfx"
    PREFIX_WINE="$PROTON_DIR/files/bin/wine"
    WINESERVER_BIN="$PROTON_DIR/files/bin/wineserver"
    info "runner: $PROTON_NAME, prefix: $COMPAT_DATA/pfx"
else
    RUNNER="wine"
    WINE="${WINE:-wine}"
    command -v "$WINE" >/dev/null 2>&1 || die "wine not found"
    WINEPREFIX_USED="${WINEPREFIX:-$HOME/.wine}"
    [[ -d "$WINEPREFIX_USED" ]] || die "wine prefix not found: $WINEPREFIX_USED"
    PREFIX_WINE="$(command -v "$WINE")"
    WINESERVER_BIN="$(command -v wineserver || true)"
    info "runner: $WINE (system), prefix: $WINEPREFIX_USED"
fi

if [[ "$MODE" == "gamescope" ]]; then
    command -v gamescope >/dev/null 2>&1 || die "gamescope not found (dnf install gamescope) — or use --xvfb"
else
    command -v Xvfb >/dev/null 2>&1 || die "Xvfb not found (dnf install xorg-x11-server-Xvfb)"
    ISOLATED_DISPLAY=":$XVFB_DISPLAY"
fi

# Unity Screenmanager keys: run as a fullscreen window at exactly the isolated
# display size, so the game fills gamescope's nested display 1:1 and MAA gets
# unscaled 1280x720 pixels.
if [[ "$KEEP_RES" -eq 0 ]]; then
    info "setting Unity Screenmanager keys ($RES fullscreen-window)"
    for kv in \
        "Screenmanager Fullscreen mode_h3630240806|1" \
        "Screenmanager Resolution Width_h182942802|$RES_W" \
        "Screenmanager Resolution Height_h2627697771|$RES_H" \
        "Screenmanager Resolution Use Native_h1405027254|0"; do
        WINEPREFIX="$WINEPREFIX_USED" "$PREFIX_WINE" reg add \
            "HKCU\Software\Yostar\Arknights_EN" \
            /v "${kv%%|*}" /t REG_DWORD /d "${kv##*|}" /f >/dev/null 2>&1 || true
    done
fi

DISP_FILE="$STATE_DIR/display"
rm -f "$DISP_FILE"

# The Gamescope WSI layer (enabled automatically under gamescope) gives direct
# scanout / HDR passthrough but presents via a private protocol, so the X
# window has no readable pixels — MAA screencap would be black. Off by default.
GAME_EXTRA_ENV=()
if [[ "$WSI_LAYER" -eq 0 ]]; then
    GAME_EXTRA_ENV+=(DISABLE_GAMESCOPE_WSI=1)
fi

info "starting game in isolated display ($MODE$([ "$HIDDEN" -eq 1 ] && echo ", hidden"), runner $RUNNER)…"
if [[ "$MODE" == "gamescope" ]]; then
    # default: visible nested window on the desktop; --hidden runs the headless
    # backend (no window, still GPU-composited and fully controllable via X11)
    if [[ "$HIDDEN" -eq 0 ]]; then
        OUT_RES="${OUT_RES:-$RES}"
    else
        OUT_RES="$RES"
    fi
    OUT_W="${OUT_RES%x*}"; OUT_H="${OUT_RES#*x}"
    GS_EXTRA_ARGS=()
    [[ "$HIDDEN" -eq 1 ]] && GS_EXTRA_ARGS+=(--backend headless)
    [[ "$FORCE_FULLSCREEN" -eq 1 ]] && GS_EXTRA_ARGS+=(--force-windows-fullscreen)

    if [[ "$RUNNER" == "proton" ]]; then
        gamescope \
            -w "$RES_W" -h "$RES_H" \
            -W "$OUT_W" -H "$OUT_H" \
            -r 60 \
            "${GS_EXTRA_ARGS[@]}" \
            -S fit -F linear \
            -- sh -c 'printf %s "$DISPLAY" > "'"$DISP_FILE"'"; exec "$@"' sh \
            env "${GAME_EXTRA_ENV[@]}" \
                STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR" \
                STEAM_COMPAT_DATA_PATH="$COMPAT_DATA" \
                SteamAppId=0 \
                "$PROTON_DIR/proton" run "$GAME_EXE" \
            >>"$STATE_DIR/gamescope.log" 2>&1 &
    else
        gamescope \
            -w "$RES_W" -h "$RES_H" \
            -W "$OUT_W" -H "$OUT_H" \
            -r 60 \
            "${GS_EXTRA_ARGS[@]}" \
            -S fit -F linear \
            -- sh -c 'printf %s "$DISPLAY" > "'"$DISP_FILE"'"; exec "$@"' sh \
            env "${GAME_EXTRA_ENV[@]}" WINEPREFIX="$WINEPREFIX_USED" "$WINE" "$GAME_EXE" \
            >>"$STATE_DIR/gamescope.log" 2>&1 &
    fi
    GAMESCOPE_PID=$!
else
    Xvfb "$ISOLATED_DISPLAY" -screen 0 "${RES_W}x${RES_H}x24" -nolisten tcp &
    XVFB_PID=$!
    if [[ "$RUNNER" == "proton" ]]; then
        env "${GAME_EXTRA_ENV[@]}" \
            STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR" \
            STEAM_COMPAT_DATA_PATH="$COMPAT_DATA" \
            SteamAppId=0 \
            "$PROTON_DIR/proton" run "$GAME_EXE" \
            >>"$STATE_DIR/proton.log" 2>&1 &
    else
        env "${GAME_EXTRA_ENV[@]}" WINEPREFIX="$WINEPREFIX_USED" "$WINE" "$GAME_EXE" \
            >>"$STATE_DIR/proton.log" 2>&1 &
    fi
    WINE_WRAPPER_PID=$!
fi

# Wait for the child to export the display number (gamescope picks the first
# free X display for its internal Xwayland; Xvfb mode is fixed but uniform).
for _ in $(seq 1 100); do
    [[ -s "$DISP_FILE" ]] && break
    sleep 0.1
done
if [[ "$MODE" == "gamescope" ]]; then
    [[ -s "$DISP_FILE" ]] || die "gamescope did not export its display (is a Wayland/X session running? see $STATE_DIR/gamescope.log)"
    ISOLATED_DISPLAY="$(cat "$DISP_FILE")"
fi

WINDOW_NAME="$ISOLATED_DISPLAY:$GAME_TITLE"

cat > "$STATE_FILE" <<EOF
MODE_HINT='$MODE'
RUNNER_USED='$RUNNER'
HIDDEN_USED='$HIDDEN'
WSI_LAYER='$WSI_LAYER'
ISOLATED_DISPLAY='$ISOLATED_DISPLAY'
GAMESCOPE_PID='${GAMESCOPE_PID:-}'
XVFB_PID='${XVFB_PID:-}'
PREFIX_WINE='$PREFIX_WINE'
WINESERVER_BIN='$WINESERVER_BIN'
WINEPREFIX_USED='$WINEPREFIX_USED'
GAME_RES='$RES'
STARTED_AT='$(date -Is)'
EOF

# Optionally rewrite window_name in a maa-cli profile so the display number
# staying in sync doesn't depend on hand-editing.
if [[ -n "$PROFILE" ]]; then
    PROFILE_FILE="$HOME/.config/maa/profiles/$PROFILE.toml"
    [[ -f "$PROFILE_FILE" ]] || die "profile not found: $PROFILE_FILE"
    if command grep -q '^window_name' "$PROFILE_FILE"; then
        sed -i "s|^window_name.*|window_name = \"$WINDOW_NAME\"|" "$PROFILE_FILE"
    else
        printf 'window_name = "%s"\n' "$WINDOW_NAME" >> "$PROFILE_FILE"
    fi
    info "updated $PROFILE_FILE: window_name = \"$WINDOW_NAME\""
fi

info "game display: $ISOLATED_DISPLAY   game res: $RES"
info "maa profile:  window_name = \"$WINDOW_NAME\""

if [[ "$WAIT" -eq 1 ]]; then
    if command -v xdotool >/dev/null 2>&1; then
        info "waiting for the game window (up to 5 min)…"
        for _ in $(seq 1 300); do
            if ! kill -0 "${GAMESCOPE_PID:-${XVFB_PID:-}}" 2>/dev/null; then
                die "display server died during startup — see $STATE_DIR/gamescope.log"
            fi
            if DISPLAY="$ISOLATED_DISPLAY" xdotool search --onlyvisible --name "^$GAME_TITLE$" >/dev/null 2>&1; then
                info "game window is up — attach MAA with window_name \"$WINDOW_NAME\""
                exit 0
            fi
            sleep 1
        done
        info "timed out waiting for the window; the game may still be loading — check manually"
    else
        info "xdotool not found; skipping window wait (game may still be loading)"
    fi
fi
