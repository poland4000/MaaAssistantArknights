"""PRTS (prts.plus) copilot search API client + roster analysis.

The site's public API lives at https://prts.maa.plus:
  GET /copilot/query  — search (levelKeyword matches *internal* stage ids,
                        e.g. main_01-07 for 1-7; prefix match for categories)
  GET /copilot/get/<id> — single copilot (same shape as query items)

Each result carries the full copilot JSON as a string in `content`, so
availability analysis (own / borrow / missing) happens locally.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

PRTS_BASE = "https://prts.maa.plus"
ORDER_BY = ["hot", "latest", "rating", "views"]

_DATA_DIR = Path(__file__).parent / "data"


class ApiError(Exception):
    pass


def _get(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "MaaGui/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except Exception as e:  # network or JSON errors
        raise ApiError(str(e)) from e
    if data.get("status_code") != 200:
        raise ApiError(data.get("message", f"status {data.get('status_code')}"))
    return data


def query(page: int = 1, limit: int = 20, level_keyword: str = "",
          operator: str = "", order_by: str = "hot", desc: bool = True) -> dict:
    """Search copilots. Returns the `data` object of the response."""
    params = {
        "page": page, "limit": limit,
        "orderBy": order_by, "desc": "true" if desc else "false",
    }
    if level_keyword:
        params["levelKeyword"] = level_keyword
    if operator:
        params["operator"] = operator
    url = PRTS_BASE + "/copilot/query?" + urllib.parse.urlencode(params)
    return _get(url)["data"]


def get_copilot(copilot_id: int) -> dict:
    return _get(f"{PRTS_BASE}/copilot/get/{copilot_id}")["data"]


# ---------------------------------------------------------------------------
# data files
# ---------------------------------------------------------------------------

def load_oper_names() -> tuple[dict, dict]:
    """(cn2en, en2cn) operator name maps, bundled from MAA battle_data.json."""
    try:
        data = json.load(open(_DATA_DIR / "oper_names.json", encoding="utf-8"))
        return data.get("cn2en", {}), data.get("en2cn", {})
    except (OSError, json.JSONDecodeError):
        return {}, {}


def load_stage_map() -> tuple[dict, dict]:
    """(code2id, id2code) stage maps from the game's stage table."""
    try:
        data = json.load(open(_DATA_DIR / "stages.json", encoding="utf-8"))
        return data.get("code2id", {}), data.get("id2code", {})
    except (OSError, json.JSONDecodeError):
        return {}, {}


def resolve_stage(text: str, code2id: dict) -> str:
    """Map what the user typed to an internal level keyword for the API.

    Display code ("TA-EX-2") -> internal id ("act49side_ex02"); anything else
    is passed through (internal ids and category prefixes work server-side).
    """
    t = text.strip()
    if not t:
        return ""
    return code2id.get(t, t)


# ---------------------------------------------------------------------------
# availability analysis
# ---------------------------------------------------------------------------

def parse_version(v: str) -> tuple[int, int, int] | None:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", v or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)) or 0


def version_ok(minimum_required: str, core_version: str) -> bool:
    need = parse_version(minimum_required)
    have = parse_version(core_version)
    if not need or not have:
        return True  # unknown requirement: assume OK
    return have >= need


