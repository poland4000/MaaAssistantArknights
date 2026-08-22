"""Connections page (连接设置): device status, profile manager, maa tools."""

from __future__ import annotations

import re

from PySide6.QtCore import QRunnable, QThreadPool, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import maa, theme
from ..state import AppState
from ..widgets import (
    combo_field,
    FieldRow,
    StatusDot,
    text_field,
)

PRESETS = ["", "MuMuPro", "PlayCover", "Waydroid", "Window"]
TOUCH_MODES = ["ADB", "MiniTouch", "MaaTouch", "MacPlayTools"]
RESOURCE_GLOBALS = ["", "YoStarEN", "YoStarJP", "YoStarKR"]


class _DeviceCheck(QRunnable):
    def __init__(self, preset: str, address: str, adb_path: str, window_name: str, result_cb):
        super().__init__()
        self.preset = preset
        self.address = address
        self.adb_path = adb_path
        self.window_name = window_name
        self.result_cb = result_cb

    @Slot()
    def run(self):
        ok, detail = maa.check_device(self.preset, self.address, self.adb_path, self.window_name)
        self.result_cb(ok, detail)


class ConnectionsPage(QWidget):
    def __init__(self, state: AppState, runner=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.runner = runner
        self._pool = QThreadPool(self)
        self._profiles: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Connections & Profiles — 连接设置")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        # ---- profile selector -------------------------------------------------
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self._on_profile_switched)
        sel_row.addWidget(self.profile_combo, 1)
        self.new_btn = QPushButton("New…")
        self.new_btn.clicked.connect(self._new_profile)
        self.dup_btn = QPushButton("Duplicate")
        self.dup_btn.clicked.connect(self._duplicate_profile)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._delete_profile)
        sel_row.addWidget(self.new_btn)
        sel_row.addWidget(self.dup_btn)
        sel_row.addWidget(self.del_btn)
        outer.addLayout(sel_row)

        # ---- connection fields -------------------------------------------------
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        self.preset = combo_field(PRESETS)
        grid.addWidget(FieldRow("Preset", self.preset, "e.g. Waydroid for Waydroid devices"), 0, 0)

        self.adb_path = text_field("", "path to adb executable")
        grid.addWidget(FieldRow("ADB path", self.adb_path), 0, 1)

        self.address = text_field("", "e.g. 192.168.240.112:5555 (empty = auto)")
        grid.addWidget(FieldRow("Device address", self.address), 0, 2)

        self.conn_config = text_field("", "connection config (rarely changed)")
        grid.addWidget(FieldRow("Connection config", self.conn_config), 0, 3)

        self.window_name = text_field("Arknights", "X11 window title for the Window preset")
        grid.addWidget(FieldRow("Window title", self.window_name), 2, 3)

        self.focus_for_keys = combo_field(["false", "true"])
        grid.addWidget(FieldRow("Focus for keys", self.focus_for_keys,
                                "move input focus to the game before sending keys"), 3, 0)

        self.touch_mode = combo_field(TOUCH_MODES, default_index=2)
        grid.addWidget(FieldRow("Touch mode", self.touch_mode), 1, 0)

        self.global_resource = combo_field(RESOURCE_GLOBALS, editable=True, default_index=1)
        grid.addWidget(FieldRow("Global resource", self.global_resource,
                                "YoStarEN / YoStarJP / YoStarKR for non-CN clients"), 1, 1)

        self.cpu_ocr = combo_field(["true", "false"], default_index=1)
        grid.addWidget(FieldRow("CPU OCR", self.cpu_ocr), 1, 2)

        self.gpu_ocr = text_field("", "GPU ID, empty = CPU OCR")
        grid.addWidget(FieldRow("GPU OCR", self.gpu_ocr), 1, 3)

        self.deployment_pause = combo_field(["false", "true"])
        grid.addWidget(FieldRow("Deployment with pause", self.deployment_pause), 2, 0)

        self.adb_lite = combo_field(["false", "true"])
        grid.addWidget(FieldRow("ADB Lite", self.adb_lite), 2, 1)

        self.kill_adb = combo_field(["false", "true"])
        grid.addWidget(FieldRow("Kill adb on exit", self.kill_adb), 2, 2)

        outer.addLayout(grid)

        # ---- device status + actions -------------------------------------------
        status_row = QHBoxLayout()
        self.device_dot = StatusDot()
        self.device_label = QLabel("device status unknown")
        self.device_label.setStyleSheet(f"color: {theme.TEXT_DIM};")
        self.check_btn = QPushButton("Check device")
        self.check_btn.clicked.connect(self.check_device)
        self.save_btn = QPushButton("Save profile")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.save_profile)
        status_row.addWidget(self.device_dot)
        status_row.addWidget(self.device_label)
        status_row.addStretch(1)
        status_row.addWidget(self.check_btn)
        status_row.addWidget(self.save_btn)
        outer.addLayout(status_row)

        # ---- maa tools -----------------------------------------------------------
        tools = QHBoxLayout()
        for label, fn in (
            ("Hot-Update resources", self._hot_update),
            ("Cleanup cache", self._cleanup),
            ("Open config dir", self._open_config),
        ):
            b = QPushButton(label)
            b.clicked.connect(fn)
            tools.addWidget(b)
        tools.addStretch(1)
        outer.addLayout(tools)

        hint = QLabel(
            f"Config directory: {maa.config_dir()} — profiles live in "
            f"{maa.profiles_dir()}. Saving edits profile files in place, "
            "preserving comments and unknown fields."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.TEXT_DIM};")
        outer.addWidget(hint)
        outer.addStretch(1)

        self._reload_profiles()

    # ------------------------------------------------------------------ profiles

    def _reload_profiles(self):
        maa.ensure_default_profile()
        current = self.profile_combo.currentText()
        self._profiles = maa.list_profiles()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self._profiles)
        if current in self._profiles:
            self.profile_combo.setCurrentText(current)
        elif self.state.profile in self._profiles:
            self.profile_combo.setCurrentText(self.state.profile)
        else:
            self.profile_combo.setCurrentIndex(0)
        self.profile_combo.blockSignals(False)
        self._on_profile_switched(self.profile_combo.currentText())

    def _on_profile_switched(self, name: str):
        if not name:
            return
        self.state.set_profile(name)
        self._load_profile(name)

    def _load_profile(self, name: str):
        data = maa.read_profile(name)
        conn = data.get("connection", {})
        res = data.get("resource", {})
        stat = data.get("static_options", {})
        inst = data.get("instance_options", {})
        self.preset.setCurrentText(str(conn.get("preset", "")))
        self.adb_path.setText(str(conn.get("adb_path", "")))
        self.address.setText(str(conn.get("address", "")))
        self.conn_config.setText(str(conn.get("config", "")))
        self.window_name.setText(str(conn.get("window_name", "Arknights")))
        self.focus_for_keys.setCurrentText("true" if conn.get("focus_for_keys", False) else "false")
        touch = str(inst.get("touch_mode", "MaaTouch"))
        if touch in TOUCH_MODES:
            self.touch_mode.setCurrentText(touch)
        gr = str(res.get("global_resource", ""))
        if gr in RESOURCE_GLOBALS:
            self.global_resource.setCurrentText(gr)
        else:
            # this GUI targets the EN client; without a global pack, localized
            # screens (recruit/mall/award) are read as CN and the runs stall
            self.global_resource.setCurrentText("YoStarEN")
        self.cpu_ocr.setCurrentText("true" if stat.get("cpu_ocr", True) else "false")
        gpu = stat.get("gpu_ocr", "")
        self.gpu_ocr.setText("" if gpu in (None, "") else str(gpu))
        self.deployment_pause.setCurrentText("true" if inst.get("deployment_with_pause", False) else "false")
        self.adb_lite.setCurrentText("true" if inst.get("adb_lite_enabled", False) else "false")
        self.kill_adb.setCurrentText("true" if inst.get("kill_adb_on_exit", False) else "false")

    def save_profile(self):
        name = self.profile_combo.currentText()
        if not name:
            QMessageBox.warning(self, "Save profile", "No profile selected — create one with New… first.")
            return
        values: dict[str, str | int | float | bool] = {
            "connection.preset": self.preset.currentText().strip(),
            "connection.adb_path": self.adb_path.text().strip(),
            "connection.address": self.address.text().strip(),
            "connection.config": self.conn_config.text().strip(),
            "connection.window_name": self.window_name.text().strip(),
            "connection.focus_for_keys": self.focus_for_keys.currentText() == "true",
            "instance_options.touch_mode": self.touch_mode.currentText(),
            "resource.global_resource": self.global_resource.currentText().strip(),
            "static_options.cpu_ocr": self.cpu_ocr.currentText() == "true",
            "static_options.gpu_ocr": self.gpu_ocr.text().strip(),
            "instance_options.deployment_with_pause": self.deployment_pause.currentText() == "true",
            "instance_options.adb_lite_enabled": self.adb_lite.currentText() == "true",
            "instance_options.kill_adb_on_exit": self.kill_adb.currentText() == "true",
        }
        try:
            maa.set_profile_fields(name, values)
        except Exception as e:  # surface failures instead of failing silently
            QMessageBox.critical(self, "Save profile", f"Failed to save '{name}':\n{e}")
            return
        self.device_label.setText(f"saved profile '{name}'")
        self.device_label.setStyleSheet(f"color: {theme.OK};")
        self.check_device()

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "New profile", "Profile name:")
        name = name.strip()
        if not ok or not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            return
        maa.write_profile(name, {"connection": {"address": ""}})
        self._reload_profiles()
        self.profile_combo.setCurrentText(name)

    def _duplicate_profile(self):
        src = self.profile_combo.currentText()
        if not src:
            return
        name, ok = QInputDialog.getText(self, "Duplicate profile",
                                        f"Name for a copy of '{src}':")
        name = name.strip()
        if not ok or not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in self._profiles:
            return
        maa.duplicate_profile(src, name)
        self._reload_profiles()
        self.profile_combo.setCurrentText(name)

    def _delete_profile(self):
        name = self.profile_combo.currentText()
        if not name:
            return
        ret = QMessageBox.question(
            self, "Delete profile",
            f"Delete profile '{name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        maa.delete_profile(name)
        self._reload_profiles()

    # ------------------------------------------------------------------ device

    def check_device(self):
        preset = self.preset.currentText()
        address = self.address.text().strip()
        adb = self.adb_path.text().strip()
        self.device_dot.set_ok(None)
        self.device_label.setText("checking…")
        self._pool.start(_DeviceCheck(preset, address, adb, self.window_name.text().strip(), self._on_device_result))

    def _on_device_result(self, ok: bool, detail: str):
        self.device_dot.set_ok(ok)
        self.device_label.setText(detail)
        self.device_label.setStyleSheet(
            f"color: {theme.OK if ok else theme.ERR};")

    # ------------------------------------------------------------------ tools

    def _hot_update(self):
        self._run_tool(["hot-update"])

    def _cleanup(self):
        self._run_tool(["cleanup", "--batch"])

    def _run_tool(self, args):
        if self.runner is None:
            QMessageBox.warning(self, "Unavailable", "Task runner not connected.")
            return
        if not self.runner.start_command(args, label=args[0]):
            QMessageBox.information(self, "Busy", "Another task is already running.")

    def _open_config(self):
        maa.open_in_file_manager(maa.config_dir())
