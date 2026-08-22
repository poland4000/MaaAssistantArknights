"""PC-pack performance knobs — currently the fight screencap interval.

The X11 screencap takes ~10ms where ADB takes 100-500ms, so the upstream
fight-loop intervals (16ms) never throttle and the battle loop saturates a
core. We override them via the platform_diff/pc resource pack's config.json;
this module reads/writes that override.
"""

from __future__ import annotations

import json
from pathlib import Path

INTERVAL_KEYS = (
    "SSSFightScreencapInterval",
    "RoguelikeFightScreencapInterval",
    "CopilotFightScreencapInterval",
)

DEFAULT_INTERVAL_MS = 33  # ~30 fps; upstream default is 16 (ADB-tuned)


def _resource_root() -> Path:
    from maagui import maa
    return maa.dir_data() / "MaaResource" / "resource"


def base_config_path() -> Path:
    return _resource_root() / "config.json"


def pc_config_path() -> Path:
    return _resource_root() / "platform_diff" / "pc" / "resource" / "config.json"


def get_interval() -> int | None:
    """Current fight interval from the pc pack (None if not overridden)."""
    p = pc_config_path()
    if not p.exists():
        return None
    try:
        return int(json.loads(p.read_text())["options"][INTERVAL_KEYS[0]])
    except Exception:
        return None


def set_interval(ms: int):
    """Write the fight interval into the pc-pack config override.

    Creates the override (full copy of the base config) if it doesn't exist.
    """
    ms = max(0, int(ms))
    base = json.loads(base_config_path().read_text())
    if pc_config_path().exists():
        cfg = json.loads(pc_config_path().read_text())
    else:
        cfg = base
    for key in INTERVAL_KEYS:
        cfg["options"][key] = ms
    pc_config_path().parent.mkdir(parents=True, exist_ok=True)
    pc_config_path().write_text(json.dumps(cfg, ensure_ascii=False, indent=4))
