"""Fight page (刷理智): stage farming settings → `__gui_fight` task."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import maa
from ..runner import TaskRunner
from ..state import AppState
from ..widgets import (
    RunBar,
    bool_field,
    FieldRow,
    spin_field,
    text_field,
)

TASK_FILE = maa.GUI_PREFIX + "fight"


class FightPage(QWidget):
    def __init__(self, runner: TaskRunner, state: AppState, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Fight — 刷理智")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        self.stage = text_field("", "e.g. 1-7, CE-6 (empty = current stage)")
        grid.addWidget(FieldRow("Stage", self.stage), 0, 0)

        self.medicine = spin_field(0, 0, 9999)
        grid.addWidget(FieldRow("Medicine (理智药)", self.medicine), 0, 1)

        self.expiring = spin_field(0, 0, 9999)
        grid.addWidget(FieldRow("Expiring medicine", self.expiring), 0, 2)

        self.stone = spin_field(0, 0, 9999)
        grid.addWidget(FieldRow("Stone (源石)", self.stone), 0, 3)

        self.times = spin_field(0, 0, 99999, suffix=" (0 = unlimited)")
        grid.addWidget(FieldRow("Times", self.times), 1, 0)

        self.series = spin_field(1, -1, 6)
        self.series.setSpecialValueText("auto")
        grid.addWidget(FieldRow("Proxy series (-1–6)", self.series), 1, 1)

        self.penguin = bool_field()
        grid.addWidget(FieldRow("Report to Penguin Statistics", self.penguin), 1, 2)

        self.yituliu = bool_field()
        grid.addWidget(FieldRow("Report to Yituliu", self.yituliu), 1, 3)

        self.penguin_id = text_field("", "optional ID")
        grid.addWidget(FieldRow("Penguin ID", self.penguin_id), 2, 0)

        self.yituliu_id = text_field("", "optional ID")
        grid.addWidget(FieldRow("Yituliu ID", self.yituliu_id), 2, 1)

        self.drops = text_field("", "itemID=count, comma-separated, e.g. 30012=100")
        self.drops.setPlaceholderText("e.g. 30012=100, 30011=50")
        grid.addWidget(FieldRow("Exit after drops", self.drops), 2, 2, 1, 2)

        outer.addLayout(grid)

        self.bar = RunBar()
        self.bar.save_requested.connect(self.save)
        self.bar.run_requested.connect(self.save_and_run)
        self.bar.stop_btn.clicked.connect(self.runner.stop)
        outer.addWidget(self.bar)
        outer.addStretch(1)

        self.runner.running_changed.connect(self.bar.set_running)
        self._load()

    # -- form <-> params ------------------------------------------------------

    def to_task_params(self) -> dict:
        params: dict = {}
        stage = self.stage.text().strip()
        if stage:
            params["stage"] = stage
        if self.medicine.value():
            params["medicine"] = self.medicine.value()
        if self.expiring.value():
            params["expiring_medicine"] = self.expiring.value()
        if self.stone.value():
            params["stone"] = self.stone.value()
        if self.times.value():
            params["times"] = self.times.value()
        params["series"] = self.series.value()
        if self.penguin.isChecked():
            params["report_to_penguin"] = True
            if self.penguin_id.text().strip():
                params["penguin_id"] = self.penguin_id.text().strip()
        if self.yituliu.isChecked():
            params["report_to_yituliu"] = True
            if self.yituliu_id.text().strip():
                params["yituliu_id"] = self.yituliu_id.text().strip()
        drops: dict[str, int] = {}
        for part in self.drops.text().split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                k, _, v = part.partition("=")
                try:
                    drops[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        if drops:
            params["drops"] = drops
        return params

    def _load(self):
        """Load a previously saved GUI fight task, if present."""
        try:
            data = maa.read_task(TASK_FILE)
            if not data.strip():
                return
            import tomllib
            parsed = tomllib.loads(data)
            p = (parsed.get("tasks") or [{}])[0].get("params", {})
        except Exception:
            return
        if not p:
            return
        self.stage.setText(str(p.get("stage", "")))
        self.medicine.setValue(int(p.get("medicine", 0)))
        self.expiring.setValue(int(p.get("expiring_medicine", 0)))
        self.stone.setValue(int(p.get("stone", 0)))
        self.times.setValue(int(p.get("times", 0)))
        self.series.setValue(int(p.get("series", 1)))
        self.penguin.setChecked(bool(p.get("report_to_penguin", False)))
        self.penguin_id.setText(str(p.get("penguin_id", "")))
        self.yituliu.setChecked(bool(p.get("report_to_yituliu", False)))
        self.yituliu_id.setText(str(p.get("yituliu_id", "")))
        drops = p.get("drops")
        if isinstance(drops, dict):
            self.drops.setText(", ".join(f"{k}={v}" for k, v in drops.items()))

    # -- actions ---------------------------------------------------------------

    def save(self) -> bool:
        params = self.to_task_params()
        maa.write_task(TASK_FILE, maa.task_file_text(
            [("Fight", "Fight", params)], header="# Generated by MaaGui — Fight"))
        return True

    def save_and_run(self):
        if self.runner.running:
            return
        self.save()
        self.runner.start(TASK_FILE, self.state.profile)
