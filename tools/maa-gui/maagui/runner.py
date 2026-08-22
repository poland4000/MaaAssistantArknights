"""TaskRunner: drives maa-cli subprocesses with live log streaming and cancel.

One shared TaskRunner lives in the main window; every page starts runs through
it. Only one run may be active at a time.
"""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from . import maa


class TaskRunner(QObject):
    """Runs `maa run <task> -p <profile> --batch` via QProcess."""

    log_line = Signal(str)          # one log line (may be partially colored)
    started = Signal(str)           # task name
    finished = Signal(int, str)     # exit code, summary message
    running_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: QProcess | None = None
        self._buf = ""
        self._task = ""
        self._start_ts = 0.0
        self._user_stopped = False
        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.timeout.connect(self._force_kill)

    # -- state --------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._proc is not None

    @property
    def task_name(self) -> str:
        return self._task

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start_ts if self.running else 0.0

    # -- control ------------------------------------------------------------

    def start(self, task: str, profile: str) -> bool:
        return self.start_command(["run", task, "-p", profile, "--batch"], label=task)

    def start_command(self, args: list[str], label: str = "") -> bool:
        """Run an arbitrary maa-cli invocation (e.g. `maa paradoxcopilot FILE`)."""
        if self.running:
            return False
        bin_ = maa.maa_binary()
        if not bin_:
            self.finished.emit(-1, "maa-cli not found in PATH")
            return False
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_ready_read)
        proc.finished.connect(self._on_finished)
        proc.start(bin_, args)
        if not proc.waitForStarted(3000):
            self.finished.emit(-1, f"failed to start: {proc.errorString()}")
            return False
        self._proc = proc
        self._task = label or " ".join(args)
        self._buf = ""
        self._start_ts = time.monotonic()
        self._user_stopped = False
        self.started.emit(self._task)
        self.running_changed.emit(True)
        return True

    def stop(self):
        """Graceful stop (SIGTERM), then SIGKILL after 4s."""
        if not self.running:
            return
        self._user_stopped = True
        self.log_line.emit(">>> Stop requested, terminating…")
        self._proc.terminate()
        self._kill_timer.start(4000)

    def shutdown(self):
        """Synchronously kill the child process tree (used on app close).

        The window close event leaves no event loop running, so the kill
        timer from :meth:`stop` would never fire — the orphaned `maa` child
        would keep the terminal's process group alive. Terminate, wait,
        then SIGKILL the process and its children.
        """
        if not self.running:
            return
        self._kill_timer.stop()
        proc = self._proc
        pid = proc.processId()
        self.log_line.emit(">>> Closing app, terminating task…")
        proc.terminate()
        if not proc.waitForFinished(3000):
            proc.kill()
            proc.waitForFinished(2000)
        # AppImage-style wrappers may leave grandchildren behind
        if pid > 0:
            try:
                children = (Path(f"/proc/{pid}/task/{pid}/children")
                            .read_text().split())
            except OSError:
                children = []
            for cpid in children:
                try:
                    os.kill(int(cpid), signal.SIGKILL)
                except (OSError, ValueError):
                    pass
        self._proc = None
        self._user_stopped = False
        self.running_changed.emit(False)

    def _force_kill(self):
        if self.running:
            self.log_line.emit(">>> Process did not exit, killing…")
            self._proc.kill()

    # -- I/O -----------------------------------------------------------------

    def _on_ready_read(self):
        data = bytes(self._proc.readAllStandardOutput())
        text = data.decode("utf-8", errors="replace")
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip("\r")
            if line.strip():
                self.log_line.emit(line)

    def _on_finished(self, code: int, status: QProcess.ExitStatus):
        if self._buf.strip():
            self.log_line.emit(self._buf.strip())
        self._buf = ""
        self._kill_timer.stop()
        self._proc = None
        if self._user_stopped:
            summary = f"Task '{self._task}' stopped by user"
            ok = False
        else:
            ok = code == 0 and status == QProcess.ExitStatus.NormalExit
            if ok:
                summary = f"Task '{self._task}' finished successfully"
            else:
                summary = f"Task '{self._task}' failed (exit code {code})"
        self.log_line.emit(f">>> {summary}")
        self.finished.emit(code, summary)
        self.running_changed.emit(False)
