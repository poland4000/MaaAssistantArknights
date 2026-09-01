"""WPF-style per-task settings panels for the Farming tab's middle column.

Each panel mirrors the matching MaaWpfGui UserControl (Recruit / Fight /
Infrast / Mall / Award / Roguelike / StartUp) in a narrow (~250px) column,
with a General/Advanced split where the WPF has one. Panels own their state
(persisted via QSettings) and produce maa-cli task params.
"""

from __future__ import annotations

import json

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from maagui.pages.roguelike import MODES, ROLES, SQUADS, THEMES, _load_operators

from . import theme
from .wpfwidgets import CheckCombo

CLIENTS = ["Official", "Bilibili", "Txwy", "YoStarEN", "YoStarJP", "YoStarKR"]

DRONES = [
    ("NotUse", "No use"),
    ("Money", "LMD (Trade)"),
    ("Soc", "Combat Record (Mfg)"),
    ("Combat", "Pure Gold (Mfg)"),
]

RECRUIT_STRATEGIES = [
    "Additional Tags are not selected by default",
    "Only select additional Tags",
    "Select default and additional Tags",
]


def vlay(spacing: int = 8) -> QVBoxLayout:
    lay = QVBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    return lay


def field_row(label: str, widget, tip: str = "") -> QWidget:
    """Small dim label above an input — the HandyControl `Title` look."""
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


def check_row(text: str, tip: str = "") -> QCheckBox:
    cb = QCheckBox(text)
    if tip:
        cb.setToolTip(tip)
    return cb


def hpair(left: QWidget, right: QWidget, stretch_left: bool = True) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lay.addWidget(left, 1 if stretch_left else 0)
    lay.addWidget(right, 0 if stretch_left else 1)
    return w


def time_pair(hour: QSpinBox, minute: QSpinBox) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    colon = QLabel(":")
    colon.setStyleSheet(f"color: {theme.TEXT_DIM};")
    for s in (hour, minute):
        s.setFixedWidth(48)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    lay.addWidget(hour)
    lay.addWidget(colon)
    lay.addWidget(minute)
    lay.addStretch(1)
    return w


def hmspin(value: int = 9, maximum: int = 9) -> QSpinBox:
    s = QSpinBox()
    s.setRange(1 if maximum <= 9 else 0, maximum)
    s.setValue(value)
    s.setFixedWidth(48)
    s.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return s


class TaskPanel(QScrollArea):
    """Base: a scrollable narrow column with an optional General/Advanced split."""

    #: QSettings prefix, e.g. "farming/recruit"
    PREFIX = ""
    HAS_ADVANCED = False

    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._body = QWidget()
        self._body.setObjectName("pageRoot")
        self._lay = vlay(10)
        self._body.setLayout(self._lay)
        self.setWidget(self._body)

        self._general_box = QWidget()
        self._general_box.setObjectName("pageRoot")
        self._general = vlay(10)
        self._general_box.setLayout(self._general)
        self._lay.addWidget(self._general_box)

        self._advanced_box = QWidget()
        self._advanced_box.setObjectName("pageRoot")
        self._advanced = vlay(10)
        self._advanced_box.setLayout(self._advanced)
        self._lay.addWidget(self._advanced_box)
        self._advanced_box.hide()

        self.build_general()
        self.build_advanced()
        self.load()

    # subclasses override these ------------------------------------------------
    def build_general(self): ...
    def build_advanced(self): ...

    def set_show_advanced(self, show: bool):
        self._general_box.setVisible(not show)
        self._advanced_box.setVisible(show)

    # --- persistence ------------------------------------------------------------
    def save(self):
        for key, getter in [(k, c) for k, c, _ in self._bind()]:
            self.settings.setValue(f"{self.PREFIX}/{key}", getter)
        self.settings.sync()

    def load(self):
        for key, current, setter in self._bind():
            val = self.settings.value(f"{self.PREFIX}/{key}", None)
            if val is not None:
                setter(self._coerce(current, val))

    @staticmethod
    def _coerce(current, val):
        if isinstance(current, bool):
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("1", "true", "yes", "on")
        if isinstance(current, (int, float)) and not isinstance(current, bool):
            try:
                return type(current)(val)
            except (TypeError, ValueError):
                return current
        return str(val)

    # to be provided by subclasses -----------------------------------------------
    def _bind(self):
        """[(key, current_value, setter)] used by save/load."""
        return []

    def params(self) -> dict:
        return {}


