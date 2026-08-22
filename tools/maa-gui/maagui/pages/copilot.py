"""Copilot page (自动战斗): battle queue + options, like the Windows GUI.

Unlike the other pages this one drives maa-cli directly (`maa copilot`), not a
task file, because the CLI supports everything the Windows app does:
multiple URIs queued as one run (multi-job), --raid both (normal + challenge
modes in sequence), auto-formation, and support-unit (borrow) policies.
"""

from __future__ import annotations

import re

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import maa, theme
from ..runner import TaskRunner
from ..state import AppState
from ..widgets import FieldRow

RAID_MODES = ["both", "normal", "raid"]
SUPPORT_USAGE = [
    ("0", "不借人 — don't borrow"),
    ("1", "缺人时借 — borrow if exactly one missing"),
    ("2", "指定干员 — borrow the specified operator"),
    ("3", "随机干员 — borrow a random one"),
]

_PRTS_RE = re.compile(r"^(?:prts://|https?://prts\.plus/m/)([A-Za-z0-9]+)$")


def normalize_copilot_uri(text: str) -> str | None:
    """Convert a share link to a maa:// URI (prts://83831 → maa://83831)."""
    m = _PRTS_RE.match(text.strip())
    if m:
        return f"maa://{m.group(1)}"
    return None


def looks_like_copilot(text: str) -> bool:
    """Heuristic: is this clipboard content a copilot URI or JSON?"""
    t = text.strip()
    if not t:
        return False
    if normalize_copilot_uri(t):
        return True
    if t.startswith("maa://") or t.startswith("file://"):
        return True
    if t.startswith("{") or t.startswith("["):
        return True
    if t.endswith(".json") or t.endswith(".txt"):
        return True
    return False


