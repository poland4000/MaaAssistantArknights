"""Main window — the WPF RootView chrome: title, top tab bar, status bar.

Tabs mirror the WPF RootViewModel: Farming / Copilot / Toolbox / Settings.
The status bar carries the fork extras shared across tabs: device state,
run state, and the Linux game status with Launch / Close game buttons.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from maagui import maa
from maagui.runner import TaskRunner
from maagui.state import AppState

from . import linuxgame, theme
from .copilot_page import CopilotPage
from .farming_page import FarmingPage
from .settings_page import SettingsPage
from .toolbox_page import ToolboxPage
from .wpfwidgets import StatusDot


class TopTabBar(QWidget):
    """The WPF inline top tab row: evenly spread labels, blue underline."""

    changed = Signal(int)

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._buttons: list[QPushButton] = []
        for i, label in enumerate(labels):
            b = QPushButton(label)
            b.setObjectName("topTab")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setChecked(i == 0)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.clicked.connect(lambda _=False, idx=i: self.changed.emit(idx))
            lay.addWidget(b, 1)
            self._buttons.append(b)

    def set_current(self, index: int):
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
            self.changed.emit(index)


class MainWindow(QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.settings = QSettings()
        self.setWindowTitle(self._window_title())
        self.resize(1180, 740)

        self.runner = TaskRunner(self)

        # ---- pages --------------------------------------------------------
        self.farming_page = FarmingPage(self.runner, self.settings, state)
        self.copilot_page = CopilotPage(self.runner, self.settings, state)
        self.toolbox_page = ToolboxPage(self.runner, self.settings, state)
        self.settings_page = SettingsPage(self.runner, self.settings, state)

        central = QWidget()
        central.setObjectName("root")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        labels = ["Farming", "Copilot", "Toolbox", "Settings"]
        self.pages = QStackedWidget()
        self.farming_page = FarmingPage(self.runner, self.settings, state)
        self.copilot_page = CopilotPage(self.runner, self.settings, state)
        self.toolbox_page = ToolboxPage(self.runner, self.settings, state)
        self.settings_page = SettingsPage(self.runner, self.settings, state)
        for page in (self.farming_page, self.copilot_page, self.toolbox_page,
                     self.settings_page):
            self.pages.addWidget(page)

        self.tab_bar = TopTabBar(labels)
        self.tab_bar.changed.connect(self.pages.setCurrentIndex)
        root.addWidget(self.tab_bar)
        root.addWidget(self.pages, 1)

        self.setCentralWidget(central)

        # ---- status bar -----------------------------------------------------
        self._build_status_bar()

        # ---- wiring ----------------------------------------------------------
        self.runner.running_changed.connect(self._on_running_changed)
        self.runner.finished.connect(lambda *_: self._refresh_title())
        self.state.profile_changed.connect(lambda _n: self._on_profile_changed())
        self.settings_page.device_result.connect(self._on_device_result)

        self.game_dot = StatusDot()
        self.game_lbl = QLabel("game: —")
        self.status_bar.addPermanentWidget(self.game_dot)
        self.status_bar.addPermanentWidget(self.game_lbl)
        self.launch_btn = QPushButton("Launch game")
        self.launch_btn.setToolTip(
            "Launch Arknights in an isolated gamescope/Xvfb session "
            "(Game settings)")
        self.launch_btn.clicked.connect(self._quick_launch)
        self.status_bar.addPermanentWidget(self.launch_btn)
        self.close_game_btn = QPushButton("Close game")
        self.close_game_btn.clicked.connect(self._quick_close_game)
        self.status_bar.addPermanentWidget(self.close_game_btn)

        self._refresh_title()
        self.settings_page.connection_panel.check_device()
        self._refresh_game_status()

        self._game_timer = QTimer(self)
        self._game_timer.setInterval(5000)
        self._game_timer.timeout.connect(self._refresh_game_status)
        self._game_timer.start()

        self._build_tray()

    # ------------------------------------------------------------------ raise / tray
    def raise_to_front(self):
        """Bring the window out of the pile (second launch / tray click)."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _build_tray(self):
        """Tray icon — a guaranteed way to bring the window back up."""
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu, QSystemTrayIcon

        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self.windowIcon()
        tray = QSystemTrayIcon(icon, self)
        tray.setToolTip(f"MAA — {self.state.profile}")

        menu = QMenu()
        show_action = QAction("Show MAA", self)
        show_action.triggered.connect(self.raise_to_front)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self.tray = tray

    def _on_tray_activated(self, reason):
        from PySide6.QtWidgets import QSystemTrayIcon

        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.raise_to_front()

    # ------------------------------------------------------------------ title
    def _window_title(self) -> str:
        """WPF-style title: MAA (profile) - version - connection - client."""
        profile = self.state.profile
        cli, _core = maa.versions()
        data = maa.read_profile(profile)
        conn = data.get("connection", {})
        preset = str(conn.get("preset", ""))
        address = str(conn.get("address", ""))
        if preset.lower() == "window":
            name = str(conn.get("window_name", "Arknights"))
            connection = f"Window ({name})"
        elif preset and address:
            connection = f"{preset} ({address})"
        elif address:
            connection = f"ADB ({address})"
        else:
            connection = preset or "Not connected"
        resource = str((data.get("resource") or {}).get("global_resource", "")) or "Official"
        ver = (cli or "dev").lstrip("v")
        return f"MAA ({profile}) - v{ver} - {connection} - {resource}"

    def _refresh_title(self):
        self.setWindowTitle(self._window_title())

    def _on_profile_changed(self):
        self._refresh_title()
        self.settings_page.connection_panel.check_device()

    # ------------------------------------------------------------------ status bar
    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        self.device_dot = StatusDot()
        self.device_lbl = QLabel("device: —")
        self.status_bar.addWidget(self.device_dot)
        self.status_bar.addWidget(self.device_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {theme.BORDER};")
        self.status_bar.addWidget(sep)

        self.run_dot = StatusDot()
        self.run_lbl = QLabel("idle")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.runner.stop)
        self.status_bar.addPermanentWidget(self.run_dot)
        self.status_bar.addPermanentWidget(self.run_lbl)
        self.status_bar.addPermanentWidget(self.stop_btn)

    def _on_running_changed(self, running: bool):
        self.run_dot.set_ok(running if running else None)
        self.run_lbl.setText("running" if running else "idle")
        self.stop_btn.setEnabled(running)

    def _on_device_result(self, ok: bool, detail: str):
        self.device_dot.set_ok(ok)
        self.device_lbl.setText(f"device: {detail}")

    # ------------------------------------------------------------------ game extras
    def _refresh_game_status(self):
        n = linuxgame.running_count()
        if n > 0:
            self.game_dot.set_ok(True)
            self.game_lbl.setText(f"game: running ({n})")
        else:
            self.game_dot.set_ok(None)
            self.game_lbl.setText("game: not running")

    def _quick_launch(self):
        self.settings_page.open_tab("game")
        self.tab_bar.set_current(3)
        self.settings_page.game_panel.launch()

    def _quick_close_game(self):
        self.settings_page.game_panel.close_game()
        QTimer.singleShot(1500, self._refresh_game_status)

    # ------------------------------------------------------------------ teardown
    def closeEvent(self, event):
        self.toolbox_page.shutdown()
        self.runner.shutdown()
        event.accept()