class StartUpPanel(TaskPanel):
    """Login (StartUp): client type + the Linux launch/close game extras."""

    PREFIX = "farming/startup"

    def build_general(self):
        self.client = QComboBox()
        self.client.addItems(CLIENTS)
        prof_client = self.settings.value("farming/client", "")
        self.client.setCurrentText(prof_client if prof_client in CLIENTS else "YoStarEN")
        self._lay.addWidget(field_row(
            "Client type", self.client,
            "Which game client to launch / log into (Official = CN, YoStar* = EN/JP/KR, Txwy = TW)"))
        launch_hint = QLabel("MAA opens the client before logging in when it is not running.")
        launch_hint.setWordWrap(True)
        launch_hint.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
        self._general.addWidget(launch_hint)
        self._general.addStretch(1)

    def build_advanced(self):
        pass

    def _bind(self):
        return [("client", self.client.currentText(), self.client.setCurrentText)]

    def params(self) -> dict:
        return {"client_type": self.client.currentText(), "start_game_enabled": True}


class RecruitPanel(TaskPanel):
    """Auto Recruit — WPF RecruitSettingsUserControl (General + Advanced)."""

    PREFIX = "farming/recruit"
    HAS_ADVANCED = True

    def build_general(self):
        self.expedited = check_row(
            "Auto use Expedited Plan*", "Use an Expedited Plan to finish recruitment instantly")
        self._general.addWidget(self.expedited)

        self.max_times = QSpinBox()
        self.max_times.setRange(0, 99)
        self.max_times.setValue(4)
        self._general.addWidget(field_row(
            "Recruit max times", self.max_times, "Stop after this many recruitments (0 = unlimited)"))

        # Auto select 3★/4★/5★/6★ (the WPF General tab "Auto confirm N★" rows)
        self.sel3 = check_row("Auto select 3★ Tags")
        self.sel4 = check_row("Auto select 4★ Tags")
        self.sel5 = check_row("Auto select 5★ Tags")
        self.sel6 = check_row("Auto select 6★ Tags",
                              "This option can only be enabled by editing the config file")
        self.sel6.setEnabled(False)

        self.h3, self.m3 = hmspin(9), QSpinBox()
        self.m3.setRange(0, 50); self.m3.setValue(0); self.m3.setSingleStep(10)
        self.h4, self.m4 = hmspin(9), QSpinBox()
        self.m4.setRange(0, 50); self.m4.setValue(0); self.m4.setSingleStep(10)
        fixed = QLabel("09:00")
        fixed.setStyleSheet(f"color: {theme.TEXT_DIM};")

        for cb, tp in ((self.sel3, time_pair(self.h3, self.m3)),
                       (self.sel4, time_pair(self.h4, self.m4)),
                       (self.sel5, fixed)):
            self._general.addWidget(cb)
            tp.setContentsMargins(18, 0, 0, 0)
            self._general.addWidget(tp)
        self._general.addWidget(self.sel6)

        self.sel3.setChecked(True)
        self.sel4.setChecked(True)
        self.sel5.setChecked(True)
        self._general.addStretch(1)

    def build_advanced(self):
        self.strategy = QComboBox()
        self.strategy.addItems(RECRUIT_STRATEGIES)
        self._advanced.addWidget(field_row(
            "Strategies for Additional Tags", self.strategy,
            "What to do when more than three Tags appear"))

        self.refresh3 = check_row("Auto refresh 3★ Tags",
                                  "Refresh new Tags until 4★+ appear (uses one permit per refresh)")
        self._advanced.addWidget(self.refresh3)

        self.force_refresh = check_row(
            "Continue trying to refresh Tags without recruitment permit",
            "Keep refreshing even after running out of permits")
        self.force_refresh.setEnabled(False)
        self._advanced.addWidget(self.force_refresh)
        self.refresh3.toggled.connect(self.force_refresh.setEnabled)

        self.short_time = check_row("Set 7:40 instead of 9:00 for 3★ Tags")
        self.very_short_time = check_row("Set 1:00 instead of 9:00 for 3★ Tags")
        self._advanced.addWidget(self.short_time)
        self._advanced.addWidget(self.very_short_time)
        self.short_time.toggled.connect(
            lambda on: on and self.very_short_time.setChecked(False))
        self.very_short_time.toggled.connect(
            lambda on: on and self.short_time.setChecked(False))

        self.robot = check_row(
            "Manually confirm Robot tag",
            "Keep the slot untouched when the Support Robot tag is identified")
        self._advanced.addWidget(self.robot)

        self._advanced.addSpacing(6)
        self.confirm3 = check_row("Auto confirm 3★")
        self.confirm4 = check_row("Auto confirm 4★")
        self.confirm5 = check_row("Auto confirm 5★")
        self.confirm3.setChecked(True)
        self.confirm4.setChecked(True)
        self.confirm5.setChecked(True)
        for cb in (self.confirm3, self.confirm4, self.confirm5):
            self._advanced.addWidget(cb)
        self._advanced.addStretch(1)

    def _bind(self):
        return [
            ("expedited", self.expedited.isChecked(), self.expedited.setChecked),
            ("max_times", self.max_times.value(), self.max_times.setValue),
            ("sel3", self.sel3.isChecked(), self.sel3.setChecked),
            ("sel4", self.sel4.isChecked(), self.sel4.setChecked),
            ("sel5", self.sel5.isChecked(), self.sel5.setChecked),
            ("h3", self.h3.value(), self.h3.setValue),
            ("m3", self.m3.value(), self.m3.setValue),
            ("h4", self.h4.value(), self.h4.setValue),
            ("m4", self.m4.value(), self.m4.setValue),
            ("strategy", self.strategy.currentIndex(), self.strategy.setCurrentIndex),
            ("refresh3", self.refresh3.isChecked(), self.refresh3.setChecked),
            ("force_refresh", self.force_refresh.isChecked(), self.force_refresh.setChecked),
            ("short_time", self.short_time.isChecked(), self.short_time.setChecked),
            ("very_short_time", self.very_short_time.isChecked(), self.very_short_time.setChecked),
            ("robot", self.robot.isChecked(), self.robot.setChecked),
            ("confirm3", self.confirm3.isChecked(), self.confirm3.setChecked),
            ("confirm4", self.confirm4.isChecked(), self.confirm4.setChecked),
            ("confirm5", self.confirm5.isChecked(), self.confirm5.setChecked),
        ]

    def params(self) -> dict:
        select = [3 + i for i, on in enumerate(
            (self.sel3.isChecked(), self.sel4.isChecked(), self.sel5.isChecked(),
             self.sel6.isChecked())) if on]
        confirm = [3 + i for i, on in enumerate(
            (self.confirm3.isChecked(), self.confirm4.isChecked(), self.confirm5.isChecked()))
            if on]
        if self.sel6.isChecked() and 6 not in confirm:
            confirm.append(6)
        params: dict = {"select": select, "confirm": confirm}
        if self.max_times.value():
            params["times"] = self.max_times.value()
        if self.expedited.isChecked():
            params["expedite"] = True
        params["extra_tags_mode"] = self.strategy.currentIndex()
        if self.refresh3.isChecked():
            params["refresh"] = True
            if self.force_refresh.isChecked():
                params["force_refresh"] = True
        if self.short_time.isChecked() or self.very_short_time.isChecked():
            # MaaCore wants per-level minutes: {"3": 460} = 7:40 for 3★ slots
            params["set_time"] = True
            params["recruitment_time"] = {
                "3": 60 if self.very_short_time.isChecked() else 460
            }
        if self.robot.isChecked():
            params["preserve_tags"] = ["\u652f\u63f4\u673a\u68b0"]
        return params


