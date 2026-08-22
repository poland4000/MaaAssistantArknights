"""Dark theme for MaaGui, loosely inspired by the Windows MAA GUI."""

ACCENT = "#3d9bfa"
ACCENT_DIM = "#2b6cb0"
BG = "#1c2027"
BG_ELEV = "#232833"
BG_INPUT = "#2a3040"
BORDER = "#343b4a"
TEXT = "#dfe4ee"
TEXT_DIM = "#8b93a5"
OK = "#3ddc84"
WARN = "#f5b041"
ERR = "#f2645a"

QSS = f"""
* {{
    font-family: "Noto Sans", "Cantarell", "DejaVu Sans", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget {{
    background-color: {BG};
}}
QWidget#sidebar {{
    background-color: {BG_ELEV};
    border-right: 1px solid {BORDER};
}}
QListWidget#sidebar {{
    background-color: transparent;
    border: none;
    outline: 0;
    padding: 8px 4px;
}}
QListWidget#sidebar::item {{
    height: 38px;
    padding-left: 14px;
    border-radius: 8px;
    margin: 2px 6px;
    color: {TEXT_DIM};
}}
QListWidget#sidebar::item:selected {{
    background-color: {ACCENT_DIM};
    color: {TEXT};
}}
QListWidget#sidebar::item:hover {{
    background-color: #2d3444;
}}
QListWidget#sidebar::item:selected:hover {{
    background-color: {ACCENT_DIM};
}}
QLabel#appTitle {{
    font-size: 16px;
    font-weight: 700;
    padding: 14px 16px 6px 16px;
}}
QLabel#appSub {{
    font-size: 11px;
    color: {TEXT_DIM};
    padding: 0 16px 10px 16px;
}}
QPushButton {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background-color: #232a38; }}
QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; }}
QPushButton#primary {{
    background-color: {ACCENT};
    color: #0d1420;
    font-weight: 600;
    border: none;
}}
QPushButton#primary:hover {{ background-color: #5fadff; }}
QPushButton#primary:disabled {{ background-color: #2b4a6d; color: #6b7a8f; }}
QPushButton#danger {{ background-color: #4a2a2e; border-color: #6b3a40; color: {ERR}; }}
QPushButton#danger:hover {{ border-color: {ERR}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {BG_ELEV};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM};
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: none;
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    background-color: {BG_ELEV};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {TEXT_DIM};
    font-weight: 600;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: {BG_ELEV};
}}
QTabBar::tab {{
    padding: 7px 16px;
    color: {TEXT_DIM};
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT_DIM}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{
    background: {BORDER}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QPlainTextEdit#logView {{
    background-color: #14171d;
    border: 1px solid {BORDER};
    border-radius: 8px;
    font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}}
QPlainTextEdit#tomlEdit {{
    font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}}
QStatusBar {{
    background-color: {BG_ELEV};
    border-top: 1px solid {BORDER};
    color: {TEXT_DIM};
}}
QStatusBar::item {{ border: none; }}
QToolTip {{
    background-color: {BG_ELEV};
    border: 1px solid {BORDER};
    color: {TEXT};
    padding: 4px 8px;
}}
QListWidget#taskList {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QListWidget#taskList::item {{ padding: 6px 10px; border-radius: 4px; }}
QListWidget#taskList::item:selected {{ background-color: {ACCENT_DIM}; }}
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {BG_INPUT};
    text-align: center;
    color: {TEXT};
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 5px; }}
QSplitter::handle {{ background: {BORDER}; }}
"""
