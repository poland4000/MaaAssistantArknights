# MaaGui3 — Linux GUI for MaaAssistantArknights

A desktop GUI for [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights)
on Linux, built with **PySide6 (Qt 6)** on top of
[maa-cli](https://github.com/MaaAssistantArknights/maa-cli). Instead of talking
to MaaCore directly it generates maa-cli **task files** and runs them through
`maa run`, so the GUI stays in sync with everything MaaCore supports. It works
with any maa-cli backend (Waydroid/ADB, PlayCover, MuMuPro, or the **Window**
preset used by the Linux X11 window controller in this fork).

**MaaGui3** is the bundle's GUI — a 1:1 re-implementation of the Windows (WPF)
MAA UI, plus this fork's Linux extras:

- The Windows layout: **Farming / Copilot / Toolbox / Settings** top tabs, the
  task checklist with per-task gear settings (General/Advanced), "Then"
  post-actions, the Link Start! button, and the timestamped log column.
- **Linux game launch/close** (Game settings + status bar): runs the Windows
  Arknights client in an isolated **gamescope** (or Xvfb) session via
  `../isolated-game/arknights-isolated.sh`, watches its status, and closes it —
  so MAA can drive the game without focus stealing.
- **PRTS copilot search with operator matching** (Copilot → PRTS Search):
  search prts.plus for stage clears, match results against your own roster
  (OperBox recognition), and queue the ones you can actually run.
- Toolbox recognitions (Recruitment / OperBox / Depot), a task-file editor,
  full logs, and the battle screencap performance knob (Settings →
  Performance).

> Legacy variants kept for development: `maagui` (classic sidebar tabs — also
> the backend library maagui3 imports for maa-cli/PRTS logic) and `maagui2`
> (an earlier WPF-inspired re-skin). The bundle launcher starts **maagui3**
> only; from a repo checkout you can still `./run.sh` / `./run-maagui2.sh` /
> `./run-maagui3.sh` to compare.

## Requirements

- Linux with a display server (X11 or Wayland) and Python 3.10+
- PySide6: `pip install --user PySide6`
- `maa` (maa-cli 0.4.8+) in `PATH` — this also provides MaaCore and MaaResource
  (run `maa install` / `maa update` as needed). The fork's MaaCore build must
  be the one in `maa`'s library directory to get the X11 window controller.
- For the gamescope isolation (recommended for the PC client):
  `gamescope` (or `xorg-x11-server-Xvfb`), `xdotool`, and Wine/GE-Proton with
  the Arknights client installed.

## Run (from the repo or any checkout)

```sh
./run-maagui3.sh    # MaaGui3 — the WPF-1:1 GUI (bundle default)
```

## Run (self-contained release bundle)

Builds from the `ci-linux-gui` GitHub Action ship a bundle containing
`libMaaCore.so` + `libMaaUtils.so`, the `MaaResource` pack (including the
`platform_diff/pc` overrides), the `maa` CLI binary, the gamescope launcher
(`isolated-game/`), and this GUI. Unzip anywhere and run:

```sh
./launcher.sh
```

The launcher points maa-cli at the bundle (`MAA_DATA_DIR`/`MAA_CONFIG_DIR`),
so profiles and task files land in `./config` next to the bundle. Pick the
**Window** preset in *Settings → Connection* (window title `Arknights`) to
use the X11 window controller; maa-cli then auto-loads the bundled
`platform_diff/pc` resource pack.

## Recommended PC flow (gamescope)

1. Install the Arknights PC client under Steam/GE-Proton, then in maagui3 open
   *Settings → Game*, pick the isolation mode (gamescope window / hidden /
   Xvfb), runner and resolution, and press **Launch game** — the launcher
   starts the client on its own display and writes the matching
   `window_name` (e.g. `:1:Arknights`) into the active profile.
2. The status bar shows `game: running (N)`; **Close game** stops the session
   (`arknights-isolated.sh --stop`, falling back to closing the window).
3. Set *Connection preset = Window* and Link Start — MAA attaches *inside* the
   isolated session, so the game never steals focus from your desktop.

## Notes specific to this fork

- The `platform_diff/pc` resource pack (repo `resource/platform_diff/pc/`)
  contains PC-captured templates and task overrides required by the X11
  window controller: main-menu entry buttons, raid/challenge difficulty
  switch, Infrast room labels. It is loaded automatically for the `Window`
  connection preset.
  **Disabling it:** the templates were tuned on an HDR display; on SDR
  screens the default (Android-tuned) templates may match better. Run
  `./toggle-pc-pack.sh off` (from a repo checkout *or* the bundle), or set
  `MAA_PC_PACK=0` when launching the bundle. `on` restores it. Systems using
  ADB/Waydroid presets never load the pack and don't need this.
- The controller parks the in-game cursor at a fixed spot after clicks so the
  main-menu parallax effect doesn't destabilize template matching; Settings →
  Performance lets you throttle how often the battle loop screenshots (fast
  X11 captures otherwise burn a core).
- GUI state lives in `~/.config/maa-gui/`; maa-cli data in
  `$MAA_DATA_DIR` (default `~/.local/share/maa`), profiles/tasks in
  `$MAA_CONFIG_DIR` (default `~/.config/maa`).

See `../LinuxWindowControllerTest/README.md` for details on the controller
itself (X11 attach, synthetic input, activation-click behaviour) and
`../isolated-game/` for the gamescope launcher.