class FightPanel(TaskPanel):
    """Combat — WPF FightSettingsUserControl (General + Advanced)."""

    PREFIX = "farming/fight"
    HAS_ADVANCED = True

    SERIES = ["Auto", "1", "2", "3", "4", "5", "6"]

    def build_general(self):
        grid_w = QWidget()
        grid_w.setObjectName("pageRoot")
        grid = self._grid()
        grid_w.setLayout(grid)
        self.medicine_on = check_row("Use sanity potion")
        self.stone_on = check_row("Use originite prime*")
        self.times_on = check_row("Perform battles")
        self.medicine = hmspin(0, 999); self.medicine.setRange(0, 999)
        self.stone = QSpinBox(); self.stone.setRange(0, 999)
        self.times = QSpinBox(); self.times.setRange(0, 999)
        for s in (self.medicine, self.stone, self.times):
            s.setFixedWidth(64)
        grid.addWidget(self.medicine_on, 0, 0)
        grid.addWidget(self.medicine, 0, 1)
        grid.addWidget(self.stone_on, 1, 0)
        grid.addWidget(self.stone, 1, 1)
        grid.addWidget(self.times_on, 2, 0)
        grid.addWidget(self.times, 2, 1)
        self._general.addWidget(grid_w)

        self.series = QComboBox()
        self.series.addItems(self.SERIES)
        self._general.addWidget(field_row(
            "Series (proxy plan)", self.series,
            "Use N sanity potions at once per run when the plan allows"))

        self.stage = QComboBox()
        self.stage.setEditable(True)
        self.stage.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.stage.lineEdit().setPlaceholderText("e.g. 1-7 / CE-6 (empty = current)")
        self._general.addWidget(field_row(
            "Stage select", self.stage,
            "Leave empty to repeat the last stage; pick one of today's open "
            "stages from the list below the settings"))

        self.drops = QLineEdit()
        self.drops.setPlaceholderText("e.g. 30012=100, 30011=50")
        self._general.addWidget(field_row(
            "Exit after drops (itemID=count)", self.drops,
            "Stop the stage once these drop counts are reached"))

        self._general.addStretch(1)

    def build_advanced(self):
        self.expiring = QSpinBox()
        self.expiring.setRange(0, 999)
        self._advanced.addWidget(field_row(
            "Expiring sanity potion", self.expiring,
            "Use potions that are about to expire first (0 = don't use)"))
        self.penguin = check_row("Report to Penguin Statistics")
        self._advanced.addWidget(self.penguin)
        self.penguin_id = QLineEdit()
        self.penguin_id.setPlaceholderText("Penguin ID (optional)")
        self._advanced.addWidget(field_row("", self.penguin_id))
        self.yituliu = check_row("Report to Yituliu")
        self._advanced.addWidget(self.yituliu)
        self.yituliu_id = QLineEdit()
        self.yituliu_id.setPlaceholderText("Yituliu ID (optional)")
        self._advanced.addWidget(field_row("", self.yituliu_id))
        self._advanced.addStretch(1)

    @staticmethod
    def _grid() -> QGridLayout:
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        return g

    def _bind(self):
        return [
            ("medicine_on", self.medicine_on.isChecked(), self.medicine_on.setChecked),
            ("medicine", self.medicine.value(), self.medicine.setValue),
            ("stone_on", self.stone_on.isChecked(), self.stone_on.setChecked),
            ("stone", self.stone.value(), self.stone.setValue),
            ("times_on", self.times_on.isChecked(), self.times_on.setChecked),
            ("times", self.times.value(), self.times.setValue),
            ("series", self.series.currentIndex(), self.series.setCurrentIndex),
            ("stage", self.stage.currentText(), self.stage.setCurrentText),
            ("drops", self.drops.text(), self.drops.setText),
            ("expiring", self.expiring.value(), self.expiring.setValue),
            ("penguin", self.penguin.isChecked(), self.penguin.setChecked),
            ("penguin_id", self.penguin_id.text(), self.penguin_id.setText),
            ("yituliu", self.yituliu.isChecked(), self.yituliu.setChecked),
            ("yituliu_id", self.yituliu_id.text(), self.yituliu_id.setText),
        ]

    def params(self) -> dict:
        params: dict = {}
        stage = self.stage.currentText().strip()
        if stage:
            params["stage"] = stage
        if self.medicine_on.isChecked() and self.medicine.value():
            params["medicine"] = self.medicine.value()
        if self.expiring.value():
            params["expiring_medicine"] = self.expiring.value()
        if self.stone_on.isChecked() and self.stone.value():
            params["stone"] = self.stone.value()
        if self.times_on.isChecked() and self.times.value():
            params["times"] = self.times.value()
        if self.series.currentIndex() > 0:
            params["series"] = self.series.currentIndex()
        if self.drops.text().strip():
            drops: dict[str, int] = {}
            for part in self.drops.text().split(","):
                k, _, v = part.partition("=")
                try:
                    drops[k.strip()] = int(v.strip())
                except ValueError:
                    continue
            if drops:
                params["drops"] = drops
        if self.penguin.isChecked():
            params["report_to_penguin"] = True
            if self.penguin_id.text().strip():
                params["penguin_id"] = self.penguin_id.text().strip()
        if self.yituliu.isChecked():
            params["report_to_yituliu"] = True
            if self.yituliu_id.text().strip():
                params["yituliu_id"] = self.yituliu_id.text().strip()
        return params


