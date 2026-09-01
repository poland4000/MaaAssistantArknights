"""Entry point: `python3 -m maagui3` (run from a directory containing the
`maagui` and `maagui3` packages, e.g. the `gui/` dir of the bundle)."""

from __future__ import annotations

import sys
from pathlib import Path

# the original maagui package (backend logic) must be importable as a sibling
_PARENT = str(Path(__file__).resolve().parent.parent)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from maagui import maa as old_maa

from . import desktop, theme
from .shell import MainWindow


def main() -> int:
    QApplication.setOrganizationName("maa-gui")
    QApplication.setApplicationName("maagui3")
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("MAA")
    app.setStyle("Fusion")
    app.setStyleSheet(theme.QSS)
    f = app.font()
    f.setPointSize(9)
    f.setFamily(theme.FONT_FAMILY)
    app.setFont(f)

    # taskbar / app-id integration + single-instance raise
    desktop.apply_app_identity(app)
    desktop.install_desktop_file()
    if desktop.is_already_running():
        return 0

    if not old_maa.maa_binary():
        QMessageBox.critical(None, "maa-cli not found", "maa-cli was not found in PATH.")
        return 1

    old_maa.ensure_dirs()
    settings = QSettings()
    _inherit_profile(settings)

    from maagui.state import AppState

    state = AppState(settings)
    window = MainWindow(state)
    window.show()
    desktop.serve_raise_requests(window.raise_to_front)
    return app.exec()


def _inherit_profile(settings: QSettings) -> None:
    """First run of maagui3: pick a sensible profile instead of falling back
    to "default". Inherit the last-used profile from maagui2/maagui, else
    prefer the Window-preset profile (the fork's Linux game flow). Never
    overrides a profile the user already picked in maagui3."""
    if settings.value("profile", "") not in ("", None):
        return
    profiles = old_maa.list_profiles()
    if not profiles:
        return
    for app in ("maagui2", "maagui"):
        prev = str(QSettings("maa-gui", app).value("profile", ""))
        if prev in profiles:
            settings.setValue("profile", prev)
            return
    for name in profiles:
        conn = old_maa.read_profile(name).get("connection", {})
        if str(conn.get("preset", "")).lower() == "window":
            settings.setValue("profile", name)
            return
    settings.setValue("profile", profiles[0])


if __name__ == "__main__":
    sys.exit(main())
