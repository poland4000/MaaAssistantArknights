"""Settings tab — the WPF SettingsView layout (left category list + panels).

Categories map the WPF sections onto maa-cli reality:
  Configuration (profiles) · Connection · Game · Performance · Update · About.
The **Game** panel hosts the fork's Linux extras: launching Arknights in an
isolated gamescope/Xvfb session, closing it, and watching its status.
"""

from __future__ import annotations

import platform
import re

from PySide6.QtCore import QRunnable, QSettings, QThreadPool, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from maagui import maa
from maagui.runner import TaskRunner
from maagui.state import AppState

from . import linuxgame, perf, theme

PRESETS = ["", "Waydroid", "Window", "MuMuPro", "PlayCover"]
TOUCH_MODES = ["ADB", "MiniTouch", "MaaTouch", "MacPlayTools"]
CLIENTS = ["", "Official", "Bilibili", "Txwy", "YoStarEN", "YoStarJP", "YoStarKR"]
GAME_MODES = [("gamescope", "Gamescope — nested window"),
              ("hidden", "Gamescope — hidden (headless)"),
              ("xvfb", "Xvfb — software fallback")]
GAME_RUNNERS = [("auto", "Auto (GE-Proton if found)"),
                ("proton", "GE-Proton (Steam prefix)"),
                ("wine", "System wine (~/.wine)")]
GAME_RESOLUTIONS = ["1280x720", "1366x768", "1600x900", "1920x1080"]


