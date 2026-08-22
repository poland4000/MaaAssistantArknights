<!-- markdownlint-disable -->

<div align="center">

<img alt="LOGO" src="./docs/.vuepress/public/images/maa-logo_512x512.png" width="256" height="256" />

# MAA

<br>
<div>
    <img alt="C++" src="https://img.shields.io/badge/C++-20-%2300599C?logo=cplusplus">
    <img alt="platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blueviolet">
</div>
<div>
    <img alt="license" src="https://img.shields.io/github/license/MaaAssistantArknights/MaaAssistantArknights">
    <img alt="commit" src="https://img.shields.io/github/commit-activity/m/MaaAssistantArknights/MaaAssistantArknights?color=%23ff69b4">
</div>
<div>
    <img alt="stars" src="https://img.shields.io/github/stars/MaaAssistantArknights/MaaAssistantArknights?style=social">
    <img alt="GitHub all releases" src="https://img.shields.io/github/downloads/MaaAssistantArknights/MaaAssistantArknights/total?style=social">
</div>
<div>
    <a href="https://deepwiki.com/MaaAssistantArknights/MaaAssistantArknights"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</div>
    <a href="https://trendshift.io/repositories/979" target="_blank"><img src="https://trendshift.io/api/badge/repositories/979" alt="MaaAssistantArknights%2FMaaAssistantArknights | Trendshift" width="250" height="55" style="width: 250px; height: 55px;" /></a>
<div>
</div>
<br>

<!-- markdownlint-restore -->

