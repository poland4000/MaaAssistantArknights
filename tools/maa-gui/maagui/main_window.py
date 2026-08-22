"""Main window: sidebar navigation, status bar, shared runner, tray icon."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from . import maa, theme
from .pages.connections import ConnectionsPage
from .pages.copilot import CopilotPage
from .pages.dashboard import DashboardPage
from .pages.daily import DailyPage
from .pages.fight import FightPage
from .pages.logs import LogsPage
from .pages.reclamation import ReclamationPage
from .pages.roguelike import RoguelikePage
from .pages.search import SearchPage
from .pages.taskfiles import TaskFilesPage
from .runner import TaskRunner
from .state import AppState
from .widgets import StatusDot

NAV = [
    ("一键长草 One-Click Daily", "dashboard"),
    ("刷理智 Fight", "fight"),
    ("肉鸽 Roguelike", "roguelike"),
    ("生息演算 Reclamation", "reclamation"),
    ("自动战斗 Copilot", "copilot"),
    ("作业搜索 PRTS Search", "search"),
    ("日常 Daily", "daily"),
    ("任务文件 Task Files", "taskfiles"),
    ("连接设置 Connections", "connections"),
    ("日志 Logs", "logs"),
]


class MainWindow(QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.setWindowTitle("MaaGui — MAA Linux GUI")
        self.resize(1180, 760)
        self._restore_geometry()

        self.runner = TaskRunner(self)
        self.tray = self._build_tray()

        # ---- central layout ------------------------------------------------------
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(0, 0, 0, 0)
        side_lay.setSpacing(0)

        app_title = QLabel("MaaGui")
        app_title.setObjectName("appTitle")
        app_sub = QLabel("MAA · Arknights assistant")
        app_sub.setObjectName("appSub")
        side_lay.addWidget(app_title)
        side_lay.addWidget(app_sub)

        self.nav = QListWidget()
        self.nav.setObjectName("sidebar")
        for label, _key in NAV:
            self.nav.addItem(QListWidgetItem(label))
        self.nav.currentRowChanged.connect(self._on_nav)
        side_lay.addWidget(self.nav, 1)

        self.version_label = QLabel("")
        self.version_label.setObjectName("appSub")
        side_lay.addWidget(self.version_label)
        root.addWidget(sidebar)

        # pages
        self.pages = QStackedWidget()
        self.fight_page = FightPage(self.runner, state)
        self.daily_page = DailyPage(self.runner, state)
        self.roguelike_page = RoguelikePage(self.runner, state)
        self.dashboard_page = DashboardPage(
            self.runner, state, self.fight_page, self.daily_page, self.roguelike_page)
        self.reclamation_page = ReclamationPage(self.runner, state)
        self.copilot_page = CopilotPage(self.runner, state)
        self.search_page = SearchPage(self.runner, state)
        self.search_page.add_to_queue.connect(
            lambda uri: self.copilot_page._enqueue([uri], "search"))
        self.taskfiles_page = TaskFilesPage(self.runner, state)
        self.connections_page = ConnectionsPage(state, runner=self.runner)
        self.logs_page = LogsPage(self.runner)

        for page in (
            self.dashboard_page, self.fight_page, self.roguelike_page,
            self.reclamation_page, self.copilot_page, self.search_page,
            self.daily_page, self.taskfiles_page, self.connections_page,
            self.logs_page,
        ):
            self.pages.addWidget(page)
        root.addWidget(self.pages, 1)

        self.setCentralWidget(central)
        self.nav.setCurrentRow(0)

        # ---- status bar ------------------------------------------------------------
        bar = QStatusBar()
        self.setStatusBar(bar)

        bar.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        bar.addWidget(self.profile_combo)
        bar.addWidget(QLabel("  "))

        self.device_dot = StatusDot()
        self.device_label = QLabel("device: —")
        bar.addWidget(self.device_dot)
        bar.addWidget(self.device_label)

        bar.addPermanentWidget(self._run_indicator())

        # ---- wiring -------------------------------------------------------------------
        self.runner.running_changed.connect(self._on_running_changed)
        self.runner.finished.connect(self._on_run_finished)
        self.state.profile_changed.connect(lambda _n: self._reload_profiles())

        self._reload_profiles()
        self._refresh_versions()
        self._check_device()

    # ------------------------------------------------------------------ helpers

    def _run_indicator(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.run_dot = StatusDot()
        self.run_label = QLabel("idle")
        self.run_label.setStyleSheet(f"color: {theme.TEXT_DIM};")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setFixedHeight(24)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.runner.stop)
        lay.addWidget(self.run_dot)
        lay.addWidget(self.run_label)
        lay.addWidget(self.stop_btn)
        return w

    def _build_tray(self) -> QSystemTrayIcon | None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        tray = QSystemTrayIcon(self)
        tray.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        tray.setToolTip("MaaGui")
        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_from_tray)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        return tray

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray() if self.isHidden() else self.hide()

    # ------------------------------------------------------------------ nav

    def _on_nav(self, row: int):
        if 0 <= row < self.pages.count():
            self.pages.setCurrentIndex(row)

    # ------------------------------------------------------------------ state

    def _reload_profiles(self):
        names = maa.list_profiles()
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
        cli, core = maa.versions()
        self.version_label.setText(f"maa-cli {cli}\nMaaCore {core}" if cli else "")

    def _check_device(self):
        profile = maa.read_profile(self.state.profile)
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
                ok, detail = maa.check_device(self.preset_, self.address_, self.adb_)
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
            f"color: {theme.TEXT if running else theme.TEXT_DIM};")

    def _on_run_finished(self, code: int, summary: str):
        if self.tray and (self.isHidden() or not self.isActiveWindow()):
            self.tray.showMessage(
                "MaaGui",
                summary,
                QSystemTrayIcon.MessageIcon.Information if code == 0
                else QSystemTrayIcon.MessageIcon.Warning,
                5000)

    # ------------------------------------------------------------------ geometry

    def _restore_geometry(self):
        geo = self.state.settings.value("window/geometry")
        if isinstance(geo, str) and "x" in geo:
            try:
                w, h = geo.split("x")
                self.resize(int(w), int(h))
            except ValueError:
                pass

    def closeEvent(self, event):
        self.state.settings.setValue("window/geometry", f"{self.width()}x{self.height()}")
        # synchronous teardown so no child processes / threads outlive the app
        self.search_page.shutdown()
        self.runner.shutdown()
        self.logs_page.shutdown()
        event.accept()
