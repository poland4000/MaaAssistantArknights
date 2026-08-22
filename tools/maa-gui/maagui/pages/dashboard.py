"""One-click daily (一键长草): pick the routine, run everything in sequence.

Generates `__gui_daily.toml` from the currently saved settings of the
fight / daily / roguelike pages, plus a StartUp subtask.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import maa, theme
from ..runner import TaskRunner
from ..state import AppState
from ..widgets import RunBar

CLIENTS = ["Official", "Bilibili", "Txwy", "YoStarEN", "YoStarJP", "YoStarKR"]

ROUTINE_ITEMS = [
    ("startup", "启动游戏 StartUp", "Launch the game client"),
    ("fight", "刷理智 Fight", "Farm the stage configured on the Fight page"),
    ("infrast", "基建换班 Infrast", "Base shift per the Daily page settings"),
    ("recruit", "公招 Recruit", "Auto-recruitment per the Daily page settings"),
    ("mall", "商店 Mall", "Credit shop shopping per the Daily page settings"),
    ("award", "奖励 Award", "Claim daily/weekly awards per the Daily page settings"),
    ("roguelike", "肉鸽 Roguelike", "Run the Roguelike page configuration"),
]


class DashboardPage(QWidget):
    def __init__(self, runner: TaskRunner, state: AppState, fight_page,
                 daily_page, roguelike_page, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state
        self._pages = {"fight": fight_page, "daily": daily_page, "roguelike": roguelike_page}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("One-Click Daily (一键长草)")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        sub = QLabel(
            "Runs the selected routine in sequence via maa-cli. "
            "Each item uses the settings from its own page."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {theme.TEXT_DIM};")
        outer.addWidget(sub)

        # -- routine card ---------------------------------------------------
        card = QWidget()
        card.setStyleSheet(
            f"background-color: {theme.BG_ELEV}; border: 1px solid {theme.BORDER}; "
            f"border-radius: 10px;"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(8)

        self._checks: dict[str, QCheckBox] = {}
        for key, label, tip in ROUTINE_ITEMS:
            cb = QCheckBox(label)
            cb.setToolTip(tip)
            cb.setChecked(self.state.settings.value(f"routine/{key}", key != "roguelike", bool))
            cb.stateChanged.connect(lambda _, k=key: (self.state.settings.setValue(
                f"routine/{k}", self._checks[k].isChecked()), self._update_preview()))
            card_lay.addWidget(cb)
            self._checks[key] = cb

        row = QHBoxLayout()
        row.addWidget(QLabel("Game client (for StartUp):"))
        self.client = QComboBox()
        self.client.addItems(CLIENTS)
        # the profile's global resource is authoritative: YoStarEN profile
        # means an EN client, so StartUp must use that client type
        prof = maa.read_profile(self.state.profile)
        gr = (prof.get("resource") or {}).get("global_resource", "")
        if gr in CLIENTS:
            self.client.setCurrentText(gr)
        else:
            saved = self.state.settings.value("routine/client", "Official")
            if saved in CLIENTS:
                self.client.setCurrentText(saved)
        self.client.currentTextChanged.connect(
            lambda t: self.state.settings.setValue("routine/client", t)
        )
        row.addWidget(self.client)
        self.close_game = QCheckBox("Close game after (完成后关闭游戏)")
        self.close_game.setChecked(
            self.state.settings.value("routine/close_game", False, bool))
        self.close_game.toggled.connect(
            lambda on: self.state.settings.setValue("routine/close_game", on))
        row.addWidget(self.close_game)
        row.addStretch(1)
        card_lay.addLayout(row)
        outer.addWidget(card)

        # -- routine preview -----------------------------------------------------
        preview_lbl = QLabel("Routine preview (what will run):")
        preview_lbl.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
        outer.addWidget(preview_lbl)
        self.preview = QListWidget()
        self.preview.setObjectName("taskList")
        self.preview.setMaximumHeight(140)
        self.preview.setEnabled(False)
        outer.addWidget(self.preview)

        # -- quick actions ---------------------------------------------------
        quick = QHBoxLayout()
        quick.setSpacing(8)
        self._make_quick(quick, "启动游戏 Start Game", "startup")
        self._make_quick(quick, "关闭游戏 Close Game", "closedown")
        self._make_quick(quick, "更新资源 Hot-Update", "hot-update")
        self._make_quick(quick, "清理缓存 Cleanup", "cleanup")
        outer.addLayout(quick)

        # -- run controls ----------------------------------------------------
        self.bar = RunBar()
        self.bar.save_btn.setText("Save Routine")
        self.bar.run_btn.setText("Run One-Click Daily")
        self.bar.save_requested.connect(self.save)
        self.bar.run_requested.connect(self.save_and_run)
        self.bar.stop_btn.clicked.connect(self.runner.stop)
        outer.addWidget(self.bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        outer.addWidget(self.status_lbl)
        outer.addStretch(1)

        self.runner.running_changed.connect(self.bar.set_running)
        self.runner.started.connect(self._on_started)
        self.runner.finished.connect(self._on_finished)

    def _make_quick(self, layout, label: str, command: str):
        btn = QPushButton(label)
        btn.setToolTip(f"Run `maa {command}` directly")
        btn.clicked.connect(lambda _=False, c=command: self._quick_action(c))
        layout.addWidget(btn)

    def _quick_action(self, command: str):
        if self.runner.running:
            return
        if command == "hot-update":
            if not self.runner.start_command(["hot-update"], label="hot-update"):
                self.status_lbl.setText("Update already in progress.")
        elif command == "cleanup":
            if not self.runner.start_command(["cleanup", "--batch"], label="cleanup"):
                self.status_lbl.setText("Cleanup already in progress.")
        else:
            profile = self.state.profile
            client = self.client.currentText()
            if command == "startup":
                args = ["startup", client, "-p", profile, "--batch"]
            else:
                args = ["closedown", client, "-p", profile, "--batch"]
            if not self.runner.start_command(args, label=command):
                self.status_lbl.setText("A task is already running.")

    # -- routine file --------------------------------------------------------

    def build_subtasks(self) -> list[tuple[str, str, dict]]:
        subs: list[tuple[str, str, dict]] = []
        if self._checks["startup"].isChecked():
            subs.append(("Launch game", "StartUp", {
                "client_type": self.client.currentText(), "start_game_enabled": True}))
        if self._checks["fight"].isChecked():
            # always include the fight subtask — an empty stage means
            # "fight the current/last stage"
            subs.append(("Fight", "Fight", self._pages["fight"].to_task_params()))
        if self._checks["infrast"].isChecked():
            params = self._pages["daily"].infrast_params()
            if params:
                subs.append(("Infrast", "Infrast", params))
        if self._checks["recruit"].isChecked():
            params = self._pages["daily"].recruit_params()
            if params:
                subs.append(("Recruit", "Recruit", params))
        if self._checks["mall"].isChecked():
            params = self._pages["daily"].mall_params()
            if params:
                subs.append(("Mall", "Mall", params))
        if self._checks["award"].isChecked():
            params = self._pages["daily"].award_params()
            if params:
                subs.append(("Award", "Award", params))
        if self._checks["roguelike"].isChecked():
            params = self._pages["roguelike"].to_task_params()
            if params:
                subs.append(("Roguelike", "Roguelike", params))
        if self.close_game.isChecked():
            subs.append(("Close game", "CloseDown",
                         {"client_type": self.client.currentText()}))
        return subs

    def _summarize(self, subs) -> list[str]:
        """One line per subtask for the routine preview."""
        lines = []
        for name, ttype, params in subs:
            detail = ""
            if ttype == "Fight":
                detail = params.get("stage", "") or "current stage"
                if params.get("times"):
                    detail += f" ×{params['times']}"
            elif ttype == "Infrast":
                detail = f"mode {params.get('mode', 0)}"
            elif ttype == "Recruit":
                detail = f"×{params.get('times', '?')}"
            elif ttype == "Roguelike":
                detail = str(params.get("theme", ""))
            elif ttype == "StartUp":
                detail = self.client.currentText()
            elif ttype == "CloseDown":
                detail = self.client.currentText()
            lines.append(f"{ttype} — {detail}".strip())
        return lines

    def _update_preview(self):
        if not hasattr(self, "preview"):
            return  # still building the page
        self.preview.clear()
        for line in self._summarize(self.build_subtasks()):
            self.preview.addItem(QListWidgetItem(line))

    def save(self):
        subs = self.build_subtasks()
        if not subs:
            self.status_lbl.setText("Nothing selected — tick at least one item.")
            return False
        maa.write_task(maa.GUI_PREFIX + "daily", maa.task_file_text(
            subs, header="# Generated by MaaGui — One-Click Daily routine"))
        self._update_preview()
        self.status_lbl.setText(f"Saved routine ({len(subs)} tasks).")
        return True

    def save_and_run(self):
        if self.runner.running:
            return
        if self.save():
            if not self.runner.start(maa.GUI_PREFIX + "daily", self.state.profile):
                self.status_lbl.setText("Failed to start maa-cli.")

    # -- runner callbacks -----------------------------------------------------

    def _on_started(self, task: str):
        self.status_lbl.setText(f"Running: {task} — watch the Logs tab.")

    def _on_finished(self, code: int, summary: str):
        color = theme.OK if code == 0 else theme.ERR
        self.status_lbl.setStyleSheet(f"color: {color};")
        self.status_lbl.setText(summary)