def parse_content(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


#: PRTS difficulty bitmask (1 = normal, 2 = challenge, 3 = both)
DIFFICULTY_NORMAL = 1
DIFFICULTY_CHALLENGE = 2


def mode_label(copilot: dict) -> str:
    """English label for which modes a copilot covers (difficulty bitmask)."""
    content = parse_content(copilot.get("content", ""))
    try:
        d = int(content.get("difficulty", 0))
    except (TypeError, ValueError):
        d = 0
    if d & (DIFFICULTY_NORMAL | DIFFICULTY_CHALLENGE) == (DIFFICULTY_NORMAL | DIFFICULTY_CHALLENGE):
        return "Both"
    if d & DIFFICULTY_NORMAL:
        return "Normal"
    if d & DIFFICULTY_CHALLENGE:
        return "Challenge"
    return "?"


def _to_cn(name: str, cn2en: dict, en2cn: dict) -> str:
    """Best-effort normalize an operator name to its CN form."""
    if name in en2cn:
        return en2cn[name]          # EN name -> CN
    if cn2en.get(name) == name:     # already CN
        return name
    return name


def _requirement_text(req: dict) -> str:
    """Human summary of a copilot's operator requirements (elite/level only —
    skill mastery and modules are shown separately as M0–M3)."""
    parts = []
    if "elite" in req:
        parts.append(f"E{req['elite']}")
    if "level" in req:
        parts.append(f"L{req['level']}")
    return " ".join(parts) if parts else ""


def mastery_label(req: dict) -> str:
    """M0/M1/M2/M3 from a copilot requirement's skill_level (7 = M0, 8 = M1,
    9 = M2, 10 = M3). Empty string when no skill requirement is given."""
    sl = req.get("skill_level")
    if sl is None:
        return ""
    try:
        sl = int(sl)
    except (TypeError, ValueError):
        return ""
    if sl <= 7:
        return "M0"
    if sl >= 10:
        return "M3"
    return f"M{sl - 7}"


def _meets_requirements(req: dict, have: dict) -> bool:
    """Whether the owned operator's elite/level satisfy the requirements.

    Skill level and module can't be verified from the roster — they're
    informational only. Returns True when nothing is verifiable.
    """
    need_elite = req.get("elite")
    need_level = req.get("level")
    if need_elite is None and need_level is None:
        return True
    h_elite = int(have.get("elite", 0))
    h_level = int(have.get("level", 1))
    if need_elite is not None:
        if h_elite < need_elite:
            return False
        if h_elite > need_elite:
            return True  # higher promotion: level cap is higher, assume OK
    if need_level is not None and h_level < need_level:
        return False
    return True


def _dedupe_entries(entries: list) -> list:
    """Dedupe missing entries (strings and group dicts), keeping order."""
    seen = set()
    out = []
    for e in entries:
        key = e if isinstance(e, str) else ("group", e.get("group"))
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def _is_missing_group(entries: list, group_name: str) -> bool:
    return any(isinstance(e, dict) and e.get("group") == group_name
               for e in entries)


def analyze_availability(copilot: dict, roster_cn: set[str],
                         cn2en: dict | None = None, en2cn: dict | None = None,
                         roster_levels: dict | None = None) -> dict:
    """Work out whether the user can run this copilot.

    Returns a dict with owned / missing / borrow counts:
      - individual `opers` must all be owned
      - `groups` need at least one owned member (MAA picks the best)
      - `underleveled` lists owned operators whose elite/level fall short of
        the copilot's requirements (warning only — MAA still runs with a
        warning, and skill/module requirements can't be verified here)
    """
    cn2en = cn2en or {}
    en2cn = en2cn or {}
    roster_levels = roster_levels or {}
    content = parse_content(copilot.get("content", ""))
    opers = content.get("opers") or []
    groups = content.get("groups") or []

    missing: list = []  # str (operator) or {"group", "members", "reqs"} entries
    underleveled: list[dict] = []

    def check_requirements(raw_name: str, req: dict):
        cn = _to_cn(raw_name, cn2en, en2cn)
        have = roster_levels.get(cn)
        if not req or not have:
            return
        if not _meets_requirements(req, have):
            underleveled.append({
                "name": raw_name,
                "need": _requirement_text(req),
                "have": f"E{have.get('elite', 0)}L{have.get('level', 1)}",
            })

    for op in opers:
        name = (op or {}).get("name", "")
        if not name:
            continue
        if _to_cn(name, cn2en, en2cn) not in roster_cn:
            missing.append(name)
        else:
            check_requirements(name, (op or {}).get("requirements") or {})
    for grp in groups:
        members = [(m or {}).get("name", "") for m in (grp.get("opers") or [])]
        members = [m for m in members if m]
        if not members:
            continue
        owned = [m for m in members if _to_cn(m, cn2en, en2cn) in roster_cn]
        if not owned:
            missing.append({
                "group": grp.get("name", "?"),
                "members": members,
                "reqs": {m: r.get("requirements") or {} for m, r in
                         zip(members, (grp.get("opers") or []))},
            })
            continue
        # all owned members underleveled -> flag the group (MAA picks the best)
        reqs = [(m, (mm or {}).get("requirements") or {}) for m, mm in
                zip(members, (grp.get("opers") or []))]
        unmet = [(m, r) for m, r in reqs
                 if m in owned and r and not _meets_requirements(
                     r, roster_levels.get(_to_cn(m, cn2en, en2cn), {}))]
        if unmet and len(unmet) == len(owned):
            worst = max(unmet, key=lambda mr: (mr[1].get("elite", 0), mr[1].get("level", 0)))
            underleveled.append({
                "name": worst[0],
                "need": _requirement_text(worst[1]),
                "have": _roster_text(roster_levels.get(_to_cn(worst[0], cn2en, en2cn))),
            })

    missing = _dedupe_entries(missing)
    return {
        "content": content,
        "oper_count": len(opers) + len(groups),
        "missing": missing,
        "missing_count": len(missing),
        "underleveled": underleveled,
        "min_version": content.get("minimum_required", ""),
    }


def _roster_text(have: dict | None) -> str:
    if not have:
        return "?"
    return f"E{have.get('elite', 0)}L{have.get('level', 1)}"


def _fmt_name(name: str, cn2en: dict) -> str:
    en = cn2en.get(name, "")
    return f"{name} ({en})" if en else name


def _fmt_member(name: str, req: dict, cn2en: dict, warned: set[str]) -> str:
    d = _fmt_name(name, cn2en)
    m = mastery_label(req)
    if m:
        d += f" {m}"
    if name in warned:
        d += " ⚠"
    return d


def fmt_entry(entry, cn2en: dict, max_members: int = 3) -> str:
    """Render a missing/borrow entry: operator name, or group as [A | B]."""
    if isinstance(entry, str):
        return _fmt_name(entry, cn2en)
    parts = [_fmt_member(m, (entry.get("reqs") or {}).get(m, {}), cn2en, set())
             for m in entry.get("members", [])]
    if len(parts) > max_members:
        parts = parts[:max_members] + [f"+{len(parts) - max_members}"]
    return "[" + " | ".join(parts) + "]"


def format_ops_short(copilot: dict, roster_cn: set[str], cn2en: dict, en2cn: dict,
                     roster_levels: dict | None = None, max_show: int = 4) -> str:
    """One-line summary: `CN (EN) M3`, groups as `[A | B]`, ⚠ = underleveled."""
    info = analyze_availability(copilot, roster_cn, cn2en, en2cn, roster_levels)
    content = info["content"]
    warned = {w["name"] for w in info["underleveled"]}
    owned, missing = [], []
    seen = set()
    for op in content.get("opers") or []:
        name = (op or {}).get("name", "")
        if not name or name in seen:
            continue
        seen.add(name)
        d = _fmt_member(name, (op or {}).get("requirements") or {}, cn2en, warned)
        if name in info["missing"]:
            missing.append(d)
        else:
            owned.append(d)
    for grp in content.get("groups") or []:
        gname = (grp or {}).get("name", "")
        members = [(m or {}).get("name", "") for m in (grp.get("opers") or [])]
        members = [m for m in members if m]
        if not members or gname in seen:
            continue
        seen.add(gname)
        entry = {"group": gname, "members": members,
                 "reqs": {m: r.get("requirements") or {} for m, r in
                          zip(members, (grp.get("opers") or []))}}
        d = fmt_entry(entry, cn2en)
        if _is_missing_group(info["missing"], gname):
            missing.append(d)
        else:
            owned.append(d)

    parts = []
    for name in owned[:max_show]:
        parts.append(name)
    if len(owned) > max_show:
        parts.append(f"+{len(owned) - max_show}")
    if missing:
        parts.append("⚠ " + ", ".join(missing[:3]))
        if len(missing) > 3:
            parts[-1] += f" +{len(missing) - 3}"
    return " / ".join(parts) if parts else "—"
