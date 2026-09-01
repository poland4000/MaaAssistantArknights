"""Farming tab — the WPF TaskQueueView (一键长草) layout, 1:1.

Three columns, like MAA v5.1.0:
  - left:  the bordered task checklist (checkbox + name + settings gear),
            Select All / Clear, the "Then" post-action combo, Link Start!
  - middle: settings panel of the task whose gear was selected, with a
            General/Advanced segmented toggle and "Today's open stages"
  - right: the log column (timestamp + colored content)
"""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from maagui import maa
from maagui.runner import TaskRunner

from . import theme
from .tasksettings import (
    AwardPanel,
    FightPanel,
    InfrastPanel,
    MallPanel,
    RecruitPanel,
    RoguelikePanel,
    StartUpPanel,
    TaskPanel,
)
from .wpfwidgets import LogPanel

# key, display name (WPF en-US), settings panel class
TASKS = [
    ("startup", "Login", StartUpPanel),
    ("recruit", "Auto Recruit", RecruitPanel),
    ("infrast", "Base", InfrastPanel),
    ("fight", "Combat", FightPanel),
    ("mall", "Credit Store", MallPanel),
    ("award", "Collect Rewards", AwardPanel),
    ("roguelike", "Auto I.S.", RoguelikePanel),
]

THEN_ACTIONS = ["Do Nothing", "Exit Arknights", "Exit MAA", "Shutdown"]

# resource-stage weekly rotation (mirrors MaaWpfGui StageManager)
_STAGE_SCHEDULE = {
    "CE (LMD)": {1, 3, 5, 6},
    "AP (Purchase Certificate)": {0, 3, 5, 6},
    "CA (Skill Summary)": {1, 2, 4, 6},
    "LS (Battle Record)": {0, 1, 2, 3, 4, 5, 6},
    "SK (Carbon)": {0, 2, 4, 5},
    "PR-A (Med/Def Chip)": {0, 3, 4, 6},
    "PR-B (Cst/Sni Chip)": {0, 1, 4, 5},
    "PR-C (Pio/Sup Chip)": {2, 3, 5, 6},
    "PR-D (Grd/Spc Chip)": {1, 2, 5, 6},
}


def todays_stages(now: _dt.datetime | None = None) -> list[str]:
    weekday = (now or _dt.datetime.now()).weekday()
    return [name for name, days in _STAGE_SCHEDULE.items() if weekday in days]


class TaskRow(QWidget):
    """One checklist row: checkbox + name + settings gear (WPF task item)."""

    def __init__(self, key: str, name: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("taskRow")
        self.setFixedHeight(30)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 6, 0)
        lay.setSpacing(6)
        self.check = QCheckBox(name)
        self.check.setObjectName("taskCheck")
        self.check.setStyleSheet("font-size: 12px;")
        lay.addWidget(self.check, 1)
        self.gear = QPushButton("⚙")
        self.gear.setObjectName("gear")
        self.gear.setCheckable(True)
        self.gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gear.setFixedSize(24, 24)
        self.gear.setToolTip(f"Open the {name} task settings")
        lay.addWidget(self.gear)


