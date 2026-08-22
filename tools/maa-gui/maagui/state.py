"""Application-level state shared between pages."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AppState(QObject):
    """Holds the active profile and GUI preferences (persisted via QSettings)."""

    profile_changed = Signal(str)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._profile = settings.value("profile", "default")

    @property
    def profile(self) -> str:
        return self._profile

    def set_profile(self, name: str):
        if name and name != self._profile:
            self._profile = name
            self.settings.setValue("profile", name)
            self.profile_changed.emit(name)
