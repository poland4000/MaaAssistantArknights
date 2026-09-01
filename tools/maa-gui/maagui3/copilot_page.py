"""Copilot tab — the WPF CopilotView (自动战斗) layout plus the fork extras.

Pills across the top switch between Copilot / SSS / Paradox (like the WPF
copilot type list) and **PRTS Search** — the fork extra that searches
prts.plus for stage clears and matches them against your own roster
(OperBox recognition) so you only queue battles you can actually run.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from maagui import maa
from maagui.pages.copilot import looks_like_copilot, normalize_copilot_uri
from maagui.pages.search import SearchPage
from maagui.runner import TaskRunner

from . import theme
from .wpfwidgets import SubTabRow

SUPPORT_USAGE = [
    ("0", "Don't borrow support units"),
    ("1", "Borrow if exactly one is missing"),
    ("2", "Borrow the specified operator"),
    ("3", "Borrow a random operator"),
]
RAID_MODES = ["both", "normal", "raid"]

PRTS_PLUS_URL = "https://prts.plus/"


class CopilotPage(QWidget):
    def __init__(self, runner: TaskRunner, settings: QSettings, state, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.settings = settings
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        self.tabs = SubTabRow(["Copilot", "SSS", "Paradox", "PRTS Search"])
        self.tabs.changed.connect(self._on_tab)
        outer.addWidget(self.tabs)

        # --- copilot view (WPF layout) ------------------------------------
        self.copilot_view = QWidget()
        self.copilot_view.setObjectName("pageRoot")
        cv = QVBoxLayout(self.copilot_view)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(10)

        file_row = QHBoxLayout()
        self.file_box = QLineEdit()
        self.file_box.setPlaceholderText(
            "Copilot file path, maa:// code or prts:// link")
        self.file_box.returnPressed.connect(self._add_current_to_queue)
        file_row.addWidget(self.file_box, 1)
        browse = QPushButton("Browse…")
        browse.setToolTip("Select a copilot JSON file")
        browse.clicked.connect(self._browse)
        file_row.addWidget(browse)
        paste = QPushButton("📋 Paste")
        paste.setToolTip(
            "Paste a copilot code from the clipboard — accepts prts:// links, "
            "maa:// codes, raw JSON or file paths")
        paste.clicked.connect(self._paste_clipboard)
        file_row.addWidget(paste)
        cv.addLayout(file_row)

        # centered column, like the WPF copilot view
        column = QVBoxLayout()
        column.setSpacing(10)

        start_row = QHBoxLayout()
        start_row.addStretch(1)
        self.start_btn = QPushButton("Start")
        self.start_btn.setObjectName("linkStart")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._start)
        start_row.addWidget(self.start_btn)
        start_row.addStretch(1)
        column.addLayout(start_row)

        opts = QGridLayout()
        opts.setHorizontalSpacing(24)
        opts.setVerticalSpacing(10)
        opts.setColumnMinimumWidth(0, 280)
        opts.setColumnMinimumWidth(1, 280)

        self.formation = QCheckBox("Auto squad")
        self.formation.setToolTip("Build the squad from the copilot file")
        opts.addWidget(self.formation, 0, 0)

        self.add_trust = QCheckBox("Fill empty slots by trust")
        opts.addWidget(self.add_trust, 0, 1)

        self.support_usage = QComboBox()
        for value, label in SUPPORT_USAGE:
            self.support_usage.addItem(label, value)
        opts.addWidget(self._with_label("Support units", self.support_usage), 1, 0)

        self.support_name = QLineEdit()
        self.support_name.setPlaceholderText("operator to borrow")
        opts.addWidget(self._with_label("Support operator", self.support_name), 1, 1)

        self.loop_times = QSpinBox()
        self.loop_times.setRange(1, 99)
        opts.addWidget(self._with_label("Loop times", self.loop_times), 2, 0)

        self.raid = QComboBox()
        self.raid.addItems(RAID_MODES)
        self.raid.setToolTip("normal / raid (challenge) / both — which modes to run")
        opts.addWidget(self._with_label("Mode", self.raid), 2, 1)

        self.sanity_potion = QCheckBox("Use sanity potions when short")
        opts.addWidget(self.sanity_potion, 3, 0)
        opts_holder = QWidget()
        opts_holder.setObjectName("pageRoot")
        opts_holder.setLayout(opts)
        opts_row = QHBoxLayout()
        opts_row.addStretch(1)
        opts_row.addWidget(opts_holder)
        opts_row.addStretch(1)
        column.addLayout(opts_row)

        self.use_list = QCheckBox("Use copilot list (queue multiple battles)")
        self.use_list.setChecked(self.settings.value("copilot/use_list", False, bool))
        self.use_list.toggled.connect(
            lambda on: self.settings.setValue("copilot/use_list", on))
        self.use_list.toggled.connect(self._update_queue_enabled)
        column.addWidget(self.use_list)

        self.queue = QListWidget()
        self.queue.setObjectName("taskList")
        self.queue.setMaximumHeight(220)
        column.addWidget(self.queue)

        q_btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.setToolTip("Add the path/link in the box above to the queue")
        add_btn.clicked.connect(self._add_current_to_queue)
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self._remove_selected)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.queue.clear)
        q_btns.addWidget(add_btn)
        q_btns.addWidget(remove_btn)
        q_btns.addWidget(clear_btn)
        q_btns.addStretch(1)
        column.addLayout(q_btns)
        column.addStretch(1)
        cv.addLayout(column, 1)

        links = QHBoxLayout()
        prts_link = QPushButton("prts.plus — find copilots")
        prts_link.setObjectName("secondary")
        prts_link.setCursor(Qt.CursorShape.PointingHandCursor)
        prts_link.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(PRTS_PLUS_URL)))
        links.addWidget(prts_link)
        links.addStretch(1)
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {theme.TEXT_DIM};")
        links.addWidget(self.status)
        cv.addLayout(links)

        outer.addWidget(self.copilot_view, 1)

        # --- SSS view -------------------------------------------------------
        self.sss_view = self._simple_file_view(
            "SSS copilot JSON path", "Run SSS", self._run_sss, with_loops=True)
        outer.addWidget(self.sss_view, 1)

        # --- paradox view -----------------------------------------------------
        self.paradox_view = self._simple_file_view(
            "Paradox copilot JSON path", "Run Paradox", self._run_paradox)
        outer.addWidget(self.paradox_view, 1)

        # --- PRTS search view (fork extra: operator matching) ----------------
        self.search_page = SearchPage(runner, state)
        self.search_page.add_to_queue.connect(self._enqueue_uris)
        outer.addWidget(self.search_page, 1)

        self._load_settings()
        self._update_queue_enabled()
        self._on_tab(0)

        self.runner.running_changed.connect(self._on_running_changed)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _with_label(label: str, widget) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        lab = QLabel(label)
        lab.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
        lay.addWidget(lab)
        lay.addWidget(widget)
        return w

    def _simple_file_view(self, placeholder: str, run_label: str, run_cb, with_loops: bool = False) -> QWidget:
        w = QWidget()
        w.setObjectName("pageRoot")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(60, 30, 60, 0)
        lay.setSpacing(12)
        box = QLineEdit()
        box.setPlaceholderText(placeholder)
        row = QHBoxLayout()
        row.addWidget(box, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(lambda: self._browse_into(box))
        row.addWidget(browse)
        lay.addLayout(row)
        opts = QHBoxLayout()
        if with_loops:
            loops = QSpinBox()
            loops.setRange(1, 99)
            loops.setValue(1)
            self.sss_loop = loops
            opts.addWidget(self._with_label("Loop times", loops))
        opts.addStretch(1)
        run = QPushButton(run_label)
        run.setObjectName("linkStart")
        run.clicked.connect(run_cb)
        opts.addWidget(run)
        lay.addLayout(opts)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------ tabs
    def _on_tab(self, index: int):
        self.copilot_view.setVisible(index == 0)
        self.sss_view.setVisible(index == 1)
        self.paradox_view.setVisible(index == 2)
        self.search_page.setVisible(index == 3)

    # ------------------------------------------------------------------ queue
    def _queue_uris(self) -> list[str]:
        return [self.queue.item(i).text() for i in range(self.queue.count())]

    def _enqueue_uris(self, entries):
        if isinstance(entries, str):
            entries = [entries]
        existing = set(self._queue_uris())
        added = 0
        for e in entries:
            e = str(e).strip()
            if e and e not in existing:
                self.queue.addItem(QListWidgetItem(e))
                existing.add(e)
                added += 1
        if added:
            self._set_status(f"Queued {added} battle(s) — {self.queue.count()} in the list",
                             theme.OK)
            self._save_queue()
        self._tabs_goto(0)

    def _tabs_goto(self, index: int):
        self.tabs.set_current(index)

    def _add_current_to_queue(self):
        text = self.file_box.text().strip()
        if not text:
            return
        uri = normalize_copilot_uri(text)
        entries = [uri] if uri else ([text] if looks_like_copilot(text) else [])
        if not entries:
            self._set_status("Not a copilot link/code — use maa://, prts://, JSON or a .json file",
                             theme.ERR)
            return
        self.file_box.clear()
        self._enqueue_uris(entries)

    def _remove_selected(self):
        for item in self.queue.selectedItems():
            self.queue.takeItem(self.queue.row(item))
        self._save_queue()

    def _paste_clipboard(self):
        text = QGuiApplication.clipboard().text().strip()
        if not text:
            self._set_status("Clipboard is empty", theme.WARN)
            return
        uri = normalize_copilot_uri(text)
        if uri:
            self.file_box.setText(uri)
            self._set_status("Pasted copilot link — press Add to queue it", theme.OK)
            return
        if looks_like_copilot(text):
            if text.startswith("{"):
                self._set_status("Clipboard holds raw JSON — save it as a .json file first",
                                 theme.WARN)
            else:
                self.file_box.setText(text.splitlines()[0])
                self._set_status("Pasted from clipboard", theme.OK)
            return
        self.file_box.setText(text.splitlines()[0])
        self._set_status("Pasted — not recognized as a copilot code", theme.WARN)

    def _browse(self):
        self._browse_into(self.file_box)

    def _browse_into(self, target: QLineEdit):
        dialog = QFileDialog(self, "Select copilot JSON")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setDirectory(str(maa.config_dir()))
        if dialog.exec():
            cfg = maa.config_dir()
            path = dialog.selectedFiles()[0]
            try:
                path = str(cfg.joinpath(path).resolve().relative_to(cfg))
            except ValueError:
                pass
            target.setText(path)

    def _update_queue_enabled(self, *_):
        self.queue.setEnabled(self.use_list.isChecked())

    def _set_status(self, text: str, color: str = ""):
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color or theme.TEXT_DIM};")

    # ------------------------------------------------------------------ run
    def _build_args(self) -> list[str]:
        args = ["copilot"]
        if self.use_list.isChecked() and self.queue.count():
            args += self._queue_uris()
        else:
            args.append(self.file_box.text().strip())
        args += ["-p", self.state.profile, "--batch"]
        args += ["--raid", self.raid.currentText()]
        if self.formation.isChecked():
            args.append("--formation")
        if self.add_trust.isChecked():
            args.append("--add-trust")
        usage = self.support_usage.currentData()
        args += ["--support-unit-usage", usage]
        name = self.support_name.text().strip()
        if usage in ("2", "3") and name:
            args += ["--support-unit-name", name]
        if self.loop_times.value() > 1:
            args += ["--loop-times", str(self.loop_times.value())]
        if self.sanity_potion.isChecked():
            args.append("--use-sanity-potion")
        return args

    def _start(self):
        if self.runner.running:
            return
        target = (self._queue_uris() if self.use_list.isChecked() and self.queue.count()
                  else [self.file_box.text().strip()])
        if not any(target):
            self._set_status("Add a copilot code, link or file first", theme.WARN)
            return
        self._save_settings()
        args = self._build_args()
        if self.runner.start_command(args, label=f"copilot × {len(target)}"):
            self._set_status(f"Starting {len(target)} battle(s)…", theme.OK)
        else:
            self._set_status("Failed to start maa-cli", theme.ERR)

    def _run_sss(self):
        if self.runner.running:
            return
        box = self.sss_view.findChild(QLineEdit)
        if box is None or not box.text().strip():
            self._set_status("Choose an SSS copilot JSON file first", theme.WARN)
            return
        args = ["ssscopilot", box.text().strip(), "-p", self.state.profile, "--batch"]
        if self.sss_loop.value() > 1:
            args += ["--loop-times", str(self.sss_loop.value())]
        self.runner.start_command(args, label="ssscopilot")

    def _run_paradox(self):
        if self.runner.running:
            return
        box = self.paradox_view.findChild(QLineEdit)
        if box is None or not box.text().strip():
            self._set_status("Choose a paradox copilot JSON file first", theme.WARN)
            return
        self.runner.start_command(
            ["paradoxcopilot", box.text().strip(), "-p", self.state.profile, "--batch"],
            label="paradoxcopilot")

    def _on_running_changed(self, running: bool):
        self.start_btn.setEnabled(not running)

    # ------------------------------------------------------------------ persistence
    def _save_queue(self):
        self.settings.setValue("copilot/queue", self._queue_uris())

    def _save_settings(self):
        s = self.settings
        s.setValue("copilot/formation", self.formation.isChecked())
        s.setValue("copilot/add_trust", self.add_trust.isChecked())
        s.setValue("copilot/support_usage", self.support_usage.currentData())
        s.setValue("copilot/support_name", self.support_name.text())
        s.setValue("copilot/loop_times", self.loop_times.value())
        s.setValue("copilot/raid", self.raid.currentText())
        s.setValue("copilot/sanity_potion", self.sanity_potion.isChecked())
        s.setValue("copilot/file", self.file_box.text())

    def _load_settings(self):
        s = self.settings
        self.formation.setChecked(s.value("copilot/formation", True, bool))
        self.add_trust.setChecked(s.value("copilot/add_trust", False, bool))
        usage = str(s.value("copilot/support_usage", "1"))
        idx = self.support_usage.findData(usage)
        if idx >= 0:
            self.support_usage.setCurrentIndex(idx)
        self.support_name.setText(str(s.value("copilot/support_name", "")))
        self.loop_times.setValue(int(s.value("copilot/loop_times", 1)))
        raid = str(s.value("copilot/raid", "both"))
        if raid in RAID_MODES:
            self.raid.setCurrentText(raid)
        self.sanity_potion.setChecked(s.value("copilot/sanity_potion", False, bool))
        self.file_box.setText(str(s.value("copilot/file", "")))
        for uri in s.value("copilot/queue", [], list) or []:
            self.queue.addItem(QListWidgetItem(str(uri)))