def panel_scroll(body: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    body.setObjectName("pageRoot")
    scroll.setWidget(body)
    return scroll


def field(label: str, widget, tip: str = "") -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(3)
    lab = QLabel(label)
    lab.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
    if tip:
        lab.setToolTip(tip)
        widget.setToolTip(tip)
    lay.addWidget(lab)
    lay.addWidget(widget)
    return w


def section(title: str) -> QLabel:
    lab = QLabel(title)
    lab.setStyleSheet("font-size: 15px; font-weight: 600; padding-top: 6px;")
    return lab


def combo_field(items, default_index: int = 0, editable: bool = False) -> QComboBox:
    c = QComboBox()
    c.addItems(list(items))
    c.setCurrentIndex(max(0, min(default_index, c.count() - 1)))
    c.setEditable(editable)
    return c


# ---------------------------------------------------------------------------
# panels
# ---------------------------------------------------------------------------

class ConfigurationPanel(QWidget):
    """Profile (配置) management — WPF 'Switch configuration'."""

    def __init__(self, state: AppState, on_changed, parent=None):
        super().__init__(parent)
        self.state = state
        self._on_changed = on_changed

        body = QVBoxLayout(self)
        body.setContentsMargins(4, 4, 24, 24)
        body.setSpacing(12)
        body.addWidget(section("Configuration"))

        row = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._on_profile)
        row.addWidget(self.profile_combo, 1)
        new_btn = QPushButton("New…")
        new_btn.clicked.connect(self._new_profile)
        dup_btn = QPushButton("Duplicate")
        dup_btn.clicked.connect(self._duplicate)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete)
        for b in (new_btn, dup_btn, del_btn):
            row.addWidget(b)
        body.addLayout(row)

        hint = QLabel(
            f"Profiles select the connection, client and resource settings.\n"
            f"Stored in {maa.profiles_dir()} — edits are written in place, "
            "comments preserved.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.TEXT_DIM};")
        body.addWidget(hint)
        body.addStretch(1)
        self.reload()

    def reload(self):
        maa.ensure_default_profile()
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

    def _on_profile(self, name: str):
        if name:
            self.state.set_profile(name)

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "New profile", "Profile name:")
        name = name.strip()
        if not ok or not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            return
        maa.write_profile(name, {"connection": {"preset": "", "window_name": "Arknights"}})
        self.reload()
        self.profile_combo.setCurrentText(name)

    def _duplicate(self):
        src = self.profile_combo.currentText()
        if not src:
            return
        name, ok = QInputDialog.getText(self, "Duplicate profile", f"Name for a copy of '{src}':")
        name = name.strip()
        if not ok or not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            return
        maa.duplicate_profile(src, name)
        self.reload()
        self.profile_combo.setCurrentText(name)

    def _delete(self):
        name = self.profile_combo.currentText()
        if not name:
            return
        if QMessageBox.question(
                self, "Delete profile", f"Delete profile '{name}'? This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) != QMessageBox.StandardButton.Yes:
            return
        maa.delete_profile(name)
        self.reload()


class ConnectionPanel(QWidget):
    """Connection settings (连接设置) — WPF ConnectionSettings section."""

    device_result = Signal(bool, str)

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        body = QVBoxLayout(self)
        body.setContentsMargins(4, 4, 24, 24)
        body.setSpacing(12)
        body.addWidget(section("Connection"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)

        self.preset = combo_field(PRESETS)
        grid.addWidget(field("Connection preset", self.preset,
                             "Waydroid for Android containers; Window to attach "
                             "the Linux X11 game window directly"), 0, 0)

        self.address = QLineEdit()
        self.address.setPlaceholderText("e.g. 127.0.0.1:5555 (empty = auto)")
        grid.addWidget(field("Connection address", self.address), 0, 1)

        self.adb_path = QLineEdit()
        self.adb_path.setPlaceholderText("path to adb (empty = PATH)")
        grid.addWidget(field("ADB path", self.adb_path), 1, 0)

        self.window_name = QLineEdit("Arknights")
        self.window_name.setToolTip(
            "X11 window title; prefix the X display for isolated sessions "
            "(\":1:Arknights\" — written automatically when you launch the "
            "game from the Game settings panel)")
        grid.addWidget(field("Window title", self.window_name), 1, 1)

        self.touch_mode = combo_field(TOUCH_MODES, default_index=2)
        grid.addWidget(field("Touch mode", self.touch_mode), 2, 0)

        self.client = combo_field(CLIENTS, editable=True)
        self.client.setCurrentText("YoStarEN")
        grid.addWidget(field("Client type (global resource)", self.client,
                             "YoStarEN / YoStarJP / YoStarKR for the global clients"), 2, 1)

        self.conn_config = QLineEdit()
        grid.addWidget(field("Connection config (rarely changed)", self.conn_config), 3, 0)

        self.focus_for_keys = combo_field(["false", "true"], default_index=1)
        grid.addWidget(field("Focus window for keys", self.focus_for_keys), 3, 1)

        self.deployment_pause = combo_field(["false", "true"])
        grid.addWidget(field("Deployment with pause", self.deployment_pause), 4, 0)

        self.adb_lite = combo_field(["false", "true"])
        grid.addWidget(field("ADB Lite", self.adb_lite), 4, 1)

        self.kill_adb = combo_field(["false", "true"])
        grid.addWidget(field("Kill adb on exit", self.kill_adb), 5, 0)

        self.cpu_ocr = combo_field(["true", "false"], default_index=0)
        grid.addWidget(field("CPU OCR", self.cpu_ocr), 5, 1)

        self.gpu_ocr = QLineEdit()
        self.gpu_ocr.setPlaceholderText("GPU ID, empty = CPU OCR")
        grid.addWidget(field("GPU OCR", self.gpu_ocr), 6, 0)
        body.addLayout(grid)

        btns = QHBoxLayout()
        self.status_lbl = QLabel("device status unknown")
        self.status_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        check_btn = QPushButton("Check device")
        check_btn.clicked.connect(self.check_device)
        save_btn = QPushButton("Save profile")
        save_btn.clicked.connect(self.save)
        btns.addWidget(self.status_lbl, 1)
        btns.addWidget(check_btn)
        btns.addWidget(save_btn)
        body.addLayout(btns)
        body.addStretch(1)

        self.state.profile_changed.connect(lambda _n: self.load())
        self.load()

    # ---------------------------------------------------------------- data
    def load(self):
        data = maa.read_profile(self.state.profile)
        conn = data.get("connection", {})
        res = data.get("resource", {})
        stat = data.get("static_options", {})
        inst = data.get("instance_options", {})
        self.preset.setCurrentText(str(conn.get("preset", "")))
        self.address.setText(str(conn.get("address", "")))
        self.adb_path.setText(str(conn.get("adb_path", "")))
        self.window_name.setText(str(conn.get("window_name", "Arknights")))
        self.conn_config.setText(str(conn.get("config", "")))
        self.focus_for_keys.setCurrentText(
            "true" if conn.get("focus_for_keys", False) else "false")
        touch = str(inst.get("touch_mode", "MaaTouch"))
        if touch in TOUCH_MODES:
            self.touch_mode.setCurrentText(touch)
        gr = str(res.get("global_resource", ""))
        self.client.setCurrentText(gr if gr in CLIENTS else "YoStarEN")
        self.deployment_pause.setCurrentText(
            "true" if inst.get("deployment_with_pause", False) else "false")
        self.adb_lite.setCurrentText(
            "true" if inst.get("adb_lite_enabled", False) else "false")
        self.kill_adb.setCurrentText(
            "true" if inst.get("kill_adb_on_exit", False) else "false")
        self.cpu_ocr.setCurrentText("true" if stat.get("cpu_ocr", True) else "false")
        gpu = stat.get("gpu_ocr", "")
        self.gpu_ocr.setText("" if gpu in (None, "") else str(gpu))

    def save(self):
        values: dict = {
            "connection.preset": self.preset.currentText().strip(),
            "connection.address": self.address.text().strip(),
            "connection.adb_path": self.adb_path.text().strip(),
            "connection.window_name": self.window_name.text().strip(),
            "connection.config": self.conn_config.text().strip(),
            "connection.focus_for_keys": self.focus_for_keys.currentText() == "true",
            "instance_options.touch_mode": self.touch_mode.currentText(),
            "resource.global_resource": self.client.currentText().strip(),
            "instance_options.deployment_with_pause": self.deployment_pause.currentText() == "true",
            "instance_options.adb_lite_enabled": self.adb_lite.currentText() == "true",
            "instance_options.kill_adb_on_exit": self.kill_adb.currentText() == "true",
            "static_options.cpu_ocr": self.cpu_ocr.currentText() == "true",
            "static_options.gpu_ocr": self.gpu_ocr.text().strip(),
        }
        try:
            maa.set_profile_fields(self.state.profile, values)
        except Exception as e:
            QMessageBox.critical(self, "Save profile",
                                 f"Failed to save '{self.state.profile}':\n{e}")
            return
        self.status_lbl.setText(f"saved profile '{self.state.profile}'")
        self.status_lbl.setStyleSheet(f"color: {theme.OK};")
        self.check_device()

    # ---------------------------------------------------------------- device
    def check_device(self):
        self.status_lbl.setText("checking…")
        self.status_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        worker = _DeviceCheck(
            self.preset.currentText(), self.address.text().strip(),
            self.adb_path.text().strip(), self.window_name.text().strip(),
            self._on_result)
        QThreadPool.globalInstance().start(worker)

    def _on_result(self, ok: bool, detail: str):
        self.status_lbl.setText(detail)
        self.status_lbl.setStyleSheet(f"color: {theme.OK if ok else theme.ERR};")
        self.device_result.emit(ok, detail)


class _DeviceCheck(QRunnable):
    def __init__(self, preset, address, adb, window_name, cb):
        super().__init__()
        self.args = (preset, address, adb, window_name)
        self.cb = cb

    @Slot()
    def run(self):
        ok, detail = maa.check_device(*self.args)
        self.cb(ok, detail)


class GamePanel(QWidget):
    """Linux game client — the fork extra (gamescope / Xvfb isolated launch)."""

    game_status = Signal()

    def __init__(self, state: AppState, settings: QSettings, parent=None):
        super().__init__(parent)
        self.state = state
        self.settings = settings

        body = QVBoxLayout(self)
        body.setContentsMargins(4, 4, 24, 24)
        body.setSpacing(12)
        body.addWidget(section("Game (Linux)"))
        intro = QLabel(
            "Launch the Windows Arknights client in an isolated display "
            "server (gamescope) so MAA can drive it without stealing desktop "
            "focus. The launcher writes the matching window title into the "
            "active profile.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {theme.TEXT_DIM};")
        body.addWidget(intro)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)

        self.mode = QComboBox()
        for value, label in GAME_MODES:
            self.mode.addItem(label, value)
        saved_mode = str(self.settings.value("game/mode", "gamescope"))
        idx = self.mode.findData(saved_mode)
        if idx >= 0:
            self.mode.setCurrentIndex(idx)
        self.mode.currentIndexChanged.connect(
            lambda _i: self.settings.setValue("game/mode", self.mode.currentData()))
        grid.addWidget(field("Isolation mode", self.mode,
                             "Hidden = no window on the desktop at all; Xvfb = "
                             "software rendering fallback"), 0, 0)

        self.runner_choice = QComboBox()
        for value, label in GAME_RUNNERS:
            self.runner_choice.addItem(label, value)
        saved_runner = str(self.settings.value("game/runner", "auto"))
        idx = self.runner_choice.findData(saved_runner)
        if idx >= 0:
            self.runner_choice.setCurrentIndex(idx)
        self.runner_choice.currentIndexChanged.connect(
            lambda _i: self.settings.setValue("game/runner", self.runner_choice.currentData()))
        grid.addWidget(field("Runner", self.runner_choice), 0, 1)

        self.res = combo_field(GAME_RESOLUTIONS,
                               GAME_RESOLUTIONS.index(
                                   str(self.settings.value("game/res", "1280x720")))
                               if str(self.settings.value("game/res", "1280x720"))
                               in GAME_RESOLUTIONS else 0)
        self.res.currentTextChanged.connect(
            lambda t: self.settings.setValue("game/res", t))
        grid.addWidget(field("Resolution (game + nested display)", self.res,
                             "1280x720 is MAA's native size"), 1, 0)

        self.exe = QLineEdit(str(self.settings.value("game/exe", "")))
        self.exe.setPlaceholderText("default: ~/arknights/YostarGames/Arknights_EN/Arknights.exe")
        self.exe.textChanged.connect(lambda t: self.settings.setValue("game/exe", t))
        browse = QPushButton("…")
        browse.setFixedWidth(28)
        browse.clicked.connect(self._browse_exe)
        exe_row = QHBoxLayout()
        exe_row.setContentsMargins(0, 0, 0, 0)
        exe_row.addWidget(self.exe, 1)
        exe_row.addWidget(browse)
        exe_holder = QWidget()
        exe_holder.setLayout(exe_row)
        grid.addWidget(field("Game executable (override)", exe_holder), 1, 1)
        body.addLayout(grid)

        btns = QHBoxLayout()
        self.launch_btn = QPushButton("Launch game")
        self.launch_btn.setObjectName("linkStart")
        self.launch_btn.clicked.connect(self.launch)
        self.close_btn = QPushButton("Close game")
        self.close_btn.clicked.connect(self.close_game)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        self.status_lbl.setWordWrap(True)
        btns.addWidget(self.launch_btn)
        btns.addWidget(self.close_btn)
        btns.addStretch(1)
        body.addLayout(btns)
        body.addWidget(self.status_lbl)
        body.addStretch(1)

    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select the Arknights executable", str(self.exe.text() or "~"))
        if path:
            self.exe.setText(path)

    def launch(self):
        if linuxgame.running_count() > 0:
            QMessageBox.information(self, "Game", "The game is already running.")
            return
        self.status_lbl.setText("launching isolated session…")
        self.launch_btn.setEnabled(False)
        QTimer.singleShot(10, self._do_launch)

    def _do_launch(self):
        ok, msg = linuxgame.launch(
            profile=self.state.profile,
            mode=self.mode.currentData(),
            runner=self.runner_choice.currentData(),
            res=self.res.currentText(),
            exe=self.exe.text().strip(),
        )
        self.launch_btn.setEnabled(True)
        self.status_lbl.setText(("✔ " if ok else "✗ ") + msg)
        self.status_lbl.setStyleSheet(f"color: {theme.OK if ok else theme.ERR};")
        self.game_status.emit()

    def close_game(self):
        window_name = ""
        prof = maa.read_profile(self.state.profile).get("connection", {})
        window_name = str(prof.get("window_name", ""))
        ok, msg = linuxgame.close_game(window_name)
        self.status_lbl.setText(("✔ " if ok else "✗ ") + msg)
        self.status_lbl.setStyleSheet(f"color: {theme.OK if ok else theme.ERR};")
        self.game_status.emit()


class PerformancePanel(QWidget):
    """Screencap throttling — the fork's performance knob."""

    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        body = QVBoxLayout(self)
        body.setContentsMargins(4, 4, 24, 24)
        body.setSpacing(12)
        body.addWidget(section("Performance"))
        note = QLabel(
            "MAA's battle loop polls as fast as the controller allows. The X11 "
            "window capture takes ~10 ms where ADB takes 100-500 ms, so without "
            "a throttle the loop runs at ~60 fps and burns a core. Lower = more "
            "responsive skill timing, higher = less CPU. 0 disables throttling "
            "(upstream default).")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_DIM};")
        body.addWidget(note)

        row = QHBoxLayout()
        spin = QSpinBox()
        spin.setRange(0, 1000)
        current = perf.get_interval()
        spin.setValue(current if current is not None else perf.DEFAULT_INTERVAL_MS)
        status = QLabel("")
        status.setStyleSheet(f"color: {theme.TEXT_DIM};")

        def apply():
            perf.set_interval(spin.value())
            fps = "unlimited" if spin.value() == 0 else f"~{1000 // max(spin.value(), 1)} fps"
            status.setText(f"saved — {spin.value()} ms ({fps}); applies to the next run")

        spin.valueChanged.connect(lambda _: apply())
        apply()
        row.addWidget(spin)
        row.addWidget(status, 1)
        body.addLayout(row)
        body.addStretch(1)