[简体中文](https://docs.maa.plus/zh-cn/) | [繁體中文](https://docs.maa.plus/zh-tw/) | [English](https://docs.maa.plus/en-us/) | [日本語](https://docs.maa.plus/ja-jp/) | [한국어](https://docs.maa.plus/ko-kr/)

MAA 的意思是 MAA Assistant Arknights

一款明日方舟游戏小助手

基于图像识别技术，一键完成全部日常任务！

绝赞更新中 ✿✿ヽ(°▽°)ノ✿

</div>

## FORK: Linux X11 window-client automation

This fork adds a **Windows-style window controller for Linux**: MAA attaches to
the Arknights **PC client** (YoStar EN, running under Wine/Proton) by window
title and drives it with **synthetic X11 input — the mouse cursor is never
moved**. Everything else (tasks, resource packs, CLI, GUI) works on top of
that.

*Caveat for a wild world: this fork is a personal, working experiment. It
has been verified on one machine (Fedora/KWin, 1920×1080, EN client, HDR).
It is *not* battle-tested across distros, GPUs, or display setups, and it
is *not* PR-ready for upstream yet.*

### What this fork adds

- `LinuxWindowController` (X11): attach by exact window title, screencap via
  `XGetImage`, click/swipe via `XSendEvent`. No cursor relocation — the game
  window stays exactly where you left it. Keyboard input works, and a
  `focus_for_keys` flag can move input focus to the game before key events.
- **Activation-click handling**: the 2026-08 EN client swallows the click
  that activates an unfocused window. Start-button clicks are re-sent when
  the window is unfocused; menu-entry and stage-navigation clicks self-heal
  via re-detection.
- **Cursor parking**: after every click, the in-game cursor is parked at a
  fixed spot (bottom-left, near the BREAKING NEWS banner). The main menu has
  a cursor-following parallax ("gyroscope") effect; parking keeps template
  scores stable instead of drifting with the last click position.
- **`platform_diff/pc` resource pack**: PC-captured templates + task
  overrides for the windowed client — main-menu entry buttons, raid/challenge
  mode switch (red "Start Challenge" button), Infrast facilities, battle-loop
  screencap throttling. Auto-loaded when the connection preset is `Window`.
- **Two GUIs** (`tools/maa-gui`): the classic tabbed `maagui` and the
  MAA-styled `maagui2` (settings tabs, screencap-interval knob, PRTS search).
- **Self-contained CI bundle**: a zip with libMaaCore + libMaaUtils, the
  full MaaResource (incl. the pc pack), the **fork's maa-cli** (see below —
  upstream's does *not* know the `Window` preset), both GUIs, and a
  `launcher.sh`.

### Setup

**Use the CI bundle** (Actions → `build-linux-gui` → artifact `maa-linux-gui`):

```sh
# the artifact download is one zip containing the maa-linux/ bundle
unzip maa-linux-gui.zip -d .
cd maa-linux
./launcher.sh                # GUI; uses the bundled maa, libs, resources
```

`launcher.sh` points `MAA_DATA_DIR`/`MAA_CONFIG_DIR`/`MAA_CACHE_DIR` at the
bundle, so profiles and task files land in `./config` next to it. Required:
a Linux display (X11 or XWayland) and Python 3.10+ with PySide6
(`pip install --user PySide6`).

**Build from source**: follow the upstream Linux build guide; you additionally
need `libx11-dev` (X11 headers) so the controller gets compiled in. MaaCore
attaches via the `AsstAttachWindowByName` API.

**maa-cli note**: the `Window` connection preset lives in
[poland4000/maa-cli](https://github.com/poland4000/maa-cli) `feat/window-preset`.
Upstream maa-cli ignores the preset (`Unknown connection preset: Window`) and
falls back to ADB, so *the fork maa-cli is required* for window control. The
CI bundle builds it for you.

**First run (GUI)**: Connections tab → profile `default` is auto-created.
Set **Preset = `Window`**, **Window title = `Arknights`**, **Global resource =
`YoStarEN`** (default), Save. Check device should find the window.

### Arknights client settings (important)

- **UI scale 100%** (game display settings) — any scaling breaks every
  template.
- **Windowed, 1920×1080** (launcher settings). MAA requires exactly 16:9 and
  at least 1280×720; a non-16:9 window (e.g. 1920×1052 with decorations)
  fails attach. Use the launcher's resolution list, not arbitrary resizing.
- **Must be a real window**: never minimized (controller can't capture an
  unmapped window), never compositor-overlay fullscreen. Covered by other
  windows is fine.
- **Cursor at bottom-left before starting dailies**: MAA parks the in-game
  cursor to the bottom-left corner (720p ≈ 8,668 — near the BREAKING NEWS
  marker) after every click. Templates were captured with the cursor there,
  so before the *first* run after launching the game, leave the in-game
  cursor at bottom-left (or just start — detection retries settle the
  parallax after the first click parks it).

### HDR / SDR and the pc resource pack

The `platform_diff/pc` templates were **captured on an HDR display**. On an
SDR screen, template scores drop and some screens (raid switch especially)
may fail.

- **Workaround**: `./toggle-pc-pack.sh off` (repo or bundle) drops the pack
  and falls back to MAA's default Android-tuned templates;
  `MAA_PC_PACK=0 ./launcher.sh` does it for one session; `on` restores.
- **Honest statement**: toggling off is a fallback, not a real SDR config —
  the base pack lacks windowed-client-specific templates (EN Terminal,
  challenge-mode Start, raid switch), so those screens go half-blind. Making
  SDR a first-class citizen requires **re-capturing the pc pack on an SDR
  machine** (controller screenshots, not Spectacle — cross-pipeline captures
  score ~0.6). If you do this, PR the templates back and the HDR capture
  issue goes away for everyone.

### Known limitations

- **X11 only for the window controller** (XGetImage + XSendEvent). Native
  Wayland windows need a future PipeWire/uinput path; Wine/Proton windows
  under XWayland work (that's what this was built against).
- **Battles**: the roguelike/copilot/SSS fight loops are throttled via the
  pc-pack `config.json` (defaults: roguelike 100 ms, copilot/SSS 33 ms) to
  keep CPU sane with ~10 ms screenshots; lower if a mission misses a timing
  window, raise if CPU is a concern (GUI Performance tab in `maagui2`).
  MAA's recognition must be able to read the PC renders — it was tuned on
  this one machine.
- **One run at a time**, same as upstream (the device is busy).
- **Language**: GUIs and resource overrides target the EN client; CN/JP/KR
  clients work with the matching `global_resource` but the pc-pack overrides
  assume the EN layout.
- **Network**: PRTS search and `maa://` copilot download need network access
  at run time.

## 下载与安装

请阅读 [文档](https://docs.maa.plus/zh-cn/manual/newbie.html) 后前往 [官网](https://maa.plus) 或 [Releases](https://github.com/MaaAssistantArknights/MaaAssistantArknights/releases) 下载，并参考 [新手上路](https://docs.maa.plus/zh-cn/manual/newbie.html) 进行安装。

## 亮点功能

- 理智作战，掉落识别及上传 [企鹅物流](https://penguin-stats.cn/)，[一图流](https://ark.yituliu.cn/)
- 智能基建换班，自动计算干员效率，单设施内最优解；同时也支持 [自定义排班](https://docs.maa.plus/zh-cn/protocol/base-scheduling-schema.html)
- 自动公招，可选使用加急许可，一次全部刷完！公招数据自动上传 [企鹅物流](https://penguin-stats.cn/result/stage/recruit/recruit)，[一图流](https://ark.yituliu.cn/survey/maarecruitdata)
- 支持手动识别公招界面，方便对高星公招做出选择 ~~（你的这个高资回费出的是推王呢还是推王呢）~~
- 支持识别干员列表，统计已有和未有干员及潜能，并在公招识别显示
- 支持识别养成材料，并导出至 [企鹅物流刷图规划](https://penguin-stats.cn/planner)、[明日方舟工具箱](https://arkntools.app/#/material)、[ARK-NIGHTS 干员培养表](https://ark-nights.com/settings)
- 访问好友、收取信用及购物、领取日常奖励等，一键全日常自动长草
- 肉鸽全自动刷源石锭和等级，自动烧水和凹直升，智能识别干员及练度
- 选择作业 JSON 文件，自动抄作业， [视频演示](https://www.bilibili.com/video/BV1H841177Fk/)
- 支持 C, Python, Java, Rust, Golang, Java HTTP, Rust HTTP 等多种接口，方便集成调用，自定义你的 MAA！

<!-- markdownlint-disable -->

<details><summary>话不多说，看图！</summary>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/.vuepress/public/images/zh-cn/readme/1-dark.png">
  <img alt="zh1" src="./docs/.vuepress/public/images/zh-cn/readme/1-light.png">
</picture>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/.vuepress/public/images/zh-cn/readme/2-dark.png">
  <img alt="zh2" src="./docs/.vuepress/public/images/zh-cn/readme/2-light.png">
</picture>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/.vuepress/public/images/zh-cn/readme/3-dark.png">
  <img alt="zh3" src="./docs/.vuepress/public/images/zh-cn/readme/3-light.png">
</picture>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/.vuepress/public/images/zh-cn/readme/4-dark.png">
  <img alt="zh4" src="./docs/.vuepress/public/images/zh-cn/readme/4-light.png">
</picture>

</details>

<!-- markdownlint-restore -->

## 使用说明

### 功能介绍

请参阅 [用户手册](https://docs.maa.plus/zh-cn/manual/)。

### 外服支持

目前国际服（美服）、日服、韩服、繁中服的绝大部分功能均已支持。但由于外服用户较少及项目人手不足，很多功能并没有进行全面的测试，所以请自行体验。  
若您遇到了 Bug，或对某个功能有强需求，欢迎在 [Issues](https://github.com/MaaAssistantArknights/MaaAssistantArknights/issues) 和 [讨论区](https://github.com/MaaAssistantArknights/MaaAssistantArknights/discussions) 催更；或加入我们一起建设 MAA！请参阅 [外服适配教程](https://docs.maa.plus/zh-cn/develop/overseas-client-adaptation.html)

### CLI 支持

MAA 支持命令行界面（CLI）操作，支持 Linux，macOS 和 Windows，可用于自动化脚本或在无图形界面的服务器上使用。请参阅 [CLI 使用指南](https://docs.maa.plus/zh-cn/manual/cli/)

## 加入我们

### 主要关联项目

- 全新框架：[MaaFramework](https://github.com/MaaXYZ/MaaFramework)
- [作业站](https://prts.plus) 前端：[zoot-plus-frontend](https://github.com/ZOOT-Plus/zoot-plus-frontend)
- [作业站](https://prts.plus) 后端：[ZootPlusBackend](https://github.com/ZOOT-Plus/ZootPlusBackend)
- [官网](https://maa.plus)：[前端](https://github.com/MaaAssistantArknights/maa-website)
- 深度学习：[MaaAI](https://github.com/MaaAssistantArknights/MaaAI)

### 多语言 (i18n)

MAA 以中文（简体）为第一语言，翻译词条均以中文（简体）为准。

### 参与开发

请参阅 [开发指南](https://docs.maa.plus/zh-cn/develop/development.html)。

### API

- [C 接口](include/AsstCaller.h)：[集成示例](src/Cpp/main.cpp)
- [Python 接口](src/Python/asst/asst.py)：[集成示例](src/Python/sample.py)
- [Golang 接口](src/Golang)：[集成示例](src/Golang/maa/maa.go)
- [Dart 接口](src/Dart)
- [Java 接口](src/Java/src/main/java/com/iguigui/maaj/easySample/MaaCore.java)：[集成示例](src/Java/src/main/java/com/iguigui/maaj/easySample/MaaJavaSample.java)
- [Java HTTP 接口](src/Java/Readme.md)
- [Rust 接口](src/Rust/src/maa_sys)：[HTTP 接口](src/Rust)
- [TypeScript 接口](https://github.com/MaaAssistantArknights/MaaX/tree/main/packages/main/coreLoader)
- [Woolang 接口](src/Woolang/maa.wo)：[集成示例](src/Woolang/demo.wo)
- [集成文档](https://docs.maa.plus/zh-cn/protocol/integration.html)
- [回调消息协议](https://docs.maa.plus/zh-cn/protocol/callback-schema.html)
- [任务流程协议](https://docs.maa.plus/zh-cn/protocol/task-schema.html)
- [自动战斗协议](https://docs.maa.plus/zh-cn/protocol/copilot-schema.html)

### 外服适配

请参阅 [外服适配教程](https://docs.maa.plus/zh-cn/develop/overseas-client-adaptation.html)，对于国服已支持的功能，绝大部分的外服适配工作仅需要截图 + 简单的 JSON 修改即可。

### Issue bot

请参阅 [Issue Bot 使用方法](https://docs.maa.plus/zh-cn/develop/issue-bot-usage.html)

## 致谢

### 开源库

- 图像识别库：[opencv](https://github.com/opencv/opencv.git)
- ~~文字识别库：[chineseocr_lite](https://github.com/DayBreak-u/chineseocr_lite.git)~~
- 文字识别库：[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- 深度学习部署库：[FastDeploy](https://github.com/PaddlePaddle/FastDeploy)
- 机器学习加速器：[onnxruntime](https://github.com/microsoft/onnxruntime)
- ~~关卡掉落识别：[企鹅物流识别](https://github.com/penguin-statistics/recognizer)~~
- 地图格子识别：[Arknights-Tile-Pos](https://github.com/yuanyan3060/Arknights-Tile-Pos)
- C++ JSON 库：[meojson](https://github.com/MistEO/meojson.git)
- C++ 运算符解析器：[calculator](https://github.com/kimwalisch/calculator)
- ~~C++ base64 编解码：[cpp-base64](https://github.com/ReneNyffenegger/cpp-base64)~~
- C++ 解压压缩库：[zlib](https://github.com/madler/zlib)
- C++ Gzip 封装：[gzip-hpp](https://github.com/mapbox/gzip-hpp)
- 安卓触控事件器：[Minitouch](https://github.com/DeviceFarmer/minitouch)
- 安卓触控事件器：[MaaTouch](https://github.com/MaaAssistantArknights/MaaTouch)
- WPF MVVM 框架：[Stylet](https://github.com/canton7/Stylet)
- WPF 控件库：[HandyControl](https://github.com/HandyOrg/HandyControl) -> [HandyControls](https://github.com/ghost1372/HandyControls)
- C# 日志：[Serilog](https://github.com/serilog/serilog)
- C# JSON 库：[Newtonsoft.Json](https://github.com/JamesNK/Newtonsoft.Json) & [System.Text.Json](https://github.com/dotnet/runtime)
- ~~下载器：[aria2](https://github.com/aria2/aria2)~~

### 数据源

- ~~公开招募数据：[明日方舟工具箱](https://www.bigfun.cn/tools/aktools/hr)~~
- ~~干员及基建数据：[PRTS Wiki](http://prts.wiki/)~~
- 关卡数据：[企鹅物流数据统计](https://penguin-stats.cn/)
- 游戏数据及资源：[明日方舟客户端素材](https://github.com/yuanyan3060/ArknightsGameResource)
- 游戏数据：[《明日方舟》Yostar游戏数据](https://github.com/ArknightsAssets/ArknightsGamedata)

### 贡献/参与者

感谢所有参与到开发/测试中的朋友们，是大家的帮助让 MAA 越来越好！ (\*´▽｀)ノノ

[![Contributors](https://contributors-img.web.app/image?repo=MaaAssistantArknights/MaaAssistantArknights&max=105&columns=15)](https://github.com/MaaAssistantArknights/MaaAssistantArknights/graphs/contributors)

## 声明

- 本软件使用 [GNU Affero General Public License v3.0 only](https://spdx.org/licenses/AGPL-3.0-only.html) 开源，并附带额外 [用户协议](https://github.com/MaaAssistantArknights/MaaAssistantArknights/blob/dev-v2/terms-of-service.md)。
- 本软件 logo 并非使用 AGPL 3.0 协议开源，[耗毛](https://weibo.com/u/3251357314)、vie 两位画师及软件全体开发者保留所有权利。不得以 AGPL 3.0 协议已授权为由在未经授权的情况下使用本软件 logo，不得在未经授权的情况下将本软件 logo 用于任何商业用途。
- 本软件开源、免费，仅供学习交流使用。若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。

### DirectML 支持说明

本软件支持 GPU 加速功能，其在 Windows 平台上依赖于 Microsoft 提供的独立组件 [DirectML](https://learn.microsoft.com/en-us/windows/ai/directml/)。DirectML 并非本项目的开源部分，也不受 AGPL 3.0 的约束。为方便用户，我们随安装包附带了一个未经修改的 DirectML.dll 文件。如果您无需 GPU 加速功能，可安全删除该 DLL 文件，软件的核心功能仍可正常运行。

## 广告

用户交流 QQ 群：[MAA 使用 & 粥游交流 QQ 群](https://api.maa.plus/MaaAssistantArknights/api/qqgroup/index.html)  
Discord 服务器: [邀请链接](https://discord.gg/23DfZ9uA4V)  
用户交流 TG 群：[Telegram 群](https://t.me/+Mgc2Zngr-hs3ZjU1)  
自动战斗 JSON 作业分享：[prts.plus](https://prts.plus)  
Bilibili 直播间：[MrEO 直播间](https://live.bilibili.com/2808861) 直播敲代码 & [MAA-Official 直播间](https://live.bilibili.com/27548877) 游戏/杂谈

技术群（舟无关、禁水）：[内卷地狱！(QQ 群)](https://jq.qq.com/?_wv=1027&k=ypbzXcA2)  
开发者群：[QQ 群](https://jq.qq.com/?_wv=1027&k=JM9oCk3C)

如果觉得软件对你有帮助，帮忙点个 Star 吧！~（网页最上方右上角的小星星），这就是对我们最大的支持了！
