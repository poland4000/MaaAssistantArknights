"""PRTS Search page (作业搜索): find stage clears, filter by your roster.

Flow:
  1. Type a stage (display code like TA-EX-2, or internal id like act49side),
     optional include/exclude operators, then Search.
  2. "Read my operators" runs MAA's OperBox recognition and remembers your
     roster, so each result is marked  own / borrow (1 missing) / missing N.
  3. The tolerance filter keeps results you can actually run — by default it
     allows exactly one missing operator, which MAA can auto-borrow
     (--support-unit-usage 1).
  4. "+ Add" pushes maa://<id> into the Copilot page's battle queue.
"""

from __future__ import annotations

import json
import time

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import maa, prts, theme
from ..runner import TaskRunner
from ..state import AppState

TASK_FILE = maa.GUI_PREFIX + "operbox"

TOLERANCES = [
    ("0", "0 — must own every operator"),
    ("1", "1 — allow one missing (auto-borrow)"),
    ("2", "2 — allow two missing"),
    ("99", "any — show everything"),
]


class _WorkerBridge(QObject):
    """Queues worker results back onto the main thread (QObject lives there)."""

    result = Signal(object)


class _SearchWorker(QRunnable):
    def __init__(self, fn, bridge: _WorkerBridge):
        super().__init__()
        self.fn = fn
        self.bridge = bridge

    @Slot()
    def run(self):
        try:
            self.bridge.result.emit(self.fn())
        except Exception as e:  # network / parse errors of any kind
            self.bridge.result.emit(("error", str(e)))


def _normalize_names(copilot: dict, cn2en: dict, en2cn: dict) -> set[str]:
    """All operator names (opers + group members) normalized to CN."""
    content = prts.parse_content(copilot.get("content", ""))
    names = set()
    for op in content.get("opers") or []:
        n = (op or {}).get("name", "")
        if n:
            names.add(prts._to_cn(n, cn2en, en2cn))
    for grp in content.get("groups") or []:
        for m in (grp.get("opers") or []):
            n = (m or {}).get("name", "")
            if n:
                names.add(prts._to_cn(n, cn2en, en2cn))
    return names


