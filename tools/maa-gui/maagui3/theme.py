"""Theme for MaaGui3 — matched to the Windows MAA (WPF) dark look.

Colors are sampled from the reference screenshots of MAA v5.1.0 dark theme:
a blue-gray window, region panels slightly lighter, primary blue accents,
 HandyControl-style 4px corner radii and 1px borders.
"""

ACCENT = "#3d6fd6"          # primary blue (tab underline, selections)
ACCENT_BRIGHT = "#4c85e8"   # hover
ACCENT_DIM = "#2b4f8f"      # pressed / filled selections
ACCENT_TEXT = "#4c85e8"     # selected tab / link text

BG = "#22252c"              # window background
BG_REGION = "#2a2d35"       # panels / inputs (RegionBrush)
BG_REGION_LIGHT = "#33363f"  # hover fill
BG_INPUT = "#2e3138"        # text inputs, combos
BORDER = "#3f434c"
TEXT = "#dde1e8"
TEXT_DIM = "#8b91a0"
TEXT_TRACE = "#6f7480"      # log timestamps
OK = "#3ddc84"
WARN = "#f5b041"
ERR = "#f2645a"
LOG_INFO = "#50c1e0"        # cyan used by MAA for recruit/tag results
FONT_FAMILY = "Noto Sans"

