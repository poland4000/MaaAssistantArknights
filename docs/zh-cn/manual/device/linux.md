---
order: 3
icon: teenyicons:linux-alt-solid
---

# Linux 模拟器与容器

## 准备工作

以下安装方式任选其一即可：

### 使用 maa-cli

[maa-cli](https://github.com/MaaAssistantArknights/maa-cli) 是一个使用 Rust 编写的简单 MAA 命令行工具。相关安装与使用教程请阅读 [CLI 使用指南](../cli/)。

### 使用 Wine

MAA WPF GUI 当前可以通过 Wine 运行。MAA 已采用自包含部署方式，内置了 .NET 运行时。

#### 安装步骤

:::: steps

1. 安装 Visual C++ Redistributable

   下载并安装 [Visual C++ 可再发行程序包](https://aka.ms/vc14/vc_redist.x64.exe)：

   ```shell
   wine vc_redist.x64.exe
   ```

   ::: tip
   `DependencySetup_依赖库安装.bat` 基于 winget 和 Windows 提权机制，通常无法在 Wine 中正常工作，因此需要手动安装运行库。
   :::

2. 下载 MAA

   下载 Windows 版 MAA，解压后运行 `wine MAA.exe`。

::::

::: info 注意
需要在连接设置中将 ADB 路径设置为 [Windows 版 `adb.exe`](https://dl.google.com/android/repository/platform-tools-latest-windows.zip)。

如果您需要通过 ADB 连接 USB 设备，请先在 Wine 外运行 `adb start-server`，即通过 Wine 连接原生 ADB server。
:::

#### 使用 Linux 原生 MaaCore（实验性功能）

下载 [MAA Wine Bridge](https://github.com/MaaAssistantArknights/MaaAssistantArknights/tree/dev/src/MaaWineBridge) 源码并构建，用生成的 `MaaCore.dll`（ELF 文件）替换 Windows 版本，并将 Linux 原生动态库（`libMaaCore.so` 以及依赖）放在同一目录下。

此时通过 Wine 运行 `MAA.exe`，将会加载 Linux 原生动态库。

::: info 注意
使用 Linux 原生 MaaCore 时，需要在连接设置中将 ADB 路径设置为 Linux 原生 ADB。
:::

#### Linux 桌面整合（实验性功能）

桌面整合提供原生桌面通知支持，以及将 fontconfig 字体配置映射到 WPF 的功能。

将 MAA Wine Bridge 生成的 `MaaDesktopIntegration.so` 放到 `MAA.exe` 同目录下即可启用。

#### 已知问题

- Wine DirectWrite 强制启用 hinting，并且不将 DPI 传递给 FreeType，导致字体显示效果不佳。
- 不使用原生桌面通知时，弹出通知会抢占全系统鼠标焦点，导致无法操作其他窗口。可以通过 `winecfg` 启用虚拟桌面模式缓解，或禁用桌面通知。
- Wine-staging 用户需要关闭 `winecfg` 中的 `隐藏 Wine 版本` 选项，以便 MAA 正确检测 Wine 环境。
- Wine 的 Light 主题会导致 WPF 中部分文字颜色异常，建议在 `winecfg` 中切换到无主题（Windows 经典主题）。
- Wine 使用旧式 XEmbed 托盘图标，在 GNOME 下可能无法正常工作。
- 使用 Linux 原生 MaaCore 时暂不支持自动更新（~~更新程序：我寻思我应该下载个 Windows 版~~）

### 使用 Python

:::: steps

1. 安装 MAA 动态库
   1. 在 [MAA 官网](https://maa.plus/) 下载 Linux 动态库并解压，或从软件源安装：
      - AUR：[maa-assistant-arknights](https://aur.archlinux.org/packages/maa-assistant-arknights)，按照安装后的提示编辑文件
      - Nixpkgs: [maa-assistant-arknights](https://github.com/NixOS/nixpkgs/blob/nixos-unstable/pkgs/by-name/ma/maa-assistant-arknights/package.nix)
   2. 进入 `./MAA-v{版本号}-linux-{架构}/Python/` 目录下打开 `sample.py` 文件

   ::: tip
   预编译的版本包含在相对较新的 Linux 发行版 (Ubuntu 22.04) 中编译的动态库，如果您系统中的 libstdc++ 版本较老，可能遇到 ABI 不兼容的问题
   可以参考 [Linux 编译教程](../../develop/linux-tutorial.md) 重新编译或使用容器运行
   :::

2. ADB 配置
   1. 找到 [`if asst.connect('adb.exe', '127.0.0.1:5554'):`](https://github.com/MaaAssistantArknights/MaaAssistantArknights/blob/b4fc3528decd6777441a8aca684c22d35d2b2574/src/Python/sample.py#L62) 一栏
   2. ADB 工具调用
      - 如果模拟器使用 `Android Studio` 的 `avd` ，其自带 ADB 。可以直接在 `adb.exe` 一栏填写 ADB 路径，一般在 `$HOME/Android/Sdk/platform-tools/` 里面可以找到，例如：

      ```python
      if asst.connect("/home/foo/Android/Sdk/platform-tools/adb", "模拟器的 ADB 地址"):
      ```

      - 如果使用其他模拟器须先下载 ADB ： `$ sudo apt install adb` 后填写路径或利用 `PATH` 环境变量直接填写 `adb` 即可。

   3. 模拟器 ADB 路径获取
      - 可以直接使用 ADB 工具： `$ adb路径 devices` ，例如：

      ```shell
      $ /home/foo/Android/Sdk/platform-tools/adb devices
      List of devices attached
      emulator-5554 device
      ```

      - 返回的 `emulator-5554` 就是模拟器的 ADB 地址，覆盖掉 `127.0.0.1:5555` ，例如：

      ```python
      if asst.connect("/home/foo/Android/Sdk/platform-tools/adb", "emulator-5554"):
      ```

   4. 这时候可以测试下： `$ python3 sample.py` ，如果返回 `连接成功` 则基本成功了。

3. 任务配置

   自定义任务： 根据需要参考 [集成文档](../../protocol/integration.md) 对 `sample.py` 的 [`# 任务及参数请参考 docs/integration.md`](https://github.com/MaaAssistantArknights/MaaAssistantArknights/blob/722f0ddd4765715199a5dc90ea1bec2940322344/src/Python/sample.py#L54) 一栏进行修改

::::

## 模拟器支持

### ✅ [AVD](https://developer.android.com/studio/run/managing-avds)

必选配置： 16:9 的屏幕分辨率，且分辨率需大于 720p

推荐配置： x86_64 的框架 (R - 30 - x86_64 - Android 11.0) 配合 MAA 的 Linux x64 动态库

额外支持[截图增强模式](../connection.md#avd-截图增强模式)。

注意：从 Android 10 开始，Minitouch 在 SELinux 为 `Enforcing` 模式时不再可用，请切换至其他触控模式，或将 SELinux **临时**切换为 `Permissive` 模式。

### ⚠️ [Genymotion](https://www.genymotion.com/)

高版本安卓自带 x86_64 框架，轻量但是运行明日方舟时易闪退

暂未严格测试， ADB 功能和路径获取没有问题

## 容器化安卓的支持

::: tip
以下方案通常对内核模块有一定要求, 请根据具体方案和发行版安装合适的内核模块
:::

### ✅ [Waydroid](https://waydro.id/)

安装后需要重新设置分辨率（或者大于 720P 且为 16:9 的分辨率，然后重新启动）：

```shell
waydroid prop set persist.waydroid.width 1280
waydroid prop set persist.waydroid.height 720
```

设置 ADB 的 IP 地址：打开 `设置` - `关于` - `IP地址` ，记录第一个 `IP` ，将 `${记录的IP}:5555` 填入`sample.py` 的 adb IP 一栏。

### ✅ [redroid](https://github.com/remote-android/redroid-doc)

安卓 11 版本的镜像可正常运行游戏, 需要暴露 5555 ADB 端口.

## 明日方舟 PC 客户端（Wine/Proton）窗口控制

MAA 可以直接控制 Linux 上通过 Wine/Proton 运行的**明日方舟 PC 客户端**窗口，无需模拟器或 ADB。
控制方式为 X11 合成事件（`XSendEvent`）：**不移动光标、不抢占焦点**，自动化期间可正常使用桌面。

### 前置要求

- 运行在 X11（含 XWayland）环境，编译时检测到 X11 开发库（`libX11-devel`），即启用 `ASST_WITH_X11`
- 游戏以**窗口化 1920×1080** 运行（MAA 对 16:9 分辨率的要求）。Arknights EN 客户端可通过修改
  Wine 前缀下的 `user.reg`（`[Software\\Yostar\\Arknights_EN]`）实现：

  ```text
  "Screenmanager Fullscreen mode_h3630240806"=dword:00000003
  "Screenmanager Resolution Width_h182942802"=dword:00000780   ; 1920
  "Screenmanager Resolution Height_h2627697771"=dword:00000438 ; 1080
  "Screenmanager Resolution Use Native_h1405027254"=dword:00000000
  ```

- 游戏窗口必须保持显示（**不可最小化**，最小化后游戏暂停且截图失败）；被其他窗口遮挡不影响运行

### 使用

通过 C API 按窗口标题绑定（如 `Arknights`）：

```c
AsstAsyncCallId id = AsstAsyncAttachWindowByName(handle, "Arknights", 0 /* focus_for_keys */, 1 /* block */);
```

`focus_for_keys`：发送按键（如 ESC、文本输入）前是否将输入焦点切换到游戏窗口。Unity 游戏仅在窗口聚焦时响应键盘，
开启后按键总能生效，但会把键盘焦点从你当前的应用夺走；关闭时按键仅在游戏窗口恰好聚焦时生效。

> 提示：鼠标点击/滑动通过合成事件直接投递到窗口，不受焦点影响，因此绝大多数 MAA 任务（如基建、刷图）无需开启该选项。

### 通过 gamescope 隔离运行（推荐）

上面的窗口控制模式有一个弱点：Wine 会把发给非活动窗口的合成点击当作“用户点击”，请求窗口管理器激活游戏窗口——
在 KDE/GNOME 上这会让游戏窗口前置并抢占焦点。控制器内置的 `guard_input_focus` 事后会归还焦点，
但窗口仍会跳到前台。

彻底的解决办法是让游戏运行在**独立的显示服务器**上：
[gamescope](https://github.com/ValveSoftware/gamescope)（Valve 的微型合成器，即 Steam Deck 的游戏会话）。
游戏成为 gamescope 私有 X server 的客户端，其窗口激活请求根本不会到达桌面合成器，
抢焦点从机制上不再可能；同时 gamescope 以完整 GPU 加速把游戏渲染为桌面上的一个普通窗口。
MAA 绑定到 gamescope **内部**的游戏窗口，即使 gamescope 窗口完全失焦也能正常控制。

使用自带启动脚本：

```shell
tools/isolated-game/arknights-isolated.sh --profile gui-window
```

脚本会：

- 自动检测 Steam 的 Proton（如 GE-Proton11-3）与明日方舟的 compat 前缀，并像 Steam 一样通过 Proton
  启动游戏（`--plain-wine` 可改用系统 wine + `~/.wine`）；
- 以 1280×720（MAA 原生分辨率）启动 gamescope，并强制游戏窗口恰好填满；
- 为游戏禁用 Gamescope WSI layer（`DISABLE_GAMESCOPE_WSI=1`）：该 layer 提供直接扫描输出 / HDR 直通，
  但走私有呈现协议，窗口截图只会得到黑屏（如需启用加 `--wsi-layer`）；
- 等游戏窗口出现后，打印（`--profile NAME` 时同时写入 `~/.config/maa/profiles/NAME.toml`）
  需要使用的窗口名，例如 `":1:Arknights"`。

窗口名语法：可在标题前加 X 显示前缀——`":1:Arknights"`、`":1.0:Arknights"` 或 `"host:1:Arknights"`；
不带前缀时与之前一样在进程自身的 `DISPLAY` 中查找。

其他选项：

- `--hidden` —— 使用 gamescope 无头后端：桌面完全不出现窗口（仍然 GPU 合成，MAA 照常控制游戏）。
  可见 ↔ 隐藏通过 `--stop` 后重新启动切换。
- `--stop` / `--status` —— 停止隔离会话 / 查看状态。
- `--res WxH`、`--scale WxH`、`--xvfb` —— 游戏分辨率、桌面窗口尺寸、软件渲染的 Xvfb 回退。

注意：

- 自动化期间请保持 gamescope 窗口**不被最小化**（最小化后客户端停止渲染、截图失败）；
  被其他窗口遮挡没有影响——游戏处于失焦状态，其窗口也永远无法自行前置。
- 游戏被隔离后，`focus_for_keys` 只是在 gamescope 内部移动焦点，开启它不再有副作用。
- 隔离显示上 MAA 通过 **XTest 扩展注入真实输入事件**（编译时检测到 `libXtst` 即启用）：虚拟鼠标指针
  只存在于 gamescope 内部，不影响桌面光标；游戏把每次点击都当作真实点击处理，彻底消除 Wine 的
  “激活点击吞没”（此前表现为空闲后的第一个合成点击偶尔失效，招募确认/加速随机失败）。无 XTest 时
  回退为合成事件 + 每次点击前主动激活。