class SearchPage(QWidget):
    add_to_queue = Signal(str)  # maa://<id>

    def __init__(self, runner: TaskRunner, state: AppState, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.state = state
        self.cn2en, self.en2cn = prts.load_oper_names()
        self.code2id, self.id2code = prts.load_stage_map()
        self.roster: dict[str, dict] = {}   # cn name -> {elite, level, potential}
        self.roster_cn: set[str] = set()
        self._results: list[dict] = []      # all fetched records
        self._page = 0
        self._has_next = False
        self._total = 0
        self._busy = False
        self._pool = QThreadPool(self)
        self._bridge = _WorkerBridge(self)
        self._bridge.result.connect(self._on_worker_result)
        self._reading_ops = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("PRTS Search — 作业搜索")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        outer.addWidget(title)

        # ---- search row ---------------------------------------------------------
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        self.stage = QLineEdit()
        self.stage.setPlaceholderText("stage — e.g. TA-EX-2, 1-7, or act49side")
        self.stage.returnPressed.connect(self._search)
        grid.addWidget(self.stage, 0, 0)

        self.include = QLineEdit()
        self.include.setPlaceholderText("must include ops (comma-separated)")
        self.include.returnPressed.connect(self._search)
        grid.addWidget(self.include, 0, 1)

        self.exclude = QLineEdit()
        self.exclude.setPlaceholderText("must NOT include ops (comma-separated)")
        self.exclude.returnPressed.connect(self._search)
        grid.addWidget(self.exclude, 0, 2)

        self.sort = QComboBox()
        self.sort.addItems(prts.ORDER_BY)
        self.sort.setCurrentText("hot")
        grid.addWidget(self.sort, 1, 0)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("primary")
        self.search_btn.clicked.connect(self._search)
        grid.addWidget(self.search_btn, 1, 1)

        self.refresh_data_btn = QPushButton("Refresh stage data")
        self.refresh_data_btn.setToolTip("Re-download the stage code table from the game data repo")
        self.refresh_data_btn.clicked.connect(self._refresh_stage_data)
        grid.addWidget(self.refresh_data_btn, 1, 2)
        outer.addLayout(grid)

        # ---- my operators --------------------------------------------------------
        ops_box = QWidget()
        ops_box.setStyleSheet(
            f"background-color: {theme.BG_ELEV}; border: 1px solid {theme.BORDER}; "
            f"border-radius: 10px;")
        ops_lay = QVBoxLayout(ops_box)
        ops_lay.setContentsMargins(14, 10, 14, 10)
        ops_lay.setSpacing(6)

        row = QHBoxLayout()
        self.read_ops_btn = QPushButton("🎯 Read my operators")
        self.read_ops_btn.setToolTip(
            "Runs MAA's OperBox recognition in the game (must be on the home "
            "screen) and remembers your roster")
        self.read_ops_btn.clicked.connect(self._read_operators)
        row.addWidget(self.read_ops_btn)
        self.roster_lbl = QLabel("no roster yet")
        self.roster_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        row.addWidget(self.roster_lbl)
        row.addStretch(1)
        self.only_runnable = QCheckBox("Only show copilots I can run")
        self.only_runnable.setChecked(self.state.settings.value("search/only_runnable", True, bool))
        self.only_runnable.toggled.connect(self._on_only_runnable_toggled)
        row.addWidget(self.only_runnable)
        row.addWidget(QLabel("missing tolerance:"))
        self.tolerance = QComboBox()
        for value, label in TOLERANCES:
            self.tolerance.addItem(label, value)
        self.tolerance.setCurrentIndex(1)
        saved = str(self.state.settings.value("search/tolerance", "1"))
        idx = self.tolerance.findData(saved)
        if idx >= 0:
            self.tolerance.setCurrentIndex(idx)
        self.tolerance.currentIndexChanged.connect(self._on_tolerance_changed)
        row.addWidget(self.tolerance)
        ops_lay.addLayout(row)
        outer.addWidget(ops_box)

        # ---- results ------------------------------------------------------------
        self.results_lbl = QLabel("")
        self.results_lbl.setStyleSheet(f"color: {theme.TEXT_DIM};")
        outer.addWidget(self.results_lbl)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Title / Stage", "Mode", "Uploader", "Views",
             "Operators needed", "Status", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        outer.addWidget(self.table, 1)

        self.load_more_btn = QPushButton("Load more")
        self.load_more_btn.clicked.connect(self._load_more)
        self.load_more_btn.setEnabled(False)
        outer.addWidget(self.load_more_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self.runner.running_changed.connect(self._on_running_changed)
        self._restore_roster()
        self._re_render()

    def shutdown(self):
        """Cancel queued network workers so interpreter exit isn't blocked."""
        self._pool.clear()
        self._pool.waitForDone(3000)

    # ------------------------------------------------------------ roster

    @staticmethod
    def _roster_path():
        """Shared roster file — persists across BOTH GUIs (maagui/maagui2)."""
        return maa.config_dir() / "roster.json"

    def _read_roster_file(self) -> dict[str, dict]:
        try:
            data = json.loads(self._roster_path().read_text())
            return {str(k): dict(v) for k, v in data.items()}
        except Exception:
            return {}

    # ------------------------------------------------------------ roster

    def _restore_roster(self):
        roster = self._read_roster_file()
        if not roster:
            # migrate from this app's legacy QSettings copy (or the very old
            # name-list format) so one final read isn't needed
            raw = self.state.settings.value("search/roster", None)
            if isinstance(raw, str) and raw.lstrip().startswith("{"):
                try:
                    roster = {str(k): dict(v) for k, v in json.loads(raw).items()}
                except (json.JSONDecodeError, ValueError, TypeError):
                    roster = {}
            elif isinstance(raw, dict):
                roster = {str(k): dict(v) for k, v in raw.items()}
            elif isinstance(raw, list):
                roster = self._roster_from_log()
            if roster:
                self._save_roster(roster, stamp="")
        self.roster = roster
        self.roster_cn = set(roster)
        stamp = self.state.settings.value("search/roster_ts", "")
        if self.roster_cn:
            self.roster_lbl.setText(
                f"{len(self.roster_cn)} operators known (read {stamp})")

    @staticmethod
    def _roster_from_log() -> dict[str, dict]:
        """Build {cn name: {elite, level, potential}} from MaaCore's asst.log."""
        msg = maa.latest_operbox_message()
        if not msg:
            return {}
        cn2en, en2cn = prts.load_oper_names()
        roster: dict[str, dict] = {}
        for o in (msg.get("details") or {}).get("own_opers", []):
            n = (o or {}).get("name", "")
            if not n:
                continue
            cn = prts._to_cn(n, cn2en, en2cn)
            if cn:
                roster[cn] = {
                    "elite": int(o.get("elite", 0)),
                    "level": int(o.get("level", 1)),
                    "potential": int(o.get("potential", 0)),
                }
        return roster

    def _save_roster(self, roster: dict[str, dict], stamp: str = ""):
        path = self._roster_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(roster, ensure_ascii=False))
            tmp.replace(path)
        except OSError:
            pass  # non-fatal: filtering just won't persist
        self.state.settings.setValue("search/roster", json.dumps(roster))
        if stamp:
            self.state.settings.setValue("search/roster_ts", stamp)

    def _read_operators(self):
        if self.runner.running:
            QMessageBox.information(self, "Busy", "A task is already running.")
            return
        maa.write_task(TASK_FILE, maa.task_file_text(
            [("Read operators", "OperBox", {})],
            header="# Generated by MaaGui — operator roster recognition"))
        self.roster_lbl.setText("reading operators… (game must be open)")
        self._reading_ops = True
        self.runner.start(TASK_FILE, self.state.profile)

    def _on_running_changed(self, running: bool):
        self.read_ops_btn.setEnabled(not running)
        if running or not self._reading_ops:
            return
        self._reading_ops = False
        msg = maa.latest_operbox_message()
        names = [
            (o or {}).get("name", "")
            for o in ((msg or {}).get("details") or {}).get("own_opers", [])
        ]
        names = [n for n in names if n]
        if not names:
            self.roster_lbl.setText(
                "couldn't read the roster — check the Logs tab (did the "
                "recognition finish?)")
            return
        # names come back in the game's language; normalize to CN, keep levels
        roster: dict[str, dict] = {}
        for o in ((msg or {}).get("details") or {}).get("own_opers", []):
            n = (o or {}).get("name", "")
            if not n:
                continue
            cn = prts._to_cn(n, self.cn2en, self.en2cn)
            if cn:
                roster[cn] = {
                    "elite": int(o.get("elite", 0)),
                    "level": int(o.get("level", 1)),
                    "potential": int(o.get("potential", 0)),
                }
        self.roster = roster
        self.roster_cn = set(roster)
        stamp = time.strftime("%Y-%m-%d %H:%M")
        self._save_roster(roster, stamp)
        self.roster_lbl.setText(f"{len(roster)} operators known (read {stamp})")
        self._re_render()

    # ------------------------------------------------------------ search

    def _search(self):
        if self._busy:
            return
        self._results = []
        self._page = 0
        self._total = 0
        self._fetch_next()

    def _load_more(self):
        if not self._busy and self._has_next:
            self._fetch_next()

    def _fetch_next(self):
        self._busy = True
        self._pending_tag = "search"
        self.search_btn.setEnabled(False)
        self.load_more_btn.setEnabled(False)
        self.results_lbl.setText("searching…")

        stage_text = self.stage.text().strip()
        level = prts.resolve_stage(stage_text, self.code2id)
        include = [t.strip() for t in self.include.text().split(",") if t.strip()]
        exclude = [t.strip() for t in self.exclude.text().split(",") if t.strip()]
        include = [prts._to_cn(n, self.cn2en, self.en2cn) for n in include]
        exclude = [prts._to_cn(n, self.cn2en, self.en2cn) for n in exclude]
        order = self.sort.currentText()
        page = self._page + 1

        def work():
            return ("search", prts.query(page=page, limit=20, level_keyword=level,
                                        order_by=order))

        self._pending = (stage_text, level, include, exclude)
        self._pool.start(_SearchWorker(work, self._bridge))

    def _on_worker_result(self, result):
        """Dispatch tagged worker results back on the main thread."""
        if not (isinstance(result, tuple) and result):
            return
        tag, payload = result[0], result[1] if len(result) > 1 else None
        if tag == "error":
            self._busy = False
            self.search_btn.setEnabled(True)
            if getattr(self, "_pending_tag", "") == "search":
                QMessageBox.warning(self, "Search failed",
                                    f"prts.plus query error: {payload}")
                self.results_lbl.setText(f"error: {payload}")
            else:
                self.results_lbl.setText(f"stage refresh failed: {payload}")
                self.refresh_data_btn.setEnabled(True)
                self.refresh_data_btn.setText("Refresh stage data")
        elif tag == "search":
            self._on_search_result(payload)
        elif tag == "refresh":
            self._on_refresh_done(payload)

    def _on_search_result(self, data):
        stage_text, level, include, exclude = self._pending
        self._busy = False
        self.search_btn.setEnabled(True)
        self._page = self._page + 1
        self._has_next = bool(data.get("has_next"))
        self._total = int(data.get("total", 0))
        records = data.get("data") or []
        if stage_text and level != stage_text:
            self.results_lbl.setText(
                f"searching '{stage_text}' (internal: {level})")
        keep = [r for r in records if self._matches_filters(r, include, exclude)]
        self._results.extend(keep)
        self.load_more_btn.setEnabled(self._has_next)
        self._re_render()

    def _matches_filters(self, record: dict, include: list[str],
                         exclude: list[str]) -> bool:
        names = _normalize_names(record, self.cn2en, self.en2cn)
        if exclude and names & set(exclude):
            return False
        if include and not set(include) <= names:
            return False
        return True

    def _on_only_runnable_toggled(self, on: bool):
        self.state.settings.setValue("search/only_runnable", on)
        self._re_render()

    def _on_tolerance_changed(self, *_):
        self.state.settings.setValue("search/tolerance", self.tolerance.currentData())
        self._re_render()

    # ------------------------------------------------------------ rendering

    def _re_render(self):
        tol = int(self.tolerance.currentData())
        core = maa.versions()[1]
        rows = []
        for rec in self._results:
            info = prts.analyze_availability(rec, self.roster_cn, self.cn2en,
                                             self.en2cn, self.roster)
            ok_version = prts.version_ok(info["min_version"], core)
            runnable = info["missing_count"] <= tol and ok_version
            rows.append((rec, info, ok_version, runnable))

        filter_on = self.only_runnable.isChecked() and bool(self.roster_cn)
        shown = [r for r in rows if not filter_on or r[3]]
        self.table.setRowCount(len(shown))
        for i, (rec, info, ok_version, runnable) in enumerate(shown):
            content = info["content"]
            doc = content.get("doc") or {}
            title = doc.get("title") or f"#{rec['id']}"
            stage = self.id2code.get(content.get("stage_name", ""),
                                     content.get("stage_name", ""))
            self._set(i, 0, f"{title}   [{stage}]")

            mode = prts.mode_label(rec)
            mode_item = QTableWidgetItem(mode)
            mode_item.setToolTip({
                "Both": "Covers normal and challenge mode — run with "
                        "Mode = both on the Copilot page",
                "Normal": "Normal mode only",
                "Challenge": "Challenge (突袭) mode only",
                "?": "Mode not specified by the author",
            }.get(mode, ""))
            mode_item.setForeground(self._mode_color(mode))
            mode_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, mode_item)

            self._set(i, 2, str(rec.get("uploader", "")))
            self._set(i, 3, str(rec.get("views", 0)))

            ops_txt = prts.format_ops_short(rec, self.roster_cn, self.cn2en,
                                            self.en2cn, self.roster)
            self._set(i, 4, ops_txt)

            # status badge
            badge = self._status_badge(info, ok_version, runnable, core)
            item = QTableWidgetItem(badge)
            item.setForeground(self._badge_color(badge))
            self.table.setItem(i, 5, item)

            add_btn = QPushButton("+ Add")
            add_btn.setToolTip(f"Queue maa://{rec['id']} on the Copilot page")
            add_btn.clicked.connect(
                lambda _=False, rid=rec["id"]: self.add_to_queue.emit(f"maa://{rid}"))
            self.table.setCellWidget(i, 6, add_btn)

        total_shown = len(shown)
        note = ""
        if self.only_runnable.isChecked() and not self.roster_cn:
            note = "  (read your operators to enable runnable filtering)"
        self.results_lbl.setText(
            f"{total_shown} shown of {self._total} on prts.plus{note}")
    def _set(self, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setToolTip(text)
        self.table.setItem(row, col, item)

    def _status_badge(self, info: dict, ok_version: bool, runnable: bool, core: str) -> str:
        if not ok_version:
            return f"needs MAA {info['min_version']}"
        if info["missing_count"] == 0:
            if info["underleveled"]:
                w = info["underleveled"][0]
                extra = f" +{len(info['underleveled']) - 1}" if len(info["underleveled"]) > 1 else ""
                return f"⚠ req: {w['name']} {w['need']} (have {w['have']}){extra}"
            return "✓ all owned"
        if info["missing_count"] == 1:
            return "⚠ borrow 1: " + prts.fmt_entry(info["missing"][0], self.cn2en)
        names = ", ".join(prts.fmt_entry(m, self.cn2en) for m in info["missing"][:2])
        return f"✗ missing {info['missing_count']}: {names}"

    def _badge_color(self, badge: str):
        from PySide6.QtGui import QColor
        if badge.startswith("✓"):
            return QColor(theme.OK)
        if badge.startswith("⚠"):
            return QColor(theme.WARN)
        return QColor(theme.ERR)

    def _mode_color(self, mode: str):
        from PySide6.QtGui import QColor
        if mode == "Both":
            return QColor("#b48cf0")  # purple: covers both modes
        if mode == "Normal":
            return QColor(theme.OK)
        if mode == "Challenge":
            return QColor(theme.WARN)
        return QColor(theme.TEXT_DIM)

    # ------------------------------------------------------------ stage data

    def _refresh_stage_data(self):
        """Re-download the game stage table and rebuild the code map."""
        self._pending_tag = "refresh"
        self.refresh_data_btn.setEnabled(False)
        self.refresh_data_btn.setText("downloading…")

        def work():
            import urllib.request
            url = ("https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/"
                   "master/zh_CN/gamedata/excel/stage_table.json")
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = json.load(resp)
            code2id, id2code = {}, {}
            for sid, info in (data.get("stages") or {}).items():
                code = info.get("code", "")
                if code:
                    code2id.setdefault(code, sid)
                    id2code.setdefault(sid, code)
            return ("refresh", (code2id, id2code))

        self._pool.start(_SearchWorker(work, self._bridge))

    def _on_refresh_done(self, payload):
        code2id, id2code = payload
        self.refresh_data_btn.setEnabled(True)
        self.refresh_data_btn.setText("Refresh stage data")
        try:
            from ..prts import _DATA_DIR
            (_DATA_DIR / "stages.json").write_text(
                json.dumps({"code2id": code2id, "id2code": id2code},
                           ensure_ascii=False))
            self.code2id, self.id2code = code2id, id2code
            self.results_lbl.setText(
                f"stage data refreshed ({len(code2id)} stages)")
        except OSError as e:
            self.results_lbl.setText(f"could not save stage data: {e}")
