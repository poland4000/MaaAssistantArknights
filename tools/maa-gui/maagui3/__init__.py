"""MaaGui3 — a Linux (PySide6) re-implementation of the Windows MAA (WPF) UI.

Top-level tabs mirror the WPF RootView: Farming / Copilot / Toolbox / Settings.
Task logic is shared with the `maagui` package (maa-cli backend, PRTS search,
roster matching); this package owns the WPF-style presentation plus the fork
extras: Linux (gamescope) game launch/close and PRTS copilot search with
operator matching.
"""