QSS = f"""
* {{
    font-family: "{FONT_FAMILY}", "Cantarell", "DejaVu Sans", sans-serif;
    font-size: 12px;
    color: {TEXT};
}}
QMainWindow, QWidget#root, QWidget#pageRoot, QDialog {{
    background-color: {BG};
}}
QToolTip {{
    background-color: {BG_REGION};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 8px;
}}

/* ---- top tab bar (Farming / Copilot / Toolbox / Settings) ---------------- */
QPushButton#topTab {{
    background-color: {BG};
    border: none;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    color: {TEXT};
    font-size: 14px;
    padding: 10px 0 8px 0;
}}
QPushButton#topTab:hover {{ color: #ffffff; }}
QPushButton#topTab:checked {{
    color: {ACCENT_TEXT};
    border-bottom: 3px solid {ACCENT};
}}

/* ---- task list (Farming left column) ------------------------------------ */
QWidget#taskPanel {{
    background-color: {BG_REGION};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
QWidget#taskRow {{
    background: transparent;
    border-radius: 4px;
}}
QWidget#taskRow:hover {{
    background-color: #363a44;
}}
QLabel#taskName {{
    background: transparent;
    font-size: 12px;
}}

/* ---- buttons -------------------------------------------------------------- */
QPushButton {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton:hover {{ border-color: {ACCENT}; background-color: #33373f; }}
QPushButton:pressed {{ background-color: {ACCENT_DIM}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; background-color: {BG_REGION}; }}
QPushButton#linkStart {{
    min-width: 100px;
    max-width: 100px;
    min-height: 48px;
    max-height: 48px;
    font-size: 14px;
    border-radius: 4px;
}}
QPushButton#linkStart:disabled {{ color: {TEXT_DIM}; }}
QPushButton#toolboxStart {{
    padding: 12px 28px;
    font-size: 13px;
}}
QPushButton#checkBtn, QPushButton#secondary {{
    background-color: {BG_REGION};
}}

/* ---- inputs --------------------------------------------------------------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ color: {TEXT_DIM}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {BG_REGION};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM};
    outline: 0;
}}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {BG_REGION_LIGHT};
    border: none;
    width: 16px;
}}

/* ---- checkboxes ------------------------------------------------------------ */
QCheckBox {{ spacing: 7px; background: transparent; }}
QCheckBox:disabled {{ color: {TEXT_DIM}; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1px solid #5a5f6b;
    border-radius: 3px;
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    image: url(none);
}}

/* ---- gear buttons in the task list ----------------------------------------- */
QPushButton#gear {{
    background: transparent;
    border: none;
    color: {TEXT_DIM};
    font-size: 14px;
    padding: 0;
}}
QPushButton#gear:hover {{ color: {ACCENT_BRIGHT}; }}
QPushButton#gear:checked {{ color: {ACCENT_TEXT}; }}

/* ---- log panel (right column) ---------------------------------------------- */
QScrollArea#logPanel {{
    background: transparent;
    border: none;
}}
QWidget#logBody {{ background: transparent; }}
QLabel#logTime {{ color: {TEXT_TRACE}; }}
QLabel#logContent {{ background: transparent; }}

/* ---- settings page (left category list) ------------------------------------ */
QListWidget#settingsCats {{
    background: transparent;
    border: none;
    outline: 0;
    font-size: 13px;
}}
QListWidget#settingsCats::item {{
    height: 34px;
    padding-left: 12px;
    border-radius: 4px;
    margin: 1px 4px;
    color: {TEXT};
}}
QListWidget#settingsCats::item:selected {{ background-color: {ACCENT_DIM}; }}
QListWidget#settingsCats::item:hover:!selected {{ background-color: #33373f; }}

/* ---- copilot sub-tabs (segmented pill row) ---------------------------------- */
QPushButton#subTab {{
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 5px 14px;
    color: {TEXT};
    font-size: 12px;
}}
QPushButton#subTab:hover {{ background-color: #33373f; }}
QPushButton#subTab:checked {{
    background-color: {ACCENT_DIM};
    color: #ffffff;
}}
QPushButton#generalAdvToggle {{
    background-color: {BG_REGION};
    border: 1px solid {BORDER};
    color: {TEXT_DIM};
    padding: 5px 18px;
    font-size: 12px;
}}
QPushButton#generalAdvToggle:checked {{
    background-color: {BG_REGION_LIGHT};
    color: {ACCENT_TEXT};
    border: 1px solid {ACCENT};
}}
QPushButton#genToggle {{
    background-color: {BG_REGION};
    border: 1px solid {BORDER};
    border-radius: 4px 0 0 4px;
    color: {TEXT_DIM};
    padding: 5px 20px;
    font-size: 12px;
}}
QPushButton#advToggle {{
    background-color: {BG_REGION};
    border: 1px solid {BORDER};
    border-left: none;
    border-radius: 0 4px 4px 0;
    color: {TEXT_DIM};
    padding: 5px 20px;
    font-size: 12px;
}}
QPushButton#genToggle:checked, QPushButton#advToggle:checked {{
    background-color: {BG_REGION_LIGHT};
    color: {ACCENT_TEXT};
    border-color: {ACCENT};
    border-left: 1px solid {ACCENT};
}}
QPushButton#genToggle:checked {{ border-right: none; }}

/* ---- tables (toolbox recognitions, search results) -------------------------- */
QTableWidget, QTreeView, QListWidget {{
    background-color: {BG_REGION};
    border: 1px solid {BORDER};
    border-radius: 4px;
    outline: 0;
}}
QTableWidget::item:selected, QListWidget::item:selected {{ background-color: {ACCENT_DIM}; }}
QHeaderView::section {{
    background-color: {BG_REGION_LIGHT};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 4px 6px;
}}

/* ---- status bar -------------------------------------------------------------- */
QStatusBar {{
    background-color: {BG};
    border-top: 1px solid {BORDER};
    color: {TEXT_DIM};
}}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {TEXT_DIM}; }}
QStatusBar QPushButton {{ padding: 2px 12px; }}

/* ---- scrollbars / misc -------------------------------------------------------- */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #43474f; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT_DIM}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #43474f; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QSplitter::handle {{ background: {BORDER}; }}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 10px;
    padding: 8px 6px 6px 6px;
    background-color: {BG_REGION};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {TEXT_DIM};
}}
QPlainTextEdit, QTextEdit {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BG_INPUT};
    text-align: center;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 3px; }}
"""
