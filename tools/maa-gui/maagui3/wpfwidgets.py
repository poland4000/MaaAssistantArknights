"""WPF-MAA style building blocks shared by the MaaGui3 pages.

- LogPanel      — the right-hand log column of the WPF Farming tab: a dim
                  timestamp column plus colored content, newest at the bottom,
                  auto-scrolling.
- CheckCombo    — HandyControl-style CheckComboBox (multi-select facilities…).
- SubTabRow     — the pill-style inner tab row used by Copilot/Toolbox.
- make_status_dot — tiny colored dot used by the status bar.
"""

from __future__ import annotations

import re
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import theme

MAX_LOG_ENTRIES = 800


class LogPanel(QScrollArea):
    """WPF-style log column: `MM-DD HH:mm:ss` in dim gray + colored content."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setObjectName("logPanel")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._body = QWidget()
        self._body.setObjectName("logBody")
        self._lay = QVBoxLayout(self._body)
        self._lay.setContentsMargins(8, 4, 8, 8)
        self._lay.setSpacing(1)
        self._lay.addStretch(1)
        self.setWidget(self._body)
        self._n = 0
        self._auto_scroll = True

    def append(self, content: str, color: str = "", ts: str | None = None,
               bold: bool = False, indent: bool = False):
        """Add one entry. Multi-line content splits into rows; only the first
        row carries the timestamp (like the WPF card log)."""
        stamp = ts if ts is not None else time.strftime("%m-%d %H:%M:%S")
        lines = content.rstrip("\n").split("\n")
        color = color or theme.TEXT
        weight = " font-weight:600;" if bold else ""
        for i, line in enumerate(lines or [""]):
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 1, 0, 1)
            row_lay.setSpacing(10)
            time_lbl = QLabel(stamp if i == 0 else "")
            time_lbl.setObjectName("logTime")
            time_lbl.setStyleSheet(f"color: {theme.TEXT_TRACE};")
            time_lbl.setFixedWidth(92)
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            row_lay.addWidget(time_lbl)
            content_lbl = QLabel(line if line else " ")
            content_lbl.setObjectName("logContent")
            content_lbl.setWordWrap(True)
            content_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            extra = " margin-left: 102px;" if indent else ""
            content_lbl.setStyleSheet(f"color: {color};{weight}{extra}")
            row_lay.addWidget(content_lbl, 1)
            self._lay.insertWidget(self._lay.count() - 1, row)
            self._n += 1
        self._trim()
        if self._auto_scroll:
            sb = self.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _trim(self):
        while self._n > MAX_LOG_ENTRIES:
            item = self._lay.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
            elif item is None:
                break
            self._n -= 1

    def clear_log(self):
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._n = 0

    # --- maa-cli line -> (content, color) ---------------------------------
    TAG_COLOR = [
        (re.compile(r"error|failed|fail\b", re.I), theme.ERR),
        (re.compile(r"warning|WRN", re.I), theme.WARN),
    ]

    def append_line(self, line: str):
        """Feed one raw maa-cli output line (LogView-compatible slot)."""
        line = line.rstrip()
        if not line:
            return
        color = next((c for rx, c in self.TAG_COLOR if rx.search(line)), theme.TEXT)
        # highlight the recruit/tag result lines in MAA's cyan, like the WPF
        if re.search(r"★|star|Recruit confirm|Recruitment Results|Tags", line):
            color = theme.LOG_INFO
        self.append(line, color)


class CheckCombo(QComboBox):
    """QComboBox with checkable items (HandyControl CheckComboBox look).

    The closed state shows `<n> selected` / the placeholder instead of the
    last-clicked item.
    """

    def __init__(self, items: list[str] | None = None, placeholder: str = "", parent=None):
        super().__init__(parent)
        self._placeholder = placeholder or "select…"
        self._checks: list[bool] = []
        view = QListView()
        self.setView(view)
        view.setStyleSheet(
            "QListView { background-color: %s; border: 1px solid %s; outline: 0; }"
            "QListView::item { height: 24px; }"
            "QListView::item:hover { background-color: %s; }"
            % (theme.BG_REGION, theme.BORDER, theme.BG_REGION_LIGHT)
        )
        if items:
            self.addItems(items)
        self.activated.connect(self._toggle_current)

    def addItems(self, texts) -> None:  # type: ignore[override]
        super().addItems(list(texts))
        self._checks.extend([False] * (self.count() - len(self._checks)))
        for i in range(self.count()):
            item = self.model().item(i)
            if item is not None:
                item.setCheckable(True)
                item.setCheckState(
                    Qt.CheckState.Checked if self._checks[i] else Qt.CheckState.Unchecked
                )

    def _toggle_current(self, index: int):
        self._checks[index] = not self._checks[index]
        item = self.model().item(index)
        if item is not None:
            item.setCheckState(
                Qt.CheckState.Checked if self._checks[index] else Qt.CheckState.Unchecked
            )
        self.setCurrentIndex(-1)

    def paintEvent(self, e):
        n = sum(self._checks)
        if n == 0:
            self.lineEdit().setText("") if self.isEditable() else None
        super().paintEvent(e)
        # draw the summary text over the (empty) current text
        if not self.isEditable():
            from PySide6.QtGui import QPainter, QPen

            p = QPainter(self)
            p.setPen(QPen(QColor(theme.TEXT_DIM if n == 0 else theme.TEXT)))
            p.drawText(self.rect().adjusted(8, 0, -24, 0),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       self._summary())
            p.end()

    def _summary(self) -> str:
        n = sum(self._checks)
        if n == 0:
            return self._placeholder
        if n <= 3:
            return ", ".join(self.checked_items())
        return f"{n} selected"

    def checked_items(self) -> list[str]:
        return [self.itemText(i) for i, c in enumerate(self._checks) if c]

    def set_checked(self, items: list[str]):
        for i in range(self.count()):
            self._checks[i] = self.itemText(i) in items
            item = self.model().item(i)
            if item is not None:
                item.setCheckState(
                    Qt.CheckState.Checked if self._checks[i] else Qt.CheckState.Unchecked
                )


class SubTabRow(QWidget):
    """Pill-style inner tab row (copilot types / toolbox recognitions)."""

    changed = Signal(int)

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._buttons: list[QPushButton] = []
        for i, label in enumerate(labels):
            b = QPushButton(label)
            b.setObjectName("subTab")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setChecked(i == 0)
            b.clicked.connect(lambda _=False, idx=i: self.changed.emit(idx))
            lay.addWidget(b)
            self._buttons.append(b)
        lay.addStretch(1)

    def set_current(self, index: int):
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
            self.changed.emit(index)

    def current(self) -> int:
        for i, b in enumerate(self._buttons):
            if b.isChecked():
                return i
        return 0


class StatusDot(QLabel):
    """Small colored status dot (green ok / red fail / gray unknown)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self.set_ok(None)

    def set_ok(self, ok: bool | None):
        color = "#7a7f8a" if ok is None else (theme.OK if ok else theme.ERR)
        self.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
