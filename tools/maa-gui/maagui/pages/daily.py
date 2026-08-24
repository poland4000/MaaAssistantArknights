"""Daily page (日常): Infrast, Recruit, Mall, Award settings.

Saves to `__gui_daily` — the same task file the One-Click Daily page builds.
The dashboard overwrites it with its selected routine; here "Save & Run" runs
the four daily subtasks directly.
"""

from __future__ import annotations

import tomllib

from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import maa
from ..runner import TaskRunner
from ..state import AppState
from ..widgets import (
    RunBar,
    bool_field,
    combo_field,
    dspin_field,
    FieldRow,
    spin_field,
    text_field,
)

TASK_FILE = maa.GUI_PREFIX + "daily"

FACILITIES = ["Mfg", "Trade", "Power", "Control", "Reception", "Office", "Dorm"]
DRONES = ["NotUse", "Money", "Soc", "Combat"]


class DailyPage(QWidget):
    def __init__(self, runner: TaskRunner, state: AppState, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Daily — 日常 (基建 / 公招 / 商店 / 奖励)")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        self._panels: dict[str, QWidget] = {
            "infrast": self._build_infrast(),
            "recruit": self._build_recruit(),
            "mall": self._build_mall(),
            "award": self._build_award(),
        }
        tabs = QTabWidget()
        for key, label in (("infrast", "Infrast 基建换班"), ("recruit", "Recruit 公招"),
                           ("mall", "Mall 商店"), ("award", "Award 奖励")):
            tabs.addTab(self._panels[key], label)
        outer.addWidget(tabs, 1)

        self.bar = RunBar()
        self.bar.save_requested.connect(self.save)
        self.bar.run_requested.connect(self.save_and_run)
        self.bar.stop_btn.clicked.connect(self.runner.stop)
        outer.addWidget(self.bar)

        self.runner.running_changed.connect(self.bar.set_running)
        self._load()

    # Accessors so alternate frontends (e.g. maagui2) can lift the panels
    # out of this page's tab widget.
    def infrast_panel(self) -> QWidget:
        return self._panels["infrast"]

    def recruit_panel(self) -> QWidget:
        return self._panels["recruit"]

    def mall_panel(self) -> QWidget:
        return self._panels["mall"]

    def award_panel(self) -> QWidget:
        return self._panels["award"]

    # ------------------------------------------------------------------ Infrast

    def _build_infrast(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(12, 12, 12, 12)

        self.facility_checks: dict[str, QCheckBox] = {}
        fac_row = QHBoxLayout()
        fac_row.setSpacing(14)
        for name in FACILITIES:
            cb = QCheckBox(name)
            cb.setChecked(True)
            self.facility_checks[name] = cb
            fac_row.addWidget(cb)
        fac_row.addStretch(1)
        grid.addWidget(FieldRow("Facilities to manage", fac_row), 0, 0, 1, 2)

        self.drones = combo_field(DRONES)
        grid.addWidget(FieldRow("Drones usage", self.drones), 1, 0)

        self.threshold = dspin_field(0.3, 0.0, 1.0)
        grid.addWidget(FieldRow("Morale threshold", self.threshold), 1, 1)

        self.replenish = bool_field(True)
        grid.addWidget(FieldRow("Replenish (补货)", self.replenish), 1, 2)

        self.dorm_trust = bool_field()
        grid.addWidget(FieldRow("Dorm trust", self.dorm_trust), 2, 0)

        self.dorm_notstationed = bool_field()
        grid.addWidget(FieldRow("Dorm non-stationed", self.dorm_notstationed), 2, 1)

        self.plan_file = text_field("", "infrast plan JSON (relative to config dir)")
        grid.addWidget(FieldRow("Custom plan file", self.plan_file), 2, 2)

        self.plan_index = spin_field(0, 0, 99)
        grid.addWidget(FieldRow("Plan index", self.plan_index), 3, 0)

        return w

    def infrast_params(self) -> dict:
        params = {
            "facility": [n for n, cb in self.facility_checks.items() if cb.isChecked()],
        }
        plan = self.plan_file.text().strip()
        # mode 10000 (custom plan) only makes sense with a plan file;
        # otherwise use the default shift mode
        params["mode"] = 10000 if plan else 0
        params["drones"] = self.drones.currentText()
        params["threshold"] = round(self.threshold.value(), 2)
        params["replenish"] = self.replenish.isChecked()
        params["dorm_trust_enabled"] = self.dorm_trust.isChecked()
        params["dorm_notstationed_enabled"] = self.dorm_notstationed.isChecked()
        if plan:
            params["filename"] = plan
            params["plan_index"] = self.plan_index.value()
        return params

    # ------------------------------------------------------------------ Recruit

    def _build_recruit(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(12, 12, 12, 12)

        self.recruit_min_star = combo_field(
            ["3★ fallback — recruit 4★+, refresh 3★ rolls, take 3★ when refresh runs out",
             "4★ — conserve tickets for 4★+ only",
             "5★ — only rare combos"], default_index=0)
        self.recruit_min_star.currentIndexChanged.connect(
            self._on_min_star_changed)
        grid.addWidget(FieldRow(
            "Min star level to recruit",
            self.recruit_min_star,
            "4★+ rolls are always recruited immediately; 3★ rolls are "
            "refreshed while refresh lasts (3★ fallback) and only recruited "
            "when the game has no refreshes left"), 0, 0)

        self.recruit_times = spin_field(4, 0, 999)
        grid.addWidget(FieldRow("Times (0 = until all slots filled)", self.recruit_times), 0, 1)

        self.recruit_refresh = bool_field()
        grid.addWidget(FieldRow("Refresh tags (刷新)", self.recruit_refresh), 0, 2)

        self.recruit_first_tags = text_field("", "e.g. \u8d44\u6df1\u5e72\u5458, \u9ad8\u7ea7\u8d44\u6df1\u5e72\u5458")
        grid.addWidget(FieldRow("First tags (优先词条)", self.recruit_first_tags), 1, 0)

        self.recruit_extra_mode = combo_field(
            ["0 — no extra tags", "1 — extra tags only", "2 — default + extra tags"])
        grid.addWidget(FieldRow("Extra tags mode", self.recruit_extra_mode), 1, 1)

        self.recruit_expedite = bool_field()
        grid.addWidget(FieldRow("Expedite (加急许可)", self.recruit_expedite), 1, 2)

        self.recruit_skip_robot = bool_field()
        grid.addWidget(FieldRow("Keep robot tags (保留支援机械词条)", self.recruit_skip_robot), 2, 0)

        self.recruit_set_time = bool_field()
        grid.addWidget(FieldRow("Set time (设置时间)", self.recruit_set_time), 2, 1)

        self.recruit_time = text_field("9:00", "e.g. 9:00")
        grid.addWidget(FieldRow("Recruit time (公招时间)", self.recruit_time), 2, 2)

        return w

    def _on_min_star_changed(self, *_):
        # 3★ fallback mode always refreshes 3★ rolls — the checkbox is forced on
        # and disabled; 4★/5★ conservation modes leave it to the user
        fallback = self.recruit_min_star.currentIndex() == 0
        self.recruit_refresh.setEnabled(not fallback)
        self.recruit_refresh.setChecked(fallback)

    def recruit_params(self) -> dict:
        # MaaCore requires `select`/`confirm` arrays (guaranteed-rarity levels
        # allowed to auto-select/auto-confirm); omitting them skips every roll.
        # With refresh=true, MAA only ever refreshes 3★ rolls (4★+ are recruited
        # directly), so 3★ fallback = select/confirm everything + refresh: the
        # 4★+ preference is preserved and 3★ becomes the no-refresh fallback.
        min_star = 3 + self.recruit_min_star.currentIndex()  # 3 / 4 / 5
        levels = list(range(min_star, 7))
        params: dict = {"select": levels, "confirm": levels}
        if self.recruit_times.value():
            params["times"] = self.recruit_times.value()
        if self.recruit_refresh.isChecked():
            params["refresh"] = True
        elif min_star != 3:
            params["refresh"] = False
        if self.recruit_first_tags.text().strip():
            params["first_tags"] = _split_tags(self.recruit_first_tags.text())
        params["extra_tags_mode"] = self.recruit_extra_mode.currentIndex()
        if self.recruit_expedite.isChecked():
            params["expedite"] = True
        if self.recruit_skip_robot.isChecked():
            # `skip_robot` is deprecated since 6.11.0 — use preserve_tags
            params["preserve_tags"] = ["\u652f\u63f4\u673a\u68b0"]
        if self.recruit_set_time.isChecked():
            params["set_time"] = True
            params["recruitment_time"] = self.recruit_time.text().strip() or "9:00"
        return params

    # --------------------------------------------------------------------- Mall

    def _build_mall(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(12, 12, 12, 12)

        self.mall_shopping = bool_field(True)
        grid.addWidget(FieldRow("Shopping (购物)", self.mall_shopping), 0, 0)

        self.mall_buy_first = text_field("", "item names, comma-separated")
        grid.addWidget(FieldRow("Buy first (优先购买)", self.mall_buy_first), 0, 1, 1, 2)

        self.mall_blacklist = text_field("", "item names, comma-separated")
        grid.addWidget(FieldRow("Blacklist (黑名单)", self.mall_blacklist), 1, 0, 1, 2)

        self.mall_credit_fight = bool_field()
        grid.addWidget(FieldRow("Fight when credit full", self.mall_credit_fight), 1, 2)

        self.mall_force = bool_field()
        grid.addWidget(FieldRow("Force shopping if credit full", self.mall_force), 2, 0)

        self.mall_discount = bool_field(True)
        grid.addWidget(FieldRow("Only buy discounted", self.mall_discount), 2, 1)

        return w

    def mall_params(self) -> dict:
        params: dict = {"shopping": self.mall_shopping.isChecked()}
        if self.mall_buy_first.text().strip():
            params["buy_first"] = _split_tags(self.mall_buy_first.text())
        if self.mall_blacklist.text().strip():
            params["blacklist"] = _split_tags(self.mall_blacklist.text())
        params["credit_fight_last"] = self.mall_credit_fight.isChecked()
        params["force_shopping_if_credit_full"] = self.mall_force.isChecked()
        params["only_buy_discount"] = self.mall_discount.isChecked()
        return params

    # -------------------------------------------------------------------- Award

    def _build_award(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(12, 12, 12, 12)

        self.award_daily = bool_field(True)
        grid.addWidget(FieldRow("Daily + weekly award (每日+每周奖励)", self.award_daily), 0, 0)

        self.award_mail = bool_field(True)
        grid.addWidget(FieldRow("Mail (邮件)", self.award_mail), 0, 1)

        self.award_recruit = bool_field()
        grid.addWidget(FieldRow("Recruit award (公招奖励)", self.award_recruit), 0, 2)

        self.award_orundum = bool_field()
        grid.addWidget(FieldRow("Orundum (合成玉)", self.award_orundum), 1, 0)

        self.award_mining = bool_field()
        grid.addWidget(FieldRow("Mining (限时开采许可)", self.award_mining), 1, 1)

        self.award_special = bool_field()
        grid.addWidget(FieldRow("Special access (特别访问许可)", self.award_special), 1, 2)

        return w

    def award_params(self) -> dict:
        # `award` covers both the daily and weekly task rewards in MaaCore
        return {
            "award": self.award_daily.isChecked(),
            "mail": self.award_mail.isChecked(),
            "recruit": self.award_recruit.isChecked(),
            "orundum": self.award_orundum.isChecked(),
            "mining": self.award_mining.isChecked(),
            "specialaccess": self.award_special.isChecked(),
        }

    # ------------------------------------------------------------------ save/run

    def save(self) -> bool:
        subs = [
            ("Infrast", "Infrast", self.infrast_params()),
            ("Recruit", "Recruit", self.recruit_params()),
            ("Mall", "Mall", self.mall_params()),
            ("Award", "Award", self.award_params()),
        ]
        maa.write_task(TASK_FILE, maa.task_file_text(
            subs, header="# Generated by MaaGui — Daily routine tasks"))
        return True

    def save_and_run(self):
        if self.runner.running:
            return
        self.save()
        self.runner.start(TASK_FILE, self.state.profile)

    def _load(self):
        try:
            data = maa.read_task(TASK_FILE)
            if not data.strip():
                return
            parsed = tomllib.loads(data)
            tasks = parsed.get("tasks") or []
        except Exception:
            return
        by_type = {t.get("type"): (t.get("params") or {}) for t in tasks}
        p = by_type.get("Infrast", {})
        if p:
            for name, cb in self.facility_checks.items():
                cb.setChecked(name in p.get("facility", FACILITIES))
            if "drones" in p:
                self.drones.setCurrentText(str(p["drones"]))
            if "threshold" in p:
                self.threshold.setValue(float(p["threshold"]))
            if "replenish" in p:
                self.replenish.setChecked(bool(p["replenish"]))
            if "dorm_trust_enabled" in p:
                self.dorm_trust.setChecked(bool(p["dorm_trust_enabled"]))
            if "dorm_notstationed_enabled" in p:
                self.dorm_notstationed.setChecked(bool(p["dorm_notstationed_enabled"]))
            if "filename" in p:
                self.plan_file.setText(str(p["filename"]))
            if "plan_index" in p:
                self.plan_index.setValue(int(p["plan_index"]))
        p = by_type.get("Recruit", {})
        if p:
            self.recruit_times.setValue(int(p.get("times", 0)))
            self.recruit_refresh.setChecked(bool(p.get("refresh", False)))
            sel = p.get("select")
            if isinstance(sel, list) and sel:
                min_star = min(int(x) for x in sel)
                if 3 <= min_star <= 5:
                    self.recruit_min_star.setCurrentIndex(min_star - 3)
            self.recruit_first_tags.setText(", ".join(p.get("first_tags", [])) if isinstance(p.get("first_tags"), list) else str(p.get("first_tags", "")))
            if "extra_tags_mode" in p:
                mode = int(p["extra_tags_mode"])
                if 0 <= mode < self.recruit_extra_mode.count():
                    self.recruit_extra_mode.setCurrentIndex(mode)
            self.recruit_expedite.setChecked(bool(p.get("expedite", False)))
            preserve = p.get("preserve_tags", [])
            self.recruit_skip_robot.setChecked(
                bool(p.get("skip_robot", False)) or "\u652f\u63f4\u673a\u68b0" in preserve)
            self.recruit_set_time.setChecked(bool(p.get("set_time", False)))
            self.recruit_time.setText(str(p.get("recruitment_time", "9:00")))
            self._on_min_star_changed()
        p = by_type.get("Mall", {})
        if p:
            if "shopping" in p:
                self.mall_shopping.setChecked(bool(p["shopping"]))
            if "buy_first" in p:
                self.mall_buy_first.setText(", ".join(p["buy_first"]) if isinstance(p["buy_first"], list) else str(p["buy_first"]))
            if "blacklist" in p:
                self.mall_blacklist.setText(", ".join(p["blacklist"]) if isinstance(p["blacklist"], list) else str(p["blacklist"]))
            if "credit_fight_last" in p:
                self.mall_credit_fight.setChecked(bool(p["credit_fight_last"]))
            if "force_shopping_if_credit_full" in p:
                self.mall_force.setChecked(bool(p["force_shopping_if_credit_full"]))
            if "only_buy_discount" in p:
                self.mall_discount.setChecked(bool(p["only_buy_discount"]))
        p = by_type.get("Award", {})
        if p:
            self.award_daily.setChecked(bool(p.get("award", True)))
            self.award_mail.setChecked(bool(p.get("mail", True)))
            self.award_recruit.setChecked(bool(p.get("recruit", False)))
            self.award_orundum.setChecked(bool(p.get("orundum", False)))
            self.award_mining.setChecked(bool(p.get("mining", False)))
            self.award_special.setChecked(bool(p.get("specialaccess", False)))


def _ints(text: str) -> list[int]:
    out = []
    for part in text.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def _join_ints(values) -> str:
    if isinstance(values, list):
        return ", ".join(str(v) for v in values)
    return ""


def _split_tags(text: str) -> list[str]:
    return [t.strip() for t in text.split(",") if t.strip()]
