"""Main window for MaaGui2 — Windows-MAA style shell.

Left icon rail + header (title / version / profile) + stacked pages.
Pages are imported from the original `maagui` package so both GUIs share
one source of truth for task logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

# make the original maagui package importable
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from maagui import maa as old_maa
from maagui import theme as old_theme
from maagui.runner import TaskRunner
from maagui.state import AppState
from maagui.widgets import StatusDot
# original pages (reused, not duplicated)
from maagui.pages.connections import ConnectionsPage
from maagui.pages.copilot import CopilotPage
from maagui.pages.logs import LogsPage
from maagui.pages.reclamation import ReclamationPage
from maagui.pages.search import SearchPage
from maagui.pages.taskfiles import TaskFilesPage
from maagui.pages.fight import FightPage
from maagui.pages.daily import DailyPage
from maagui.pages.roguelike import RoguelikePage

from . import theme
from .farming import FarmingPage
from .settings_page import SettingsPage

NAV = [
    ("🌱", "Farming", "farming"),
    ("⚔", "Fight / Copilot", "copilot"),
    ("🔎", "PRTS Search", "search"),
    ("🏕", "Reclamation", "reclamation"),
    ("📄", "Task Files", "taskfiles"),
    ("⚙", "Settings", "settings"),
    ("📋", "Logs", "logs"),
]


class MainWindow(QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.setWindowTitle("MAA — MaaGui2")
        self.resize(1100, 720)

        self.runner = TaskRunner(self)

        # ---- pages (original classes, new shell) -----------------------------
        self.fight_page = FightPage(self.runner, state)
        self.daily_page = DailyPage(self.runner, state)
        self.roguelike_page = RoguelikePage(self.runner, state)
        self.farming_page = FarmingPage(
            self.runner, state, self.fight_page, self.daily_page, self.roguelike_page)
        self.copilot_page = CopilotPage(self.runner, state)
        self.search_page = SearchPage(self.runner, state)
        self.search_page.add_to_queue.connect(
            lambda uri: self.copilot_page._enqueue([uri], "search"))
        self.reclamation_page = ReclamationPage(self.runner, state)
        self.taskfiles_page = TaskFilesPage(self.runner, state)
        self.connections_page = ConnectionsPage(state, runner=self.runner)
        self.logs_page = LogsPage(self.runner)
        self.settings_page = SettingsPage(
            self.connections_page, self.fight_page, self.daily_page, self.roguelike_page)

        # ---- central layout ---------------------------------------------------
        central = QWidget()
        central.setObjectName("root")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_rail())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._build_header())

        self.pages = QStackedWidget()
        for key in ("farming", "copilot", "search", "reclamation", "taskfiles", "settings", "logs"):
            page = {
                "farming": self.farming_page,
                "copilot": self.copilot_page,
                "search": self.search_page,
                "reclamation": self.reclamation_page,
                "taskfiles": self.taskfiles_page,
                "settings": self.settings_page,
                "logs": self.logs_page,
            }[key]
            self.pages.addWidget(page)
        right.addWidget(self.pages, 1)
        root.addLayout(right, 1)

        self.setCentralWidget(central)
        self._nav_buttons["farming"].setChecked(True)
        self.pages.setCurrentIndex(0)

        # ---- status bar ---------------------------------------------------------
        bar = QStatusBar()
        self.setStatusBar(bar)
        self.device_dot = StatusDot()
        self.device_label = QLabel("device: —")
        bar.addWidget(self.device_dot)
        bar.addWidget(self.device_label)
        self.run_dot = StatusDot()
        self.run_label = QLabel("idle")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.runner.stop)
        bar.addPermanentWidget(self.run_dot)
        bar.addPermanentWidget(self.run_label)
        bar.addPermanentWidget(self.stop_btn)

        self.runner.running_changed.connect(self._on_running_changed)
        self.runner.finished.connect(self._on_run_finished)
        self.state.profile_changed.connect(lambda _n: self._check_device())
        self._refresh_versions()
        self._check_device()

    # ------------------------------------------------------------------ chrome

    def _build_rail(self) -> QWidget:
        rail = QWidget()
        rail.setObjectName("rail")
        rail.setFixedWidth(72)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(8, 14, 8, 14)
        lay.setSpacing(6)

        logo = QLabel("MAA")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff; padding: 6px;")
        lay.addWidget(logo)

        self._nav_buttons: dict[str, QToolButton] = {}
        for icon, label, key in NAV:
            btn = QToolButton()
            btn.setObjectName("nav")
            btn.setText(icon)
            btn.setToolTip(label)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda _=False, k=key: self._goto(k))
            lay.addWidget(btn)
            self._nav_buttons[key] = btn
        lay.addStretch(1)
        return rail

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(64)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 8, 20, 8)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title = QLabel("MaaAssistantArknights")
        title.setObjectName("appTitle")
        sub = QLabel("Linux · maa-cli backend · MaaGui2")
        sub.setObjectName("appSub")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        lay.addLayout(title_col)
        lay.addStretch(1)

        self.version_label = QLabel("")
        self.version_label.setStyleSheet(f"color: {theme.TEXT_DIM};")
        lay.addWidget(self.version_label)

        lay.addWidget(QLabel("Profile"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        lay.addWidget(self.profile_combo)
        return header

    # ------------------------------------------------------------------ nav

    def _goto(self, key: str):
        idx = [k for _, _, k in NAV].index(key)
        self.pages.setCurrentIndex(idx)
        self._nav_buttons[key].setChecked(True)

    def open_settings_tab(self, tab: str):
        self.settings_page.open_tab(tab)
        self._goto("settings")

    # ------------------------------------------------------------------ state

    def reload_profiles(self):
        names = old_maa.list_profiles()
        current = self.state.profile
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(names)
        if current in names:
            self.profile_combo.setCurrentText(current)
        elif names:
            self.profile_combo.setCurrentText(names[0])
        self.profile_combo.blockSignals(False)
        if names:
            self.state.set_profile(self.profile_combo.currentText())

    def _on_profile_changed(self, name: str):
        if name:
            self.state.set_profile(name)
            self._check_device()

    def _refresh_versions(self):
        cli, core = old_maa.versions()
        self.version_label.setText(f"maa-cli {cli} · MaaCore {core}" if cli else "")

    def _check_device(self):
        profile = old_maa.read_profile(self.state.profile)
        conn = profile.get("connection", {})
        preset = str(conn.get("preset", ""))
        address = str(conn.get("address", ""))
        adb = str(conn.get("adb_path", ""))
        self.device_dot.set_ok(None)
        self.device_label.setText("checking…")

        from PySide6.QtCore import QRunnable, QThreadPool, Slot

        class _Check(QRunnable):
            def __init__(self, preset_, address_, adb_, cb):
                super().__init__()
                self.preset_, self.address_, self.adb_, self.cb = preset_, address_, adb_, cb

            @Slot()
            def run(self):
                ok, detail = old_maa.check_device(self.preset_, self.address_, self.adb_)
                self.cb(ok, detail)

        QThreadPool.globalInstance().start(
            _Check(preset, address, adb, self._on_device_result))

    def _on_device_result(self, ok: bool, detail: str):
        self.device_dot.set_ok(ok)
        self.device_label.setText(f"device: {detail}")

    def _on_running_changed(self, running: bool):
        self.run_dot.set_ok(running)
        self.stop_btn.setEnabled(running)
        self.run_label.setText("running" if running else "idle")
        self.run_label.setStyleSheet(
            f"color: {old_theme.TEXT if running else old_theme.TEXT_DIM};")

    def _on_run_finished(self, code: int, summary: str):
        self.run_label.setText("idle")

    # ------------------------------------------------------------------ teardown

    def closeEvent(self, event):
        self.search_page.shutdown()
        self.runner.shutdown()
        self.logs_page.shutdown()
        event.accept()