class InfrastPanel(TaskPanel):
    """Base — WPF InfrastSettingsUserControl."""

    PREFIX = "farming/infrast"

    FACILITIES = ["Mfg", "Trade", "Power", "Control", "Reception", "Office", "Dorm"]

    def build_general(self):
        self.facilities = CheckCombo(
            self.FACILITIES, placeholder="All facilities")
        self.facilities.set_checked(self.FACILITIES)
        self._general.addWidget(field_row(
            "Facilities to manage", self.facilities,
            "Which base facilities MAA shifts staff around in"))

        self.drones = QComboBox()
        for value, label in DRONES:
            self.drones.addItem(label, value)
        self._general.addWidget(field_row(
            "Drones usage", self.drones, "Spend breakpoint drones on…"))

        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.0, 1.0)
        self.threshold.setSingleStep(0.05)
        self.threshold.setValue(0.3)
        self._general.addWidget(field_row(
            "Morale threshold (working until)", self.threshold,
            "Operators are moved to dorms when morale drops below this"))

        self.replenish = check_row("Replenish trade orders / manufacturing")
        self.replenish.setChecked(True)
        self._general.addWidget(self.replenish)
        self._general.addStretch(1)

    def build_advanced(self):
        self.dorm_trust = check_row("Fill dorms by trust preference")
        self.dorm_notstationed = check_row("Not station assigned operators to dorms")
        self._advanced.addWidget(self.dorm_trust)
        self._advanced.addWidget(self.dorm_notstationed)
        self.plan_file = QLineEdit()
        self.plan_file.setPlaceholderText("custom plan JSON (relative to config dir)")
        self._advanced.addWidget(field_row("Custom plan (layout) file", self.plan_file))
        self.plan_index = QSpinBox()
        self.plan_index.setRange(0, 99)
        self._advanced.addWidget(field_row("Plan index", self.plan_index))
        self._advanced.addStretch(1)

    def _bind(self):
        return [
            ("facilities", json.dumps(self.facilities.checked_items()),
             lambda v: self.facilities.set_checked(json.loads(v))),
            ("drones", self.drones.currentData(), self._set_drones),
            ("threshold", self.threshold.value(), self.threshold.setValue),
            ("replenish", self.replenish.isChecked(), self.replenish.setChecked),
            ("dorm_trust", self.dorm_trust.isChecked(), self.dorm_trust.setChecked),
            ("dorm_notstationed", self.dorm_notstationed.isChecked(),
             self.dorm_notstationed.setChecked),
            ("plan_file", self.plan_file.text(), self.plan_file.setText),
            ("plan_index", self.plan_index.value(), self.plan_index.setValue),
        ]

    def _set_drones(self, value):
        idx = self.drones.findData(str(value))
        if idx >= 0:
            self.drones.setCurrentIndex(idx)

    def params(self) -> dict:
        facilities = self.facilities.checked_items() or self.FACILITIES
        params: dict = {
            "facility": facilities,
            "mode": 0,
            "drones": self.drones.currentData() or "NotUse",
            "threshold": round(self.threshold.value(), 2),
            "replenish": self.replenish.isChecked(),
            "dorm_trust_enabled": self.dorm_trust.isChecked(),
            "dorm_notstationed_enabled": self.dorm_notstationed.isChecked(),
        }
        plan = self.plan_file.text().strip()
        if plan:
            params["mode"] = 10000
            params["filename"] = plan
            params["plan_index"] = self.plan_index.value()
        return params


