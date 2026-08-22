# MaaGui / MaaGui2 — Linux GUI for MaaAssistantArknights

A desktop GUI for [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights)
on Linux, built with **PySide6 (Qt 6)** on top of
[maa-cli](https://github.com/MaaAssistantArknights/maa-cli). Instead of talking
to MaaCore directly it generates maa-cli **task files** and runs them through
`maa run`, so the GUI stays in sync with everything MaaCore supports. It works
with any maa-cli backend (Waydroid/ADB, PlayCover, MuMuPro, or the **Window**
preset used by the Linux X11 window controller in this fork).

Two variants share the same code base:

- `maagui`  — the original: sidebar tabs (one-click daily, fight, roguelike,
  reclamation, copilot, PRTS search, daily, task files, connections, logs).
- `maagui2` — a Windows-MAA-styled re-skin (icon rail + vertical settings
  tabs) reusing the same pages, plus a Performance tab that tunes the battle
  screencap interval for fast-capture backends.

## Requirements

- Linux with a display server (X11 or Wayland) and Python 3.10+
- PySide6: `pip install --user PySide6`
- `maa` (maa-cli 0.4.8+) in `PATH` — this also provides MaaCore and MaaResource
  (run `maa install` / `maa update` as needed). The fork's MaaCore build must
  be the one in `maa`'s library directory to get the X11 window controller.

## Run (from the repo or any checkout)

```sh
./run.sh            # classic GUI
./run-maagui2.sh    # MAA-styled GUI
```

## Run (self-contained release zip)

Builds from the `ci-linux-gui` GitHub Action ship a zip containing
`libMaaCore.so` + `libMaaUtils.so`, the `MaaResource` pack (including the
`platform_diff/pc` overrides), the `maa` CLI binary, and this GUI. Unzip
anywhere and run:

```sh
./launcher.sh [maagui|maagui2]
```

The launcher points maa-cli at the bundle (`MAA_DATA_DIR`/`MAA_CONFIG_DIR`),
so profiles and task files land in `./config` next to the bundle. Pick the
**Window** preset in *Connections* (window title `Arknights`) to use the X11
window controller; maa-cli then auto-loads the bundled `platform_diff/pc`
resource pack.

## Notes specific to this fork

- The `platform_diff/pc` resource pack (repo `resource/platform_diff/pc/`)
  contains PC-captured templates and task overrides required by the X11
  window controller: main-menu entry buttons, raid/challenge difficulty
  switch, Infrast room labels. It is loaded automatically for the `Window`
  connection preset.
- The controller parks the in-game cursor at a fixed spot after clicks so the
  main-menu parallax effect doesn't destabilize template matching; the
  Performance tab in MaaGui2 lets you throttle how often the battle loop
  screenshots (fast X11 captures otherwise burn a core).
- GUI state lives in `~/.config/maa-gui/`; maa-cli data in
  `$MAA_DATA_DIR` (default `~/.local/share/maa`), profiles/tasks in
  `$MAA_CONFIG_DIR` (default `~/.config/maa`).

See `../LinuxWindowControllerTest/README.md` for details on the controller
itself (X11 attach, synthetic input, activation-click behaviour).