class CopilotPage(QWidget):
    def __init__(self, runner: TaskRunner, state: AppState, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Copilot — 自动战斗")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        # ---------------- battle queue (作战列表) -------------------------------
        queue_box = QGroupBox("作战列表 Battle Queue")
        q_lay = QVBoxLayout(queue_box)

        self.queue = QListWidget()
        self.queue.setObjectName("taskList")
        self.queue.setMinimumHeight(110)
        self.queue.itemSelectionChanged.connect(self._update_buttons)
        q_lay.addWidget(self.queue)

        q_btns = QHBoxLayout()
        self.clip_btn = QPushButton("📋  From Clipboard")
        self.clip_btn.setToolTip(
            "Read copilot codes from the clipboard and queue them — "
            "accepts maa:// codes, raw JSON, or file paths, one per line")
        self.clip_btn.clicked.connect(self._import_clipboard)
        self.file_btn = QPushButton("Browse…")
        self.file_btn.clicked.connect(self._browse_file)
        self.remove_btn = QPushButton("Remove selected")
        self.remove_btn.clicked.connect(self._remove_selected)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_queue)
        for b in (self.clip_btn, self.file_btn, self.remove_btn, self.clear_btn):
            q_btns.addWidget(b)
        q_btns.addStretch(1)
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {theme.TEXT_DIM};")
        q_btns.addWidget(self.status)
        q_lay.addLayout(q_btns)
        outer.addWidget(queue_box)

        # ---------------- options (编队 / 借人 / 模式) ---------------------------
        opt_box = QGroupBox("选项 Options")
        og = QGridLayout(opt_box)
        og.setHorizontalSpacing(18)
        og.setVerticalSpacing(10)

        self.formation = QCheckBox("自动编队 AutoSquad")
        self.formation.setToolTip("--formation: auto-build the squad from the task file")
        og.addWidget(self.formation, 0, 0)

        self.formation_index = QSpinBox()
        self.formation_index.setRange(0, 4)
        self.formation_index.setSpecialValueText("current")
        og.addWidget(FieldRow("Formation slot (1–4)", self.formation_index), 0, 1)

        self.add_trust = QCheckBox("空位按信赖填充 (--add-trust)")
        self.add_trust.setToolTip("Fill empty squad slots by ascending trust value")
        og.addWidget(self.add_trust, 0, 2)

        self.support_usage = QComboBox()
        for value, label in SUPPORT_USAGE:
            self.support_usage.addItem(label, value)
        self.support_usage.setToolTip("--support-unit-usage: borrow policy")
        og.addWidget(FieldRow("借干员 Borrow", self.support_usage), 1, 0)

        self.support_name = QLineEdit()
        self.support_name.setPlaceholderText("operator name for 指定/随机 borrow")
        self.support_name.setToolTip("--support-unit-name")
        og.addWidget(FieldRow("借的干员 Support operator", self.support_name), 1, 1)

        self.loop_times = QSpinBox()
        self.loop_times.setRange(1, 99)
        self.loop_times.setValue(1)
        og.addWidget(FieldRow("循环次数 Loop times", self.loop_times), 1, 2)

        self.raid = QComboBox()
        self.raid.addItems(RAID_MODES)
        self.raid.setCurrentText("both")
        self.raid.setToolTip(
            "--raid: normal = normal mode only, raid = challenge mode only, "
            "both = run both modes one after another")
        og.addWidget(FieldRow("作战模式 Mode", self.raid), 2, 0)

        self.sanity_potion = QCheckBox("理智不够用药 (--use-sanity-potion)")
        og.addWidget(self.sanity_potion, 2, 1)

        outer.addWidget(opt_box)

        # ---------------- run controls --------------------------------------------
        run_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Start Battle")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.runner.stop)
        run_row.addWidget(self.start_btn)
        run_row.addWidget(self.stop_btn)
        run_row.addStretch(1)
        outer.addLayout(run_row)

        # ---------------- sss / paradox ---------------------------------------------
        misc = QHBoxLayout()
        sss_box = QGroupBox("SSS Copilot")
        s_lay = QVBoxLayout(sss_box)
        s_row = QHBoxLayout()
        self.sss_file = QLineEdit()
        self.sss_file.setPlaceholderText("SSS copilot JSON path")
        s_row.addWidget(self.sss_file, 1)
        s_browse = QPushButton("Browse…")
        s_browse.clicked.connect(lambda: self._browse_into(self.sss_file, "Select SSS copilot JSON"))
        s_row.addWidget(s_browse)
        s_lay.addLayout(s_row)
        s_btn_row = QHBoxLayout()
        self.sss_loop = QSpinBox()
        self.sss_loop.setRange(1, 99)
        s_btn_row.addWidget(QLabel("Loops:"))
        s_btn_row.addWidget(self.sss_loop)
        self.sss_run = QPushButton("Run SSS")
        self.sss_run.setObjectName("primary")
        self.sss_run.clicked.connect(self._run_sss)
        s_btn_row.addWidget(self.sss_run)
        s_btn_row.addStretch(1)
        s_lay.addLayout(s_btn_row)
        misc.addWidget(sss_box, 1)

        par_box = QGroupBox("Paradox Copilot")
        p_lay = QVBoxLayout(par_box)
        p_row = QHBoxLayout()
        self.paradox_file = QLineEdit()
        self.paradox_file.setPlaceholderText("paradox copilot JSON path")
        p_row.addWidget(self.paradox_file, 1)
        p_browse = QPushButton("Browse…")
        p_browse.clicked.connect(lambda: self._browse_into(self.paradox_file, "Select paradox copilot JSON"))
        p_row.addWidget(p_browse)
        p_lay.addLayout(p_row)
        self.paradox_run = QPushButton("Run Paradox")
        self.paradox_run.setObjectName("primary")
        self.paradox_run.clicked.connect(self._run_paradox)
        p_lay.addWidget(self.paradox_run)
        misc.addWidget(par_box, 1)
        outer.addLayout(misc)

        outer.addStretch(1)

        self.runner.running_changed.connect(self._on_running_changed)
        self._load_settings()

    # ---------------------------------------------------------------- helpers

    def _relative(self, path: str) -> str:
        cfg = maa.config_dir()
        try:
            return str(cfg.joinpath(path).resolve().relative_to(cfg))
        except ValueError:
            return path

    def _browse_into(self, target, title: str):
        dialog = QFileDialog(self, title)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setDirectory(str(maa.config_dir()))
        if dialog.exec():
            target.setText(self._relative(dialog.selectedFiles()[0]))

    # ---------------------------------------------------------------- queue

    def _queue_uris(self) -> list[str]:
        return [self.queue.item(i).text() for i in range(self.queue.count())]

    def _enqueue(self, entries: list[str], source: str):
        existing = set(self._queue_uris())
        added = 0
        for e in entries:
            if e and e not in existing:
                self.queue.addItem(QListWidgetItem(e))
                existing.add(e)
                added += 1
        if added:
            self.status.setStyleSheet(f"color: {theme.OK};")
            self.status.setText(f"✔ Queued {added} battle(s) from {source}. "
                                f"Queue: {self.queue.count()}")
            self._save_queue()
        else:
            self.status.setStyleSheet(f"color: {theme.TEXT_DIM};")
            self.status.setText("Nothing new to queue.")
        self._update_buttons()

    def _import_clipboard(self):
        text = QGuiApplication.clipboard().text()
        if not text.strip():
            QMessageBox.information(
                self, "Clipboard is empty",
                "Nothing to import — copy a copilot share link or code first "
                "(e.g. prts://83831, maa://xxxxx, or copilot JSON), then click "
                "📋 From Clipboard.")
            return
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            uri = normalize_copilot_uri(line)  # prts://83831 → maa://83831
            if uri:
                entries.append(uri)
            elif looks_like_copilot(line):
                entries.append(line)
        if not entries:
            QMessageBox.information(
                self, "Nothing to queue",
                "No copilot codes found in the clipboard.\n\n"
                "Accepted formats (one per line):\n"
                "• prts://83831  or  https://prts.plus/m/83831\n"
                "• maa://xxxxx  (add a trailing s for a task set)\n"
                "• raw copilot JSON\n"
                "• a .json file path")
            return
        self._enqueue(entries, "clipboard")

    def _browse_file(self):
        dialog = QFileDialog(self, "Select copilot JSON")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setDirectory(str(maa.config_dir()))
        if dialog.exec():
            self._enqueue([self._relative(dialog.selectedFiles()[0])], "file")

    def _remove_selected(self):
        for item in self.queue.selectedItems():
            self.queue.takeItem(self.queue.row(item))
        self._save_queue()
        self._update_buttons()

    def _clear_queue(self):
        self.queue.clear()
        self._save_queue()
        self._update_buttons()

    def _update_buttons(self):
        has = self.queue.count() > 0
        sel = len(self.queue.selectedItems()) > 0
        self.remove_btn.setEnabled(sel)
        self.clear_btn.setEnabled(has)
        self.start_btn.setEnabled(has and not self.runner.running)

    # ---------------------------------------------------------------- run

    def _build_args(self) -> list[str]:
        args = ["copilot", *self._queue_uris(), "-p", self.state.profile, "--batch"]
        args += ["--raid", self.raid.currentText()]
        if self.formation.isChecked():
            args.append("--formation")
            if self.formation_index.value() > 0:
                args += ["--formation-index", str(self.formation_index.value())]
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
        if self.runner.running or self.queue.count() == 0:
            return
        self._save_settings()
        n = self.queue.count()
        args = self._build_args()
        ok = self.runner.start_command(args, label=f"copilot × {n}")
        if ok:
            self.status.setText(f"Starting {n} battle(s)…")
        else:
            self.status.setText("Failed to start maa-cli.")

    def _run_sss(self):
        if self.runner.running or not self.sss_file.text().strip():
            return
        args = ["ssscopilot", self.sss_file.text().strip(), "-p", self.state.profile, "--batch"]
        if self.sss_loop.value() > 1:
            args += ["--loop-times", str(self.sss_loop.value())]
        self.runner.start_command(args, label="ssscopilot")

    def _run_paradox(self):
        if self.runner.running or not self.paradox_file.text().strip():
            return
        self.runner.start_command(
            ["paradoxcopilot", self.paradox_file.text().strip(), "-p", self.state.profile, "--batch"],
            label="paradoxcopilot")

    def _on_running_changed(self, running: bool):
        self.start_btn.setEnabled(not running and self.queue.count() > 0)
        self.stop_btn.setEnabled(running)
        self.sss_run.setEnabled(not running)
        self.paradox_run.setEnabled(not running)

    # ---------------------------------------------------------------- persistence

    def _save_queue(self):
        self.state.settings.setValue("copilot/queue", self._queue_uris())

    def _save_settings(self):
        s = self.state.settings
        s.setValue("copilot/formation", self.formation.isChecked())
        s.setValue("copilot/formation_index", self.formation_index.value())
        s.setValue("copilot/add_trust", self.add_trust.isChecked())
        s.setValue("copilot/support_usage", self.support_usage.currentData())
        s.setValue("copilot/support_name", self.support_name.text())
        s.setValue("copilot/loop_times", self.loop_times.value())
        s.setValue("copilot/raid", self.raid.currentText())
        s.setValue("copilot/sanity_potion", self.sanity_potion.isChecked())
        s.setValue("copilot/sss_file", self.sss_file.text())
        s.setValue("copilot/sss_loop", self.sss_loop.value())
        s.setValue("copilot/paradox_file", self.paradox_file.text())

    def _load_settings(self):
        s = self.state.settings
        for uri in s.value("copilot/queue", [], list):
            self.queue.addItem(QListWidgetItem(str(uri)))
        self.formation.setChecked(s.value("copilot/formation", False, bool))
        self.formation_index.setValue(int(s.value("copilot/formation_index", 0)))
        self.add_trust.setChecked(s.value("copilot/add_trust", False, bool))
        usage = str(s.value("copilot/support_usage", "0"))
        idx = self.support_usage.findData(usage)
        if idx >= 0:
            self.support_usage.setCurrentIndex(idx)
        self.support_name.setText(str(s.value("copilot/support_name", "")))
        self.loop_times.setValue(int(s.value("copilot/loop_times", 1)))
        raid = str(s.value("copilot/raid", "both"))
        if raid in RAID_MODES:
            self.raid.setCurrentText(raid)
        self.sanity_potion.setChecked(s.value("copilot/sanity_potion", False, bool))
        self.sss_file.setText(str(s.value("copilot/sss_file", "")))
        self.sss_loop.setValue(int(s.value("copilot/sss_loop", 1)))
        self.paradox_file.setText(str(s.value("copilot/paradox_file", "")))
        self._update_buttons()


# ---------------------------------------------------------------------------
# clipboard detection helper used by _import_clipboard
# ---------------------------------------------------------------------------
