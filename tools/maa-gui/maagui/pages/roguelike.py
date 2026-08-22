"""Roguelike page (肉鸽): Integrated Strategies → `__gui_roguelike`.

Squad/roles values are Chinese (MAA matches them after OCR-normalising the
English screen text); the dropdowns show English labels and write the CN value.
Strategy (mode) values and per-theme availability mirror RoguelikeMode in MaaCore.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import maa
from ..runner import TaskRunner
from ..state import AppState
from ..widgets import (
    RunBar,
    bool_field,
    combo_field,
    FieldRow,
    spin_field,
    text_field,
)

TASK_FILE = maa.GUI_PREFIX + "roguelike"

THEMES = ["Phantom", "Mizuki", "Sami", "Sarkaz", "JieGarden"]

# (value, label, allowed themes or None for all)
MODES = [
    (0, "Farm XP — play as deep as possible (aggressive encounters)", None),
    (1, "Farm Originum Ingot — invest floor 1 then exit (conservative)", None),
    (4, "Collectibles — farm starting collectibles / E2 starts (conservative)", None),
    (6, "Monthly squad — play as deep as possible", None),
    (7, "Deep investigation — play as deep as possible", None),
    (5, "Collapse paradigms — farm hidden collapsal paradigms", ["Sami"]),
    (10001, "Fast pass — quick-pass the first floor", ["Sarkaz"]),
    (20001, "Changle nodes — restart until the right floor-1 node", ["JieGarden"]),
]

# EN label -> CN value (the value MAA matches after ocrReplace)
SQUADS = [
    ("(default / random)", ""),
    ("Leader Squad", "指挥分队"),
    ("Gathering Squad", "集群分队"),
    ("Support Squad", "后勤分队"),
    ("Spearhead Squad", "矛头分队"),
    ("Tactical Assault", "突击战术分队"),
    ("Tactical Fortification", "堡垒战术分队"),
    ("Tactical Ranged", "远程战术分队"),
    ("Tactical Destruction", "破坏战术分队"),
    ("Research Squad", "研究分队"),
    ("First-Class Squad", "高规格分队"),
    ("Mind Over Matter Squad", "心胜于物分队"),
    ("Resourceful Squad", "物尽其用分队"),
    ("People-Oriented Squad", "以人为本分队"),
    ("Scientific Thinking", "科学主义分队"),
    ("Life Prioritizing Squad", "生活至上分队"),
    ("Eternal Hunting Squad", "永恒狩猎分队"),
    ("Special Training Squad", "特训分队"),
    ("Soul Escort Squad", "魂灵护送分队"),
    ("Erudite Squad", "博闻广记分队"),
    ("Blueprint Squad", "蓝图测绘分队"),
    ("Improvisation Squad", "因地制宜分队"),
    ("Ingots Squad (Sarkaz)", "点刺成锭分队"),
    ("Collection Squad", "拟态学者分队"),
    ("Mimic Squad", "异想天开分队"),
    ("Top Gun Squad", "专业人士分队"),
    ("Special Squad", "特勤分队"),
    ("High Ground Breaching Squad", "高台突破分队"),
    ("Ground Breaching Squad", "地面突破分队"),
    ("Tourist Squad", "游客分队"),
    ("Sui Regulator Squad", "司岁台分队"),
    ("Tianshi Bureau Squad", "天师府分队"),
    ("Blooming Flowers Squad", "花团锦簇分队"),
    ("Perilous Game Squad", "棋行险着分队"),
    ("Sui's Shadow Squad", "岁影回音分队"),
    ("Proxy Squad", "代理人分队"),
    ("Knowledge Squad", "知学分队"),
    ("Merchant Squad", "商贾分队"),
]

ROLES = [
    ("(default)", ""),
    ("First Move Advantage", "先手必胜"),
    ("Slow and Steady Wins", "稳扎稳打"),
    ("Overcoming Your Weaknesses", "取长补短"),
    ("Flexible Deployment", "灵活部署"),
    ("Indestructible", "坚不可摧"),
    ("As Your Heart Desires", "随心所欲"),
]


def _load_operators() -> list[str]:
    """EN names of 4★+ operators from the resource battle_data.json."""
    try:
        data = json.loads(
            Path(maa.dir_data() / "MaaResource" / "resource" / "battle_data.json").read_text()
        )
    except Exception:
        return []
    names = [
        c.get("name_en", "")
        for cid, c in data.get("chars", {}).items()
        if not cid.startswith("token_") and c.get("rarity", 0) >= 4 and c.get("name_en", "")
    ]
    return sorted(names)


class RoguelikePage(QWidget):
    def __init__(self, runner: TaskRunner, state: AppState, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Roguelike — Integrated Strategies")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        self.theme = combo_field(THEMES)
        self.theme.currentTextChanged.connect(self._refresh_modes)
        grid.addWidget(FieldRow("Theme", self.theme), 0, 0)

        self.mode = combo_field([])
        grid.addWidget(FieldRow("Strategy (mode)", self.mode), 0, 1, 1, 2)

        self.squad = combo_field([label for label, _ in SQUADS])
        grid.addWidget(FieldRow("Squad", self.squad), 0, 3)

        self.roles = combo_field([label for label, _ in ROLES])
        grid.addWidget(FieldRow("Roles group", self.roles), 1, 0)

        ops = _load_operators()
        self.core_char = combo_field(ops, editable=True)
        self.core_char.setEditable(True)
        grid.addWidget(FieldRow("Preferred operator", self.core_char), 1, 1)

        self.use_support = bool_field()
        grid.addWidget(FieldRow("Take operator as support", self.use_support), 1, 2)

        self.use_nonfriend = bool_field()
        grid.addWidget(FieldRow("Allow non-friend support", self.use_nonfriend), 1, 3)

        self.starts = spin_field(1, 0, 9999)
        grid.addWidget(FieldRow("Runs (starts_count)", self.starts), 2, 0)

        self.difficulty = spin_field(0, 0, 15)
        grid.addWidget(FieldRow("Difficulty (0 = client default)", self.difficulty), 2, 1)

        self.investment = bool_field(True)
        grid.addWidget(FieldRow("Invest at trader (投资)", self.investment), 2, 2)

        self.investments_count = spin_field(0, 0, 9999)
        grid.addWidget(FieldRow("Investment count (0 = ∞)", self.investments_count), 2, 3)

        self.stop_when_full = bool_field()
        grid.addWidget(FieldRow("Stop when investment full", self.stop_when_full), 3, 0)

        self.stop_at_max_level = spin_field(0, 0, 120)
        grid.addWidget(FieldRow("Stop at max level (0 = off)", self.stop_at_max_level), 3, 1)

        self.stop_at_final_boss = bool_field()
        grid.addWidget(FieldRow("Stop before final boss", self.stop_at_final_boss), 3, 2)

        self.refresh_trader_with_dice = bool_field()
        grid.addWidget(FieldRow("Refresh trader with dice", self.refresh_trader_with_dice), 3, 3)

        self.start_e2 = bool_field()
        grid.addWidget(FieldRow("Start with E2 (collectible mode)", self.start_e2), 4, 0)

        self.only_e2 = bool_field()
        grid.addWidget(FieldRow("Only start with E2", self.only_e2), 4, 1)

        self.collectible_shopping = bool_field()
        grid.addWidget(FieldRow("Collectible-mode shopping", self.collectible_shopping), 4, 2)

        self.collectible_squad = combo_field([label for label, _ in SQUADS])
        grid.addWidget(FieldRow("Collectible-mode squad", self.collectible_squad), 4, 3)

        outer.addLayout(grid)

        self.bar = RunBar()
        self.bar.save_requested.connect(self.save)
        self.bar.run_requested.connect(self.save_and_run)
        self.bar.stop_btn.clicked.connect(self.runner.stop)
        outer.addWidget(self.bar)
        outer.addStretch(1)

        self.runner.running_changed.connect(self.bar.set_running)
        self._refresh_modes()
        self._load()

    # -- helpers -------------------------------------------------------------

    def _refresh_modes(self):
        theme = self.theme.currentText()
        self.mode.blockSignals(True)
        self.mode.clear()
        for value, label, themes in MODES:
            if themes is None or theme in themes:
                self.mode.addItem(label, value)
        self.mode.blockSignals(False)

    def _combo_value(self, combo, table):
        idx = combo.currentIndex()
        if 0 <= idx < len(table):
            return table[idx][1]
        return ""

    def _set_combo_by_value(self, combo, table, value):
        combo.setCurrentIndex(0)
        for i, (_, v) in enumerate(table):
            if v == value:
                combo.setCurrentIndex(i)
                return

    # -- form <-> params ------------------------------------------------------

    def to_task_params(self) -> dict:
        params: dict = {"theme": self.theme.currentText()}
        params["mode"] = self.mode.currentData() if self.mode.currentData() is not None else 0
        if self.difficulty.value():
            params["difficulty"] = self.difficulty.value()
        squad = self._combo_value(self.squad, SQUADS)
        if squad:
            params["squad"] = squad
        roles = self._combo_value(self.roles, ROLES)
        if roles:
            params["roles"] = roles
        if self.core_char.currentText().strip():
            params["core_char"] = self.core_char.currentText().strip()
        params["use_support"] = self.use_support.isChecked()
        params["use_nonfriend_support"] = self.use_nonfriend.isChecked()
        params["starts_count"] = self.starts.value()
        params["investment_enabled"] = self.investment.isChecked()
        if self.investments_count.value():
            params["investments_count"] = self.investments_count.value()
        params["stop_when_investment_full"] = self.stop_when_full.isChecked()
        if self.stop_at_max_level.value():
            params["stop_at_max_level"] = self.stop_at_max_level.value()
        params["stop_at_final_boss"] = self.stop_at_final_boss.isChecked()
        params["refresh_trader_with_dice"] = self.refresh_trader_with_dice.isChecked()
        params["start_with_elite_two"] = self.start_e2.isChecked()
        params["only_start_with_elite_two"] = self.only_e2.isChecked()
        if self.mode.currentData() == 4:
            params["collectible_mode_shopping"] = self.collectible_shopping.isChecked()
            csquad = self._combo_value(self.collectible_squad, SQUADS)
            if csquad:
                params["collectible_mode_squad"] = csquad
        return params

    def _load(self):
        try:
            data = maa.read_task(TASK_FILE)
            if not data.strip():
                return
            parsed = tomllib.loads(data)
            p = (parsed.get("tasks") or [{}])[0].get("params", {})
        except Exception:
            return
        if not p:
            return
        if "theme" in p and p["theme"] in THEMES:
            self.theme.setCurrentText(str(p["theme"]))
        self._refresh_modes()
        idx = self.mode.findData(int(p.get("mode", 0)))
        if idx >= 0:
            self.mode.setCurrentIndex(idx)
        self.difficulty.setValue(int(p.get("difficulty", 0)))
        self._set_combo_by_value(self.squad, SQUADS, str(p.get("squad", "")))
        self._set_combo_by_value(self.roles, ROLES, str(p.get("roles", "")))
        self.core_char.setCurrentText(str(p.get("core_char", "")))
        self.use_support.setChecked(bool(p.get("use_support", False)))
        self.use_nonfriend.setChecked(bool(p.get("use_nonfriend_support", False)))
        self.starts.setValue(int(p.get("starts_count", 1)))
        self.investment.setChecked(bool(p.get("investment_enabled", True)))
        self.investments_count.setValue(int(p.get("investments_count", 0)))
        self.stop_when_full.setChecked(bool(p.get("stop_when_investment_full", False)))
        self.stop_at_max_level.setValue(int(p.get("stop_at_max_level", 0)))
        self.stop_at_final_boss.setChecked(bool(p.get("stop_at_final_boss", False)))
        self.refresh_trader_with_dice.setChecked(bool(p.get("refresh_trader_with_dice", False)))
        self.start_e2.setChecked(bool(p.get("start_with_elite_two", False)))
        self.only_e2.setChecked(bool(p.get("only_start_with_elite_two", False)))
        self.collectible_shopping.setChecked(bool(p.get("collectible_mode_shopping", False)))
        self._set_combo_by_value(self.collectible_squad, SQUADS, str(p.get("collectible_mode_squad", "")))

    # -- actions ---------------------------------------------------------------

    def save(self) -> bool:
        maa.write_task(TASK_FILE, maa.task_file_text(
            [("Roguelike", "Roguelike", self.to_task_params())],
            header="# Generated by MaaGui — Roguelike (Integrated Strategies)"))
        return True

    def save_and_run(self):
        if self.runner.running:
            return
        self.save()
        self.runner.start(TASK_FILE, self.state.profile)
