"""Entry point: `python3 -m maagui`."""

from __future__ import annotations

import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from . import maa, theme
from .main_window import MainWindow
from .state import AppState


def main() -> int:
    QApplication.setOrganizationName("maa-gui")
    QApplication.setApplicationName("maagui")
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("MaaGui")
    app.setStyleSheet(theme.QSS)

    settings = QSettings()
    state = AppState(settings)

    if not maa.maa_binary():
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "maa-cli not found",
            "maa-cli was not found in PATH. Install it first, see:\n"
            "https://github.com/MaaAssistantArknights/maa-cli")
        return 1

    maa.ensure_dirs()
    window = MainWindow(state)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
