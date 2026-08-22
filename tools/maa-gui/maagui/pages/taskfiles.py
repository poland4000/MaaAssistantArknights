"""Task Files page (任务文件): manage custom maa-cli tasks with raw TOML editing.

This is the escape hatch for everything without a dedicated form — Depot,
OperBox, Custom, variants/conditions, and hand-authored tasks.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .. import maa, theme
from ..runner import TaskRunner
from ..state import AppState

TEMPLATE = """# Custom task
[[tasks]]
type = "Fight"

[tasks.params]
stage = "1-7"
"""


class TaskFilesPage(QWidget):
    def __init__(self, runner: TaskRunner, state: AppState, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state
        self._names: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Task Files — 任务文件")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # left: task list --------------------------------------------------------
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setObjectName("taskList")
        self.list.currentItemChanged.connect(self._on_select)
        left_lay.addWidget(self.list, 1)

        left_btns = QHBoxLayout()
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._new_task)
        self.dup_btn = QPushButton("Duplicate")
        self.dup_btn.clicked.connect(self._duplicate_task)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._delete_task)
        left_btns.addWidget(self.new_btn)
        left_btns.addWidget(self.dup_btn)
        left_btns.addWidget(self.del_btn)
        left_lay.addLayout(left_btns)
        splitter.addWidget(left)

        # right: editor ------------------------------------------------------------
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Task:"))
        self.name_label = QLabel("—")
        self.name_label.setStyleSheet(f"color: {theme.TEXT_DIM};")
        info_row.addWidget(self.name_label, 1)
        info_row.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("(detect from file)", "")
        for t in maa.TASK_TYPES:
            self.type_combo.addItem(maa.TASK_TYPE_LABELS.get(t, t), t)
        info_row.addWidget(self.type_combo)
        right_lay.addLayout(info_row)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("tomlEdit")
        self.editor.setPlaceholderText(
            "TOML task definition — see maa-cli docs for the [[tasks]] format"
        )
        right_lay.addWidget(self.editor, 1)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save_task)
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._run_task)
        self.rename_btn = QPushButton("Rename")
        self.rename_btn.clicked.connect(self._rename_task)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.rename_btn)
        btn_row.addStretch(1)
        right_lay.addLayout(btn_row)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        outer.addWidget(splitter, 1)

        self.runner.running_changed.connect(self._on_running_changed)
        self._reload()

    # ------------------------------------------------------------------ list

    def _reload(self, select: str = ""):
        current = select or self.list.currentItem().text() if self.list.currentItem() else ""
        self._names = [n for n in maa.list_tasks() if not n.startswith(maa.GUI_PREFIX)]
        self.list.blockSignals(True)
        self.list.clear()
        for n in self._names:
            self.list.addItem(QListWidgetItem(n))
        self.list.blockSignals(False)
        if current in self._names:
            items = self.list.findItems(current, Qt.MatchFlag.MatchExactly)
            if items:
                self.list.setCurrentItem(items[0])
        if self.list.currentItem():
            self._on_select(self.list.currentItem(), None)
        else:
            self.name_label.setText("—")
            self.editor.setPlainText("")
            self.editor.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.run_btn.setEnabled(False)
            self.rename_btn.setEnabled(False)
            self.dup_btn.setEnabled(False)
            self.del_btn.setEnabled(False)

    def _on_select(self, item: QListWidgetItem | None, _prev):
        if item is None:
            return
        self.name_label.setText(item.text())
        self.editor.setPlainText(maa.read_task(item.text()))
        self.editor.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.run_btn.setEnabled(not self.runner.running)
        self.rename_btn.setEnabled(True)
        self.dup_btn.setEnabled(True)
        self.del_btn.setEnabled(True)

    # ------------------------------------------------------------------ actions

    def _new_task(self):
        name, ok = QInputDialog.getText(self, "New task", "Task name:")
        name = name.strip()
        if not ok or not name or name in self._names or name.startswith(maa.GUI_PREFIX):
            if ok and (name in self._names or name.startswith(maa.GUI_PREFIX)):
                QMessageBox.warning(self, "Name taken", f"Task '{name}' already exists or is reserved.")
            return
        maa.write_task(name, TEMPLATE)
        self._reload(select=name)

    def _duplicate_task(self):
        src = self._current()
        if not src:
            return
        name, ok = QInputDialog.getText(self, "Duplicate task",
                                        f"Name for a copy of '{src}':")
        name = name.strip()
        if not ok or not name or name in self._names or name.startswith(maa.GUI_PREFIX):
            return
        maa.write_task(name, maa.read_task(src))
        self._reload(select=name)

    def _delete_task(self):
        name = self._current()
        if not name:
            return
        ret = QMessageBox.question(
            self, "Delete task", f"Delete task '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        maa.delete_task(name)
        self._reload()

    def _rename_task(self):
        src = self._current()
        if not src:
            return
        name, ok = QInputDialog.getText(self, "Rename task", "New name:", text=src)
        name = name.strip()
        if not ok or not name or name in self._names or name.startswith(maa.GUI_PREFIX):
            return
        maa.write_task(name, maa.read_task(src))
        maa.delete_task(src)
        self._reload(select=name)

    def _save_task(self):
        name = self._current()
        if not name:
            return
        text = self.editor.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Empty", "Task file is empty.")
            return
        maa.write_task(name, text)
        self.type_combo.setCurrentIndex(0)  # reset "detect" hint

    def _run_task(self):
        if self.runner.running:
            return
        self._save_task()
        self.runner.start(self._current(), self.state.profile)

    def _current(self) -> str:
        item = self.list.currentItem()
        return item.text() if item else ""

    def _on_running_changed(self, running: bool):
        self.run_btn.setEnabled(not running)