class FarmingPage(QWidget):
    SELECTED_TASK_KEY = "farming/selected_task"

    def __init__(self, runner: TaskRunner, settings: QSettings, state, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.settings = settings
        self.state = state

        self.panels: dict[str, TaskPanel] = {}
        self.rows: dict[str, TaskRow] = {}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(14)

        outer.addWidget(self._build_left(), 0)
        outer.addWidget(self._build_middle(), 0)
        outer.addWidget(self._build_right(), 1)

        self.runner.started.connect(self._on_started)
        self.runner.running_changed.connect(self._on_running_changed)
        self.runner.finished.connect(self._on_finished)
        self.runner.log_line.connect(self.log.append_line)

        # restore the last gear-selected task's settings panel (default: Combat)
        self._advanced = False
        saved = self.settings.value(self.SELECTED_TASK_KEY, "fight")
        self._select_task(saved if saved in self.panels else "fight")
        self._set_advanced(self.settings.value(f"{self.SELECTED_TASK_KEY}_adv", False, bool))

    # ------------------------------------------------------------------ left
    def _build_left(self) -> QWidget:
        col = QVBoxLayout()
        col.setSpacing(8)

        panel = QWidget()
        panel.setObjectName("taskPanel")
        panel.setFixedWidth(230)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(8, 8, 8, 8)
        pl.setSpacing(2)

        for key, name, panel_cls in TASKS:
            row = TaskRow(key, name)
            row.check.setChecked(self.settings.value(f"farming/enabled/{key}", True, bool))
            row.check.toggled.connect(
                lambda on, k=key: self.settings.setValue(f"farming/enabled/{k}", on))
            row.gear.clicked.connect(lambda _=False, k=key: self._select_task(k))
            self.rows[key] = row
            pl.addWidget(row)
        pl.addSpacing(6)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        select_all = QPushButton("Select All")
        select_all.clicked.connect(lambda: self._set_all(True))
        clear = QPushButton("Clear")
        clear.clicked.connect(lambda: self._set_all(False))
        btns.addWidget(select_all)
        btns.addWidget(clear)
        pl.addLayout(btns)
        col.addWidget(panel)

        then_row = QHBoxLayout()
        then_lbl = QLabel("Then")
        then_lbl.setStyleSheet(f"color: {theme.TEXT};")
        self.then = QComboBox()
        for a in THEN_ACTIONS:
            self.then.addItem(a)
        saved_then = self.settings.value("farming/then", "Do Nothing")
        if saved_then in THEN_ACTIONS:
            self.then.setCurrentText(saved_then)
        self.then.currentTextChanged.connect(
            lambda t: self.settings.setValue("farming/then", t))
        then_row.addWidget(then_lbl)
        then_row.addWidget(self.then, 1)
        col.addLayout(then_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.run_btn = QPushButton("Link Start!")
        self.run_btn.setObjectName("linkStart")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(self.link_start)
        btn_row.addWidget(self.run_btn)
        btn_row.addStretch(1)
        col.addLayout(btn_row)
        col.addStretch(1)

        holder = QWidget()
        holder.setLayout(col)
        holder.setFixedWidth(246)
        return holder

    def _set_all(self, on: bool):
        for row in self.rows.values():
            row.check.setChecked(on)

    def _select_task(self, key: str):
        self._selected = key
        self.settings.setValue(self.SELECTED_TASK_KEY, key)
        for k, row in self.rows.items():
            row.gear.setChecked(k == key)
        for k, panel in self.panels.items():
            panel.setVisible(k == key)
        self._update_adv_toggle()

    # ------------------------------------------------------------------ middle
    def _build_middle(self) -> QWidget:
        col = QVBoxLayout()
        col.setContentsMargins(0, 14, 0, 0)
        col.setSpacing(8)

        stack_holder = QWidget()
        stack_lay = QHBoxLayout(stack_holder)
        stack_lay.setContentsMargins(0, 0, 0, 0)
        for key, _name, panel_cls in TASKS:
            panel = panel_cls(self.settings)
            panel.setVisible(False)
            panel.setMinimumWidth(240)
            panel.setMaximumWidth(280)
            self.panels[key] = panel
            stack_lay.addWidget(panel)
        col.addWidget(stack_holder, 1)

        self.adv_row = QHBoxLayout()
        self.adv_row.addStretch(1)
        self.gen_btn = QPushButton("General")
        self.gen_btn.setObjectName("genToggle")
        self.gen_btn.setCheckable(True)
        self.adv_btn = QPushButton("Advanced")
        self.adv_btn.setObjectName("advToggle")
        self.adv_btn.setCheckable(True)
        self.gen_btn.clicked.connect(lambda: self._set_advanced(False))
        self.adv_btn.clicked.connect(lambda: self._set_advanced(True))
        self.adv_row.addWidget(self.gen_btn)
        self.adv_row.addWidget(self.adv_btn)
        self.adv_row.addStretch(1)
        col.addLayout(self.adv_row)

        self.stages_lbl = QLabel()
        self.stages_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        self._update_stages()
        col.addWidget(self.stages_lbl)

        holder = QWidget()
        holder.setLayout(col)
        holder.setFixedWidth(262)
        return holder

    def _set_advanced(self, advanced: bool):
        current = self._current_panel()
        if current is None or not current.HAS_ADVANCED:
            return
        self._advanced = advanced
        self.settings.setValue(f"{self.SELECTED_TASK_KEY}_adv", advanced)
        current.set_show_advanced(advanced)
        self._update_adv_toggle()

    def _update_adv_toggle(self):
        current = self._current_panel()
        has = current is not None and current.HAS_ADVANCED
        self.gen_btn.setVisible(bool(has))
        self.adv_btn.setVisible(bool(has))
        if has:
            self.gen_btn.setChecked(not self._advanced)
            self.adv_btn.setChecked(self._advanced)

    def _current_panel(self) -> TaskPanel | None:
        # visibility queries are unreliable before the window is shown, so the
        # selection is tracked explicitly
        return self.panels.get(getattr(self, "_selected", None))

    def _update_stages(self):
        self.stages_lbl.setText(
            "Today's open stages:\n" + "\n".join(todays_stages()))

    # ------------------------------------------------------------------ right
    def _build_right(self) -> QWidget:
        self.log = LogPanel()
        return self.log

    # ------------------------------------------------------------------ run
    def build_subtasks(self) -> list[tuple[str, str, dict]]:
        subs: list[tuple[str, str, dict]] = []
        client = self.panels["startup"].client.currentText()
        for key, name, _cls in TASKS:
            if not self.rows[key].check.isChecked():
                continue
            params = self.panels[key].params()
            if key == "startup":
                subs.append(("Launch game", "StartUp", params))
                continue
            if key == "roguelike" and not params:
                continue
            subs.append((name, {"recruit": "Recruit", "infrast": "Infrast",
                                "fight": "Fight", "mall": "Mall",
                                "award": "Award", "roguelike": "Roguelike"}[key], params))
        action = self.then.currentText()
        if subs and action in ("Exit Arknights", "Shutdown"):
            subs.append(("Close game", "CloseDown", {"client_type": client}))
        return subs

    def link_start(self):
        if self.runner.running:
            return
        if not any(self.rows[k].check.isChecked() for k, _n, _c in TASKS):
            self.log.append("No tasks selected — tick at least one task.", theme.WARN)
            return
        if self.then.currentText() == "Shutdown":
            ret = QMessageBox.question(
                self, "Shutdown",
                "MAA will shut the computer down after all tasks complete.\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return
        subs = self.build_subtasks()
        for panel in self.panels.values():
            panel.save()
        maa.write_task(maa.GUI_PREFIX + "daily", maa.task_file_text(
            subs, header="# Generated by MaaGui3 — Farming routine"))
        self.runner.start(maa.GUI_PREFIX + "daily", self.state.profile)

    # ------------------------------------------------------------------ runner
    def _on_started(self, task: str):
        self.log.append(f"Start task: {task}")

    def _on_running_changed(self, running: bool):
        self.run_btn.setText("Stop" if running else "Link Start!")
        # while running the button acts as Stop (WPF swaps Start for Stop)
        try:
            self.run_btn.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.run_btn.clicked.connect(self.runner.stop if running else self.link_start)

    def _on_finished(self, code: int, summary: str):
        self.log.append(
            summary,
            theme.OK if code == 0 else theme.ERR)
        action = self.then.currentText()
        if code == 0 and action == "Exit MAA":
            QApplication.instance().quit()
        elif code == 0 and action == "Shutdown":
            from PySide6.QtCore import QProcess
            QProcess.startDetached("systemctl", ["poweroff", "-i"])