class UpdatePanel(QWidget):
    """Resource update + maintenance — WPF UpdateSettings-ish."""

    def __init__(self, runner: TaskRunner, parent=None):
        super().__init__(parent)
        self.runner = runner
        body = QVBoxLayout(self)
        body.setContentsMargins(4, 4, 24, 24)
        body.setSpacing(12)
        body.addWidget(section("Update & maintenance"))

        row = QHBoxLayout()
        hot = QPushButton("Hot-update resources")
        hot.clicked.connect(lambda: self._run(["hot-update"], "hot-update"))
        cleanup = QPushButton("Cleanup cache")
        cleanup.clicked.connect(lambda: self._run(["cleanup", "--batch"], "cleanup"))
        open_cfg = QPushButton("Open config dir")
        open_cfg.clicked.connect(lambda: maa.open_in_file_manager(maa.config_dir()))
        open_data = QPushButton("Open data dir")
        open_data.clicked.connect(lambda: maa.open_in_file_manager(maa.dir_data()))
        for b in (hot, cleanup, open_cfg, open_data):
            row.addWidget(b)
        row.addStretch(1)
        body.addLayout(row)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {theme.TEXT_DIM};")
        body.addWidget(self.status)
        body.addStretch(1)

    def _run(self, args, label):
        if self.runner.running:
            QMessageBox.information(self, "Busy", "A task is already running.")
            return
        if self.runner.start_command(args, label=label):
            self.status.setText(f"running: {label} — see the Farming log")
        else:
            self.status.setText("failed to start maa-cli")


