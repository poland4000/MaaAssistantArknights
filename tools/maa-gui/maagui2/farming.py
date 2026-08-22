"""Farming page (一键长草) — mirrors the Windows MAA task-card layout.

Cards with checkboxes in a grid; each card's gear button jumps to the matching
settings tab. The routine composes `__gui_daily` exactly like the old GUI.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from maagui import maa as old_maa
from maagui import theme as old_theme
from maagui.runner import TaskRunner
from maagui.state import AppState

from . import theme

CLIENTS = ["Official", "Bilibili", "Txwy", "YoStarEN", "YoStarJP", "YoStarKR"]

# key, icon, title, subtitle, settings tab to jump to
TASKS = [
    ("startup",  "🚀", "StartUp",            "Launch & login the game client",       "game"),
    ("fight",    "⚔", "Fight",              "Farm sanity on the configured stage",  "fight"),
    ("infrast",  "🏭", "Infrast shift",      "Base shifts, drones, dorms",           "infrast"),
    ("recruit",  "📋", "Auto Recruit",       "Tag refresh and recruitment slots",    "recruit"),
    ("mall",     "🛒", "Credit Mall",        "Spend credits in the store",           "mall"),
    ("award",    "🎁", "Awards",             "Claim daily / weekly rewards",         "award"),
    ("roguelike","🗺", "Roguelike",          "Integrated Strategies run",            "roguelike"),
]


class TaskCard(QWidget):
    """One routine card: checkbox + icon + title + subtitle + settings gear."""

    toggled = Signal(str, bool)   # key, checked
    settings_requested = Signal(str)  # settings tab key

    def __init__(self, key: str, icon: str, title: str, subtitle: str, tab: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.tab = tab
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(74)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 12, 10)
        lay.setSpacing(10)

        self.check = QCheckBox("")
        self.check.setChecked(True)
        lay.addWidget(self.check)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        lay.addWidget(icon_lbl)

        text = QVBoxLayout()
        text.setSpacing(2)
        text.setContentsMargins(0, 0, 0, 0)
        name = QLabel(title)
        name.setObjectName("cardTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("cardSub")
        text.addWidget(name)
        text.addWidget(sub)
        lay.addLayout(text, 1)

        gear = QPushButton("⚙")
        gear.setObjectName("gear")
        gear.setToolTip("Configure this task")
        gear.clicked.connect(lambda: self.settings_requested.emit(self.tab))
        lay.addWidget(gear)

        self.check.toggled.connect(lambda on: self.toggled.emit(self.key, on))

    def set_checked(self, on: bool):
        self.check.setChecked(on)

    def is_checked(self) -> bool:
        return self.check.isChecked()


class FarmingPage(QWidget):
    def __init__(self, runner: TaskRunner, state: AppState, fight_page, daily_page,
                 roguelike_page, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state
        self._pages = {"fight": fight_page, "daily": daily_page, "roguelike": roguelike_page}
        self._cards: dict[str, TaskCard] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("pageRoot")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 20)
        body_lay.setSpacing(16)

        title = QLabel("Farming")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        sub = QLabel("One-click daily routine — each card uses its Settings tab configuration.")
        sub.setStyleSheet(f"color: {theme.TEXT_DIM};")
        body_lay.addWidget(title)
        body_lay.addWidget(sub)

        # -- task card grid (2 columns, like the Windows MAA layout) -----------
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        for i, (key, icon, title_, sub_, tab) in enumerate(TASKS):
            card = TaskCard(key, icon, title_, sub_, tab)
            card.set_checked(self.state.settings.value(f"routine/{key}", key != "roguelike", bool))
            card.toggled.connect(self._on_toggled)
            card.settings_requested.connect(self._goto_settings)
            self._cards[key] = card
            grid.addWidget(card, i // 2, i % 2)
        body_lay.addLayout(grid)

        # -- client row ---------------------------------------------------------
        client_row = QHBoxLayout()
        client_row.setSpacing(10)
        client_row.addWidget(QLabel("Client"))
        self.client = QComboBox()
        self.client.addItems(CLIENTS)
        prof = old_maa.read_profile(self.state.profile)
        gr = (prof.get("resource") or {}).get("global_resource", "")
        if gr in CLIENTS:
            self.client.setCurrentText(gr)
        else:
            saved = self.state.settings.value("routine/client", "Official")
            if saved in CLIENTS:
                self.client.setCurrentText(saved)
        self.client.currentTextChanged.connect(
            lambda t: self.state.settings.setValue("routine/client", t))
        client_row.addWidget(self.client)

        self.close_game = QCheckBox("Close game afterwards")
        self.close_game.setChecked(self.state.settings.value("routine/close_game", False, bool))
        self.close_game.toggled.connect(
            lambda on: self.state.settings.setValue("routine/close_game", on))
        client_row.addWidget(self.close_game)
        client_row.addStretch(1)
        body_lay.addLayout(client_row)

        # -- run controls (big green 开始, Windows-MAA style) -------------------
        run_row = QHBoxLayout()
        run_row.addStretch(1)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        run_row.addWidget(self.status_lbl)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.runner.stop)
        run_row.addWidget(self.stop_btn)
        self.run_btn = QPushButton("Start")
        self.run_btn.setObjectName("runBtn")
        self.run_btn.clicked.connect(self._save_and_run)
        run_row.addWidget(self.run_btn)
        body_lay.addLayout(run_row)
        body_lay.addStretch(1)

        scroll.setWidget(body)
        outer.addWidget(scroll)

        self.runner.running_changed.connect(self._on_running)
        self.runner.started.connect(lambda t: self.status_lbl.setText(f"running: {t}"))
        self.runner.finished.connect(self._on_finished)

    # ------------------------------------------------------------------ cards

    def _on_toggled(self, key: str, on: bool):
        self.state.settings.setValue(f"routine/{key}", on)

    def _goto_settings(self, tab: str):
        # handled by the shell (needs the settings page reference)
        win = self.window()
        if hasattr(win, "open_settings_tab"):
            win.open_settings_tab(tab)

    # ------------------------------------------------------------------ run

    def build_subtasks(self) -> list[tuple[str, str, dict]]:
        subs: list[tuple[str, str, dict]] = []
        if self._cards["startup"].is_checked():
            subs.append(("Launch game", "StartUp", {
                "client_type": self.client.currentText(), "start_game_enabled": True}))
        if self._cards["fight"].is_checked():
            subs.append(("Fight", "Fight", self._pages["fight"].to_task_params()))
        if self._cards["infrast"].is_checked():
            params = self._pages["daily"].infrast_params()
            if params:
                subs.append(("Infrast", "Infrast", params))
        if self._cards["recruit"].is_checked():
            params = self._pages["daily"].recruit_params()
            if params:
                subs.append(("Recruit", "Recruit", params))
        if self._cards["mall"].is_checked():
            params = self._pages["daily"].mall_params()
            if params:
                subs.append(("Mall", "Mall", params))
        if self._cards["award"].is_checked():
            params = self._pages["daily"].award_params()
            if params:
                subs.append(("Award", "Award", params))
        if self._cards["roguelike"].is_checked():
            subs.append(("Roguelike", "Roguelike", self._pages["roguelike"].to_task_params()))
        if self.close_game.isChecked() and subs:
            subs[-1] = (
                subs[-1][0],
                subs[-1][1],
                {**subs[-1][2], "client_type": self.client.currentText()},
            )
            subs.append(("Close game", "CloseDown", {"client_type": self.client.currentText()}))
        return subs

    def save(self) -> bool:
        subs = self.build_subtasks()
        old_maa.write_task(
            old_maa.GUI_PREFIX + "daily",
            old_maa.task_file_text(subs, header="# Generated by MaaGui2 — One-click Farming"),
        )
        return True

    def _save_and_run(self):
        if self.runner.running:
            return
        self.save()
        self.runner.start(old_maa.GUI_PREFIX + "daily", self.state.profile)

    def _on_running(self, running: bool):
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def _on_finished(self, code: int, summary: str):
        self.status_lbl.setText(summary)
        self.status_lbl.setStyleSheet(
            f"color: {old_theme.OK if code == 0 else old_theme.ERR};")
