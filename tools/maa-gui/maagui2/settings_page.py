"""Settings page — Windows-MAA style vertical tab list with embedded panels."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import theme


def _wrap(panel: QWidget, title: str, subtitle: str = "") -> QWidget:
    """Scrollable host with a heading, so embedded panels match the new style."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    body = QWidget()
    body.setObjectName("pageRoot")
    lay = QVBoxLayout(body)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(12)
    head = QLabel(title)
    head.setStyleSheet("font-size: 20px; font-weight: 800;")
    lay.addWidget(head)
    if subtitle:
        sub = QLabel(subtitle)
        sub.setStyleSheet(f"color: {theme.TEXT_DIM};")
        lay.addWidget(sub)
        sub.setWordWrap(True)
    lay.addWidget(panel)
    # Panels lifted out of a QTabWidget keep their hidden flag (QTabWidget hides
    # non-current pages); a hidden child is skipped by the new layout entirely.
    panel.show()
    scroll.setWidget(body)
    return scroll


def _perf_panel() -> QWidget:
    """Fight screencap interval knob (writes the platform_diff/pc override)."""
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpinBox

    from . import perf

    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setSpacing(10)

    note = QLabel(
        "MAA's battle loop polls as fast as the controller allows. ADB screencaps\n"
        "take 100-500ms and throttle it naturally; the X11 window capture takes\n"
        "~10ms, so without an interval the loop runs at ~60fps and burns a core\n"
        "(Windows + MuMu gets the same effect from fast captures, but its capture\n"
        "and resize are GPU/compositor-side and much cheaper per frame).\n\n"
        "Lower = more responsive skill timing (needed by some precise copilot/\n"
        "SSS missions) but more CPU. 0 disables throttling (upstream default).")
    note.setWordWrap(True)
    note.setStyleSheet(f"color: {theme.TEXT_DIM};")
    lay.addWidget(note)

    row = QHBoxLayout()
    row.addWidget(QLabel("Fight screencap interval (ms)"))
    spin = QSpinBox()
    spin.setRange(0, 1000)
    current = perf.get_interval()
    spin.setValue(current if current is not None else perf.DEFAULT_INTERVAL_MS)
    status = QLabel("")
    status.setStyleSheet(f"color: {theme.TEXT_DIM};")

    def apply():
        perf.set_interval(spin.value())
        fps = "unlimited" if spin.value() == 0 else f"~{1000 // max(spin.value(), 1)} fps"
        status.setText(f"saved — {spin.value()} ms ({fps}); takes effect on the next run")

    spin.valueChanged.connect(lambda _: apply())
    apply()
    row.addWidget(spin)
    row.addWidget(status)
    row.addStretch(1)
    lay.addLayout(row)
    lay.addStretch(1)
    return w


class SettingsPage(QWidget):
    """Vertical tabs on the left, embedded configuration panels on the right."""

    TABS = [
        ("game",      "Game",          "Connection & client"),
        ("fight",     "Fight",         "Stage farming"),
        ("infrast",   "Infrast",       "Base shifts"),
        ("recruit",   "Recruit",       "Auto recruitment"),
        ("mall",      "Mall",          "Credit store"),
        ("award",     "Award",         "Daily rewards"),
        ("roguelike", "Roguelike",     "Integrated Strategies"),
        ("perf",      "Performance",   "Screencap throttling"),
    ]

    def __init__(self, connections_page, fight_page, daily_page, roguelike_page, parent=None):
        super().__init__(parent)
        self._tabs_by_key: dict[str, int] = {}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        self.tabs = QListWidget()
        self.tabs.setObjectName("settingsTabs")
        self.tabs.setFixedWidth(180)
        outer.addWidget(self.tabs)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        panels = {
            "game": _wrap(connections_page, "Game", "Window / client connection settings"),
            "fight": _wrap(fight_page, "Fight", "Stage, repeats, and medicine use"),
            "infrast": _wrap(daily_page.infrast_panel(), "Infrast", "Facilities, drones, shifts"),
            "recruit": _wrap(daily_page.recruit_panel(), "Recruit", "Slots, permits, tag refresh"),
            "mall": _wrap(daily_page.mall_panel(), "Mall", "Credit store shopping"),
            "award": _wrap(daily_page.award_panel(), "Award", "Daily and weekly rewards"),
            "roguelike": _wrap(roguelike_page, "Roguelike", "Theme, strategy, squad, operator"),
            "perf": _wrap(_perf_panel(), "Performance", "Battle-loop screencap throttling"),
        }
        for i, (key, label, _sub) in enumerate(self.TABS):
            self.tabs.addItem(QListWidgetItem(label))
            self.stack.addWidget(panels[key])
            self._tabs_by_key[key] = i
        self.tabs.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.tabs.setCurrentRow(0)

    def open_tab(self, key: str):
        if key in self._tabs_by_key:
            self.tabs.setCurrentRow(self._tabs_by_key[key])
