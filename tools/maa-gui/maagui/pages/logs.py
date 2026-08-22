"""Logs page (日志): live run output + MaaCore log file browsing."""

from __future__ import annotations

import os
import time

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .. import maa, theme
from ..runner import TaskRunner
from ..widgets import LogView


def _scan_logs() -> list:
    """Scan the MaaCore debug dir for .log files, newest first."""
    d = maa.log_dir()
    if not d.is_dir():
        return []
    out = []
    try:
        for p in sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if p.suffix == ".log":
                st = p.stat()
                out.append((str(p), st.st_mtime, st.st_size))
    except OSError:
        pass
    return out[:50]


class LogsPage(QWidget):
    def __init__(self, runner: TaskRunner, parent=None):
        super().__init__(parent)
        self.runner = runner

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Logs — 日志")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        splitter = QSplitter()

        # left: live log ----------------------------------------------------------
        self.view = LogView()
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        self.run_state = QLabel("idle")
        self.run_state.setStyleSheet(f"color: {theme.TEXT_DIM};")
        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        self.auto_scroll.toggled.connect(self.view.set_auto_scroll)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear)
        head.addWidget(self.run_state)
        head.addStretch(1)
        head.addWidget(self.auto_scroll)
        head.addWidget(self.clear_btn)
        left_lay.addLayout(head)
        left_lay.addWidget(self.view, 1)
        splitter.addWidget(left)

        # right: core log files -----------------------------------------------------
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.addWidget(QLabel("MaaCore logs (maa dir log):"))
        self.file_list = QListWidget()
        self.file_list.setObjectName("taskList")
        self.file_list.currentItemChanged.connect(self._show_file)
        right_lay.addWidget(self.file_list, 1)
        self.file_view = LogView()
        self.file_view.setMaximumBlockCount(2000)
        right_lay.addWidget(self.file_view, 2)
        self.refresh_btn = QPushButton("Refresh list")
        self.refresh_btn.clicked.connect(self._refresh_files)
        right_lay.addWidget(self.refresh_btn)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)

        # live log wiring -------------------------------------------------------------
        self.runner.log_line.connect(self.view.append_line)
        self.runner.started.connect(self._on_started)
        self.runner.finished.connect(self._on_finished)
        self.runner.running_changed.connect(self._on_running_changed)

        self._scanner = QTimer(self)
        self._scanner.setInterval(5000)
        self._scanner.timeout.connect(self._refresh_files)
        self._scanner.start()
        self._refresh_files()
        self._scan_version()

    def _scan_version(self):
        cli, core = maa.versions()
        if cli:
            self.view.append_line(f"maa-cli {cli} / MaaCore {core}")

    def _clear(self):
        self.view.clear_log()

    def _on_started(self, task: str):
        self.view.append_line(f"─── starting task '{task}' ───")
        self.run_state.setText(f"running: {task}")

    def _on_finished(self, code: int, summary: str):
        color = theme.OK if code == 0 else theme.ERR
        self.run_state.setStyleSheet(f"color: {color};")
        self.run_state.setText(summary)

    def _on_running_changed(self, running: bool):
        if not running:
            self.run_state.setStyleSheet(f"color: {theme.TEXT_DIM};")

    # ---- file browsing ---------------------------------------------------------

    def _refresh_files(self):
        self._on_scan(_scan_logs())

    @Slot(list)
    def _on_scan(self, files):
        current = self.file_list.currentItem().text() if self.file_list.currentItem() else ""
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for path, mtime, size in files:
            name = os.path.basename(path)
            stamp = time.strftime("%m-%d %H:%M", time.localtime(mtime))
            item = QListWidgetItem(f"{name}  ({stamp}, {size // 1024} KB)")
            item.setData(0x0100, path)  # Qt.UserRole
            self.file_list.addItem(item)
            if name == current:
                self.file_list.setCurrentItem(item)
        self.file_list.blockSignals(False)

    def _show_file(self, item: QListWidgetItem | None, _prev=None):
        if item is None:
            return
        path = item.data(0x0100)
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()
        except OSError as e:
            self.file_view.clear_log()
            self.file_view.append_line(f"cannot read {path}: {e}")
            return
        lines = text.splitlines()
        if len(lines) > 2000:
            lines = lines[-2000:]
        self.file_view.clear_log()
        for ln in lines:
            self.file_view.append_line(ln)

    def shutdown(self):
        self._scanner.stop()