class MallPanel(TaskPanel):
    """Credit Store — WPF MallSettingsUserControl."""

    PREFIX = "farming/mall"

    def build_general(self):
        self.shopping = check_row("Perform shopping")
        self.shopping.setChecked(True)
        self._general.addWidget(self.shopping)
        self.buy_first = QLineEdit()
        self.buy_first.setPlaceholderText("item names, comma-separated")
        self._general.addWidget(field_row(
            "Buy first (priority)", self.buy_first))
        self.blacklist = QLineEdit()
        self.blacklist.setPlaceholderText("item names, comma-separated")
        self._general.addWidget(field_row("Blacklist", self.blacklist))
        self.credit_fight = check_row(
            "Perform the credit fight stage (visiting friends combat)",
            "Run CE-… once with support units for +20 credits when available")
        self._general.addWidget(self.credit_fight)
        self._general.addStretch(1)

    def build_advanced(self):
        self.discount = check_row("Only buy discounted items")
        self.discount.setChecked(True)
        self.force = check_row("Force shopping if credit is full")
        self._advanced.addWidget(self.discount)
        self._advanced.addWidget(self.force)
        self._advanced.addStretch(1)

    def _bind(self):
        return [
            ("shopping", self.shopping.isChecked(), self.shopping.setChecked),
            ("buy_first", self.buy_first.text(), self.buy_first.setText),
            ("blacklist", self.blacklist.text(), self.blacklist.setText),
            ("credit_fight", self.credit_fight.isChecked(), self.credit_fight.setChecked),
            ("discount", self.discount.isChecked(), self.discount.setChecked),
            ("force", self.force.isChecked(), self.force.setChecked),
        ]

    @staticmethod
    def _split(text: str) -> list[str]:
        return [t.strip() for t in text.split(",") if t.strip()]

    def params(self) -> dict:
        params: dict = {"shopping": self.shopping.isChecked()}
        if self.buy_first.text().strip():
            params["buy_first"] = self._split(self.buy_first.text())
        if self.blacklist.text().strip():
            params["blacklist"] = self._split(self.blacklist.text())
        params["credit_fight"] = self.credit_fight.isChecked()
        params["only_buy_discount"] = self.discount.isChecked()
        params["force_shopping_if_credit_full"] = self.force.isChecked()
        return params


