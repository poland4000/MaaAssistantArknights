"""Reusable widgets: log view, form fields, status dot, section helpers."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import theme

# ---------------------------------------------------------------------------
# Log view
# ---------------------------------------------------------------------------

LEVEL_COLORS = {
    "INFO": theme.TEXT,
    "INF": theme.TEXT,
    "WARN": theme.WARN,
    "WRN": theme.WARN,
    "ERROR": theme.ERR,
    "ERR": theme.ERR,
    "FATAL": theme.ERR,
    "FTAL": theme.ERR,
}

MAX_BLOCKS = 4000


class LogView(QPlainTextEdit):
    """Read-only, auto-scrolling log pane with level-based coloring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("logView")
        self.setReadOnly(True)
        self.setMaximumBlockCount(MAX_BLOCKS)
        self._auto_scroll = True

    def set_auto_scroll(self, on: bool):
        self._auto_scroll = on

    def append_line(self, line: str):
        level = "INFO"
        for tok, color in LEVEL_COLORS.items():
            if tok in line.split():
                level = tok
                break
        color = LEVEL_COLORS.get(level, theme.TEXT)
        html = f'<span style="color:{color}">{_esc(line)}</span>'
        self.appendHtml(html)

    def clear_log(self):
        self.clear()


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Form field helpers
# ---------------------------------------------------------------------------

class FieldRow(QWidget):
    """A labeled form row that stacks vertically, suitable for narrow columns."""

    def __init__(self, label: str, widget, tooltip: str = ""):
        super().__init__()
        from PySide6.QtWidgets import QBoxLayout
        if isinstance(widget, QBoxLayout):
            holder = QWidget()
            holder.setLayout(widget)
            widget = holder
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        lab = QLabel(label)
        lab.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
        if tooltip:
            lab.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        lay.addWidget(lab)
        lay.addWidget(widget)


def text_field(default: str = "", placeholder: str = "") -> QLineEdit:
    e = QLineEdit(default)
    e.setPlaceholderText(placeholder)
    return e


def spin_field(default: int = 0, minimum: int = 0, maximum: int = 99999, suffix: str = "") -> QSpinBox:
    s = QSpinBox()
    s.setRange(minimum, maximum)
    s.setValue(default)
    if suffix:
        s.setSuffix(suffix)
    return s


def dspin_field(default: float = 0.0, minimum: float = 0.0, maximum: float = 100.0) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(minimum, maximum)
    s.setValue(default)
    s.setDecimals(1)
    return s


def combo_field(items: list[str], default_index: int = 0, editable: bool = False) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    c.setCurrentIndex(max(0, min(default_index, len(items) - 1)))
    c.setEditable(editable)
    return c


def bool_field(default: bool = False) -> QCheckBox:
    c = QCheckBox()
    c.setChecked(default)
    return c


def form_row(form: QFormLayout, label: str, widget: QWidget) -> None:
    form.addRow(QLabel(label), widget)


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

class StatusDot(QLabel):
    """Small colored dot (green/red/gray) used for device & run status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.set_ok(None)

    def set_ok(self, ok: bool | None):
        color = theme.TEXT_DIM if ok is None else (theme.OK if ok else theme.ERR)
        self.setStyleSheet(
            f"background-color: {color}; border-radius: 6px;"
        )


def section_card(title: str) -> tuple[QWidget, QVBoxLayout]:
    """A titled card (QGroupBox-like) returning (container, inner layout)."""
    from PySide6.QtWidgets import QGroupBox
    box = QGroupBox(title)
    lay = QVBoxLayout(box)
    lay.setSpacing(10)
    return box, lay


def hbox(*widgets, margins=(0, 0, 0, 0), spacing=8) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    for w in widgets:
        if w is None:
            lay.addStretch(1)
        else:
            lay.addWidget(w)
    return lay


class RunBar(QWidget):
    """Save / Run / Stop row shared by the task pages."""

    save_requested = Signal()
    run_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.save_btn = QPushButton("Save")
        self.run_btn = QPushButton("Save & Run")
        self.run_btn.setObjectName("primary")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        lay.addWidget(self.save_btn)
        lay.addWidget(self.run_btn)
        lay.addStretch(1)
        lay.addWidget(self.stop_btn)
        self.save_btn.clicked.connect(self.save_requested)
        self.run_btn.clicked.connect(self.run_requested)

    def set_running(self, running: bool):
        self.save_btn.setEnabled(not running)
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
