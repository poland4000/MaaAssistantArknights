"""Desktop integration for MaaGui3 — makes the window visible to the taskbar
and recoverable when it gets buried.

KDE Plasma (and other Wayland desktops) hide windows from the Task Manager
when their Wayland app_id / X11 WM_CLASS doesn't match an installed .desktop
file — the window still appears in Alt+Tab with a generic icon, but there is
no taskbar entry. So we:

  1. set the Qt desktop file name -> Wayland app_id "maagui3" / WM_CLASS,
  2. install ~/.local/share/applications/maagui3.desktop with
     StartupWMClass=maagui3 and the MAA icon,
  3. register a single-instance socket: launching maagui3 a second time
     raises the existing window instead of starting a duplicate,
  4. add a tray icon (see shell.py) as a guaranteed way to raise the window.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QIcon

SOCKET_NAME = "maagui3-raise"

PACKAGE_DIR = Path(__file__).resolve().parent
GUI_DIR = PACKAGE_DIR.parent          # tools/maa-gui
ICON_PATH = PACKAGE_DIR / "icon.png"


def desktop_exec() -> str:
    run_script = GUI_DIR / "run-maagui3.sh"
    if run_script.is_file():
        return str(run_script)
    launcher = GUI_DIR.parent / "launcher.sh"
    if launcher.is_file():
        return f"{launcher} maagui3"
    return "/usr/bin/env python3 -m maagui3"


DESKTOP_FILE_CONTENT = f"""[Desktop Entry]
Type=Application
Name=MAA
Comment=MaaAssistantArknights (maagui3)
Exec={desktop_exec()}
Icon={ICON_PATH}
Terminal=false
StartupWMClass=maagui3
Categories=Game;Utility;
"""


def install_desktop_file() -> None:
    """Write the user-level .desktop so Plasma can map app_id -> entry."""
    apps_dir = Path.home() / ".local" / "share" / "applications"
    target = apps_dir / "maagui3.desktop"
    try:
        if not target.exists() or target.read_text() != DESKTOP_FILE_CONTENT:
            apps_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(DESKTOP_FILE_CONTENT)
    except OSError:
        pass  # cosmetic only — tray + single-instance still work


def apply_app_identity(app) -> None:
    app.setApplicationName("maagui3")
    app.setDesktopFileName("maagui3")   # Wayland app_id
    if ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(ICON_PATH)))


def is_already_running() -> bool:
    """True when another maagui3 instance is up (we asked it to raise)."""
    sock = QLocalSocket()
    sock.connectToServer(SOCKET_NAME)
    if not sock.waitForConnected(300):
        return False
    sock.write(b"raise\n")
    sock.flush()
    sock.waitForBytesWritten(300)
    sock.disconnectFromServer()
    return True


def serve_raise_requests(callback) -> QLocalServer:
    """Listen for 'launch again' attempts and invoke `callback` (raise)."""
    QLocalServer.removeServer(SOCKET_NAME)  # clear a crashed instance's socket
    server = QLocalServer()
    server.listen(SOCKET_NAME)

    def _on_connection():
        conn = server.nextPendingConnection()
        if conn is None:
            return

        def _read():
            conn.readAll()
            callback()

        conn.readyRead.connect(_read)

    server.newConnection.connect(_on_connection)
    return server
