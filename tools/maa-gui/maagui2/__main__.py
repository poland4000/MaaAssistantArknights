"""Entry point: `python3 -m maagui2` (run from a directory containing both
`maagui` and `maagui2` packages, e.g. the `gui/` dir of the bundle)."""

from __future__ import annotations

import sys
from pathlib import Path

# ensure the original maagui package is importable as a sibling
_PARENT = str(Path(__file__).resolve().parent.parent)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from maagui import maa as old_maa

from . import theme
from .shell import MainWindow


def main() -> int:
    QApplication.setOrganizationName("maa-gui")
    QApplication.setApplicationName("maagui2")
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("MaaGui2")
    app.setStyleSheet(theme.QSS)

    if not old_maa.maa_binary():
        QMessageBox.critical(
            None, "maa-cli not found",
            "maa-cli was not found in PATH.")
        return 1

    old_maa.ensure_dirs()
    settings = QSettings()
    from maagui.state import AppState
    state = AppState(settings)
    window = MainWindow(state)
    window.reload_profiles()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
