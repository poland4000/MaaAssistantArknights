"""Linux game client management — the fork's "Linux launch game" extra.

Wraps `tools/isolated-game/arknights-isolated.sh`, which runs the Windows
Arknights client inside an isolated display server (gamescope by default —
visible nested window or `--hidden` headless; Xvfb as fallback) via
GE-Proton or plain wine. The script writes the real `window_name`
(`:<display>:Arknights`) straight into the maa-cli profile, so MAA attaches
to the isolated session without focus-stealing the desktop.

Status/close work without the script too: game processes are counted with
pgrep and the game window can be closed via xdotool as a last resort.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

GAME_TITLE = "Arknights"

STATE_FILE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "maa" / "isolated-game.env"


def pgrep(pattern: str, exact: bool = False) -> list[int]:
    """Return matching pids; exact matches the process name (comm) instead
    of the full command line."""
    args = ["pgrep", "-x" if exact else "-f", pattern]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return [int(p) for p in r.stdout.split() if p.strip().isdigit()]
    except (OSError, subprocess.TimeoutExpired):
        return []


# ---------------------------------------------------------------------------
# script discovery
# ---------------------------------------------------------------------------

def script_path() -> Path | None:
    """Locate arknights-isolated.sh (repo checkout or self-contained bundle)."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "isolated-game" / "arknights-isolated.sh",
        Path(__file__).resolve().parent.parent / "isolated-game" / "arknights-isolated.sh",
        Path(__file__).resolve().parent.parent.parent.parent / "tools" / "isolated-game" / "arknights-isolated.sh",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


# ---------------------------------------------------------------------------
# launch / stop
# ---------------------------------------------------------------------------

def launch(
    profile: str = "",
    mode: str = "gamescope",       # gamescope | hidden | xvfb
    runner: str = "auto",          # auto | proton | wine
    res: str = "1280x720",
    exe: str = "",
) -> tuple[bool, str]:
    """Start the game in an isolated session (non-blocking).

    Returns (ok, message). The script itself backgrounds the game and, when
    `profile` is given, rewrites the profile's `window_name` to the isolated
    display so the next MAA run attaches to it.
    """
    script = script_path()
    if script is None:
        return False, "arknights-isolated.sh not found"
    if running_count() > 0:
        return False, "game is already running"
    if not (shutil.which("gamescope") or mode == "xvfb"):
        return False, "gamescope not found (dnf install gamescope) — or use Xvfb mode"

    args = [str(script), "--res", res]
    if mode == "hidden":
        args.append("--hidden")
    elif mode == "xvfb":
        args.append("--xvfb")
    if runner == "wine":
        args.append("--plain-wine")
    elif runner == "proton":
        args.append("--proton")
    if exe:
        args += ["--exe", exe]
    if profile:
        args += ["--profile", profile, "--no-wait"]

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    except OSError as e:
        return False, str(e)

    # the launcher exits after setup (or dies with an error); give it a moment
    try:
        out, _ = proc.communicate(timeout=20 if not profile else 30)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return False, "launcher timed out:\n" + (out or "")[-800:]

    if proc.returncode != 0:
        return False, (out or f"launcher exited with {proc.returncode}").strip()[-800:]

    msg = (out or "").strip().splitlines()
    detail = next((ln for ln in reversed(msg) if "window_name" in ln or "display" in ln), "")
    return True, detail or "game launching in isolated session"


def stop_isolated() -> tuple[bool, str]:
    """Stop the isolated session via the script (wineserver + gamescope)."""
    script = script_path()
    if script is None:
        return False, "arknights-isolated.sh not found"
    try:
        r = subprocess.run(
            [str(script), "--stop"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    return r.returncode == 0, out.splitlines()[-1] if out else ("stopped" if r.returncode == 0 else "failed")


def close_game(profile: str = "") -> tuple[bool, str]:
    """Close the running game: isolated session first, then the X11 window.

    `profile` may be a raw window_name (":1:Arknights") whose display prefix
    selects the host display. Falls back to closing the X11 window via
    xdotool, and only then to killing the game process.
    """
    if STATE_FILE.is_file():
        ok, msg = stop_isolated()
        if ok:
            return True, msg

    env = dict(os.environ)
    m = re.match(r"^(?::\d+(?:\.\d+)?|[A-Za-z0-9._-]+:\d+(?:\.\d+)?):", profile or "")
    if m:
        env["DISPLAY"] = m.group(1)
    try:
        r = subprocess.run(
            ["xdotool", "search", "--name", GAME_TITLE],
            capture_output=True, text=True, timeout=10, env=env,
        )
        wins = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if wins:
            for w in wins:
                subprocess.run(
                    ["xdotool", "windowclose", w], capture_output=True, timeout=10, env=env
                )
            return True, f"closed window(s): {len(wins)}"
    except FileNotFoundError:
        pass
    except (OSError, subprocess.TimeoutExpired):
        pass

    killed = _pkill_game()
    if killed:
        return True, f"terminated game process(es): {killed}"
    return False, "no running game found"


def _pkill_game() -> int:
    """Kill Arknights.exe / wine holding the game; returns the count."""
    n = 0
    for pat in ["Arknights.exe", "-Arknights.exe"]:
        try:
            r = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, timeout=5)
            pids = [int(p) for p in r.stdout.split() if p.strip().isdigit()]
            for pid in pids:
                try:
                    os.kill(pid, 15)
                    n += 1
                except OSError:
                    pass
        except (OSError, subprocess.TimeoutExpired):
            pass
    return n


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def running_count() -> int:
    """Number of running game sessions (0 / 1, or more with multi-instance wine).

    An exact-name match hits only the real wine game process — the gamescope
    host, reaper and proton wrapper merely carry the exe path in their argv.
    While the game is still booting inside its isolated host, the state file
    marks the session as up.
    """
    n = len(pgrep("Arknights.exe", exact=True))
    if n:
        return n
    if STATE_FILE.is_file() and (pgrep("gamescope", exact=True) or pgrep("Xvfb", exact=True)):
        return 1
    return 0


def isolated_status() -> str:
    """One-line status of the isolated session, '' when not isolated."""
    try:
        r = subprocess.run(
            [str(script_path()), "--status"] if script_path() else ["false"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if r.returncode != 0:
        return ""
    return (r.stdout or "").strip().splitlines()[0] if r.stdout else ""