class AwardPanel(TaskPanel):
    """Collect Rewards — WPF AwardSettingsUserControl."""

    PREFIX = "farming/award"

    def build_general(self):
        self.daily = check_row("Daily & weekly rewards")
        self.mail = check_row("Mail")
        self.recruit = check_row("Recruit rewards (limited-time)")
        self.orundum = check_row("Orundum (daily delivery)",
                                 "Claim the daily Orundum delivery on the home screen")
        self.mining = check_row("Limited mining permits")
        self.special = check_row("Special access passes")
        self.daily.setChecked(True)
        self.mail.setChecked(True)
        for cb in (self.daily, self.mail, self.recruit, self.orundum,
                   self.mining, self.special):
            self._general.addWidget(cb)
        self._general.addStretch(1)

    def build_advanced(self):
        pass

    def _bind(self):
        return [
            ("daily", self.daily.isChecked(), self.daily.setChecked),
            ("mail", self.mail.isChecked(), self.mail.setChecked),
            ("recruit", self.recruit.isChecked(), self.recruit.setChecked),
            ("orundum", self.orundum.isChecked(), self.orundum.setChecked),
            ("mining", self.mining.isChecked(), self.mining.setChecked),
            ("special", self.special.isChecked(), self.special.setChecked),
        ]

    def params(self) -> dict:
        return {
            "award": self.daily.isChecked(),
            "mail": self.mail.isChecked(),
            "recruit": self.recruit.isChecked(),
            "orundum": self.orundum.isChecked(),
            "mining": self.mining.isChecked(),
            "specialaccess": self.special.isChecked(),
        }