class AboutPanel(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        body = QVBoxLayout(self)
        body.setContentsMargins(4, 4, 24, 24)
        body.setSpacing(12)
        body.addWidget(section("About"))

        cli, core = maa.versions()
        lines = [
            "MaaGui3 — Linux (PySide6) re-implementation of the Windows MAA UI",
            f"maa-cli: {cli or '?'}    MaaCore: {core or '?'}",
            f"Python: {platform.python_version()}    Qt (PySide6)",
            f"Profile: {state.profile}",
            "",
            "Fork extras over upstream MAA: Linux X11 window controller, "
            "gamescope isolated game sessions, PRTS copilot search with "
            "operator matching, PC performance pack.",
            "Repo: github.com/MaaAssistantArknights/MaaAssistantArknights",
        ]
        info = QLabel("\n".join(lines))
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.addWidget(info)
        body.addStretch(1)


# ---------------------------------------------------------------------------
# the settings tab
# ---------------------------------------------------------------------------

class SettingsPage(QWidget):
    device_result = Signal(bool, str)

    TABS = [
        ("config", "Configuration"),
        ("connection", "Connection"),
        ("game", "Game"),
        ("performance", "Performance"),
        ("update", "Update"),
        ("about", "About"),
    ]

    def __init__(self, runner: TaskRunner, settings: QSettings, state: AppState, parent=None):
        super().__init__(parent)
        self._tabs_by_key: dict[str, int] = {}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(18)

        cats = QListWidget()
        cats.setObjectName("settingsCats")
        cats.setFixedWidth(190)
        outer.addWidget(cats)
        self.cats = cats

        self.config_panel = ConfigurationPanel(state, on_changed=self._on_profile_changed)
        self.connection_panel = ConnectionPanel(state)
        self.connection_panel.device_result.connect(self.device_result)
        self.game_panel = GamePanel(state, settings)
        self.performance_panel = PerformancePanel(settings)
        self.update_panel = UpdatePanel(runner)
        self.about_panel = AboutPanel(state)

        self.stack = QStackedWidget()
        for panel in (self.config_panel, self.connection_panel, self.game_panel,
                      self.performance_panel, self.update_panel, self.about_panel):
            self.stack.addWidget(panel_scroll(panel))
        outer.addWidget(self.stack, 1)

        for i, (key, label) in enumerate(self.TABS):
            self.cats.addItem(label)
            self._tabs_by_key[key] = i
        self.cats.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.cats.setCurrentRow(0)

    def _on_profile_changed(self, _name: str):
        self.connection_panel.load()

    def open_tab(self, key: str):
        if key in self._tabs_by_key:
            self.cats.setCurrentRow(self._tabs_by_key[key])

    def reload_profiles(self):
        self.config_panel.reload()
