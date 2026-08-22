"""Theme for MaaGui2 — styled after the official Windows MAA (WPF) dark look."""

ACCENT = "#4f8cff"
ACCENT_DIM = "#33608f"
BG = "#22252e"          # window background (MAA dark blue-gray)
BG_RAIL = "#1b1d24"     # left icon rail
BG_CARD = "#2b2f3b"     # task cards / panels
BG_INPUT = "#333846"
BORDER = "#3c4250"
TEXT = "#e6e9f0"
TEXT_DIM = "#9aa0ae"
OK = "#3ddc84"
WARN = "#f5b041"
ERR = "#f2645a"

QSS = f"""
* {{
    font-family: "Noto Sans", "Cantarell", "DejaVu Sans", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget#root {{ background-color: {BG}; }}
QWidget#rail {{
    background-color: {BG_RAIL};
    border-right: 1px solid {BORDER};
}}
QToolButton#nav {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 0;
    font-size: 16px;
}}
QToolButton#nav:hover {{ background-color: #262a35; }}
QToolButton#nav:checked {{ background-color: {ACCENT_DIM}; }}

QWidget#header {{ background-color: {BG}; border-bottom: 1px solid {BORDER}; }}
QLabel#appTitle {{ font-size: 22px; font-weight: 800; color: {TEXT}; }}
QLabel#appSub {{ color: {TEXT_DIM}; font-size: 12px; }}

QWidget#card, QFrame#card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QLabel#cardTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#cardSub {{ color: {TEXT_DIM}; font-size: 11px; }}

QPushButton {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; }}

QPushButton#runBtn {{
    background-color: #1f7a4d;
    border: 1px solid #2aa767;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    padding: 10px 34px;
    border-radius: 8px;
}}
QPushButton#runBtn:hover {{ background-color: #269a5f; }}
QPushButton#runBtn:disabled {{ background-color: #2b3b33; color: #7d8a83; border-color: {BORDER}; }}

QPushButton#stopBtn {{
    background-color: #8a2f2a;
    border: 1px solid #c0483f;
    color: #ffffff;
    font-weight: 700;
    padding: 10px 22px;
    border-radius: 8px;
}}
QPushButton#stopBtn:disabled {{ background-color: #3a2b2b; color: #8a7d7d; border-color: {BORDER}; }}

QPushButton#gear {{ background: transparent; border: none; font-size: 15px; }}
QPushButton#gear:hover {{ color: {ACCENT}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM};
}}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT}; }}

QListWidget#settingsTabs {{
    background-color: transparent;
    border: none;
    outline: 0;
}}
QListWidget#settingsTabs::item {{
    height: 36px;
    padding-left: 12px;
    border-radius: 8px;
    margin: 2px 4px;
    color: {TEXT_DIM};
}}
QListWidget#settingsTabs::item:selected {{ background-color: {ACCENT_DIM}; color: {TEXT}; }}
QListWidget#settingsTabs::item:hover {{ background-color: #2d3240; }}

QListWidget, QTreeView, QTreeView#logs {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QListWidget::item:selected {{ background-color: {ACCENT_DIM}; }}

QPlainTextEdit, QTextEdit {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QStatusBar {{ background-color: {BG_RAIL}; color: {TEXT_DIM}; }}
QToolTip {{
    background-color: {BG_CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
}}
QScrollArea {{ border: none; background: transparent; }}
QWidget#pageRoot {{ background-color: {BG}; }}
"""