class RoguelikePanel(TaskPanel):
    """Auto I.S. — WPF RoguelikeSettingsUserControl."""

    PREFIX = "farming/roguelike"
    HAS_ADVANCED = True

    def build_general(self):
        self.theme_cb = QComboBox()
        self.theme_cb.addItems(THEMES)
        self.theme_cb.currentTextChanged.connect(self._refresh_modes)
        self._general.addWidget(field_row("Theme", self.theme_cb))

        self.mode = QComboBox()
        self._general.addWidget(field_row("Strategy", self.mode))

        self.squad = QComboBox()
        self.squad.addItems([label for label, _ in SQUADS])
        self._general.addWidget(field_row("Squad", self.squad))

        self.roles = QComboBox()
        self.roles.addItems([label for label, _ in ROLES])
        self._general.addWidget(field_row("Roles group", self.roles))

        self.core_char = QComboBox()
        self.core_char.setEditable(True)
        self.core_char.addItem("")  # allow empty = no preference
        self.core_char.addItems(_load_operators())
        self.core_char.setCurrentIndex(0)
        self._general.addWidget(field_row(
            "Core operator (first choice)", self.core_char))

        self.use_support = check_row("Take the core operator as support")
        self.use_nonfriend = check_row("Allow non-friend support units")
        self._general.addWidget(self.use_support)
        self._general.addWidget(self.use_nonfriend)

        self.starts = QSpinBox()
        self.starts.setRange(0, 9999)
        self.starts.setValue(1)
        self._general.addWidget(field_row("Runs (starts)", self.starts))

        self.investment = check_row("Invest at the trader")
        self.investment.setChecked(True)
        self._general.addWidget(self.investment)

        self.invest_count = QSpinBox()
        self.invest_count.setRange(0, 9999)
        self._general.addWidget(field_row("Investment count (0 = unlimited)", self.invest_count))

        self.stop_full = check_row("Stop when investment is full")
        self._general.addWidget(self.stop_full)
        self._general.addStretch(1)
        self._refresh_modes()

    def build_advanced(self):
        self.difficulty = QSpinBox()
        self.difficulty.setRange(0, 20)
        self._advanced.addWidget(field_row(
            "Difficulty (0 = client default)", self.difficulty))
        self.stop_max_level = QSpinBox()
        self.stop_max_level.setRange(0, 120)
        self._advanced.addWidget(field_row(
            "Stop at max level (0 = off)", self.stop_max_level))
        self.stop_boss = check_row("Stop before the final boss")
        self.dice = check_row("Refresh the trader with dice")
        self.start_e2 = check_row("Start with E2 (collectible mode)")
        self.only_e2 = check_row("Only start with E2")
        for cb in (self.stop_boss, self.dice, self.start_e2, self.only_e2):
            self._advanced.addWidget(cb)
        self._advanced.addStretch(1)

    def _refresh_modes(self):
        t = self.theme_cb.currentText()
        self.mode.blockSignals(True)
        self.mode.clear()
        for value, label, themes in MODES:
            if themes is None or t in themes:
                self.mode.addItem(label, value)
        self.mode.blockSignals(False)

    def _bind(self):
        return [
            ("theme", self.theme_cb.currentText(), self.theme_cb.setCurrentText),
            ("mode", self.mode.currentData(), self._set_mode),
            ("squad", self.squad.currentIndex(), self.squad.setCurrentIndex),
            ("roles", self.roles.currentIndex(), self.roles.setCurrentIndex),
            ("core_char", self.core_char.currentText(), self.core_char.setCurrentText),
            ("use_support", self.use_support.isChecked(), self.use_support.setChecked),
            ("use_nonfriend", self.use_nonfriend.isChecked(), self.use_nonfriend.setChecked),
            ("starts", self.starts.value(), self.starts.setValue),
            ("investment", self.investment.isChecked(), self.investment.setChecked),
            ("invest_count", self.invest_count.value(), self.invest_count.setValue),
            ("stop_full", self.stop_full.isChecked(), self.stop_full.setChecked),
            ("difficulty", self.difficulty.value(), self.difficulty.setValue),
            ("stop_max_level", self.stop_max_level.value(), self.stop_max_level.setValue),
            ("stop_boss", self.stop_boss.isChecked(), self.stop_boss.setChecked),
            ("dice", self.dice.isChecked(), self.dice.setChecked),
            ("start_e2", self.start_e2.isChecked(), self.start_e2.setChecked),
            ("only_e2", self.only_e2.isChecked(), self.only_e2.setChecked),
        ]

    def _set_mode(self, value):
        try:
            idx = self.mode.findData(int(value))
        except (TypeError, ValueError):
            return
        if idx >= 0:
            self.mode.setCurrentIndex(idx)

    def params(self) -> dict:
        params: dict = {"theme": self.theme_cb.currentText()}
        params["mode"] = self.mode.currentData() if self.mode.currentData() is not None else 0
        if self.difficulty.value():
            params["difficulty"] = self.difficulty.value()
        squad = SQUADS[self.squad.currentIndex()][1] if 0 <= self.squad.currentIndex() < len(SQUADS) else ""
        if squad:
            params["squad"] = squad
        roles = ROLES[self.roles.currentIndex()][1] if 0 <= self.roles.currentIndex() < len(ROLES) else ""
        if roles:
            params["roles"] = roles
        if self.core_char.currentText().strip():
            params["core_char"] = self.core_char.currentText().strip()
        params["use_support"] = self.use_support.isChecked()
        params["use_nonfriend_support"] = self.use_nonfriend.isChecked()
        params["starts_count"] = self.starts.value()
        params["investment_enabled"] = self.investment.isChecked()
        if self.invest_count.value():
            params["investments_count"] = self.invest_count.value()
        params["stop_when_investment_full"] = self.stop_full.isChecked()
        if self.stop_max_level.value():
            params["stop_at_max_level"] = self.stop_max_level.value()
        params["stop_at_final_boss"] = self.stop_boss.isChecked()
        params["refresh_trader_with_dice"] = self.dice.isChecked()
        params["start_with_elite_two"] = self.start_e2.isChecked()
        params["only_start_with_elite_two"] = self.only_e2.isChecked()
        return params
