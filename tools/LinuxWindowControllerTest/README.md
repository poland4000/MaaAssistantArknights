# LinuxWindowControllerTest

LinuxWindowController（X11 窗口控制）的验证驱动，通过 `AsstAsyncAttachWindowByName` 绑定窗口并执行截图/点击。

## 编译

```bash
gcc -O2 -o lwtest main.c -I<MAA>/include -L<MAA>/build/bin/Debug -lMaaCore
```

## 运行

```bash
LD_LIBRARY_PATH=<MAA>/build/bin/Debug:<MAA>/src/MaaUtils/MaaDeps/vcpkg/installed/maa-x64-linux/lib \
DISPLAY=:0 ./lwtest <MAA> Arknights [click_x click_y]
```

- `<MAA>`: 仓库根目录（内含 `resource/`）
- 第二个参数为窗口标题（完全匹配），如 `Arknights`
- 可选 `click_x click_y`：以 MAA 内部坐标（1280×720 空间）执行一次点击，用于验证输入链路

输出截图保存到当前目录的 `ctrl_before.png` / `ctrl_after.png`（测试用途，可按需修改路径）。

## 焦点行为

Wine 会把发给非活动窗口的合成点击当作“用户点击”，随后请求激活窗口（XSetInputFocus /
_NET_ACTIVE_WINDOW），KWin 的防焦点窃取挡不住它（点击携带新鲜 user time）。因此：

- `focus_for_keys = false`（默认）时，控制器在每次合成输入前先把焦点切到游戏窗口
  （纯焦点变化，无可吞点击），输入完成后再把焦点与遮挡关系还原给用户原窗口
  （`guard_input_focus` 的 pre-focus 方案）。
- 游戏窗口的 “active” 标记会在点击瞬间短暂翻转，KWin 数秒内自动与真实焦点重新同步；
  键盘输入不受中断。
- `focus_for_keys = true` 时不做干预，游戏保持持有焦点。


## 游戏窗口抢焦点问题（2026-08 客户端更新后）

2026-08-13 的 EN 客户端更新后，游戏在收到合成输入时会主动请求激活窗口（携带新 user time），
KWin 的防焦点窃取（fsplevel/fpplevel 规则）无法拦截，导致自动化期间打断用户在其他窗口的输入。

**解决方案：KWin 脚本 `focusguard`**（本目录 `focusguard/`）：
游戏窗口激活时，若鼠标光标不在游戏窗口内（= 合成输入触发），立即把焦点还给之前的活动窗口；
真实用户点击（光标在游戏上）不受影响。安装：

```bash
mkdir -p ~/.local/share/kwin/scripts/focusguard/contents/code
cp focusguard/metadata.json ~/.local/share/kwin/scripts/focusguard/
cp focusguard/main.js ~/.local/share/kwin/scripts/focusguard/contents/code/
kwriteconfig6 --file kwinrc --group Plugins --key focusguardEnabled true
busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure
```

实测：连点不打断输入、窗口不再前置；手动游玩不受影响。
控制器侧的 `guard_input_focus` 仍保留，用于无此脚本的场景/窗口管理器。

## 更新（2026-08-14）：激活吞点击问题

2026-08 客户端更新还会**吞掉触发激活的那次点击**（Windows 激活语义）：
游戏非前台时到达的点击被激活流程消耗，copilot 的 BattleStartPre 单击被吞后
流程错乱（编队为空、直接开打）。
实测只有“一次性”点击受害（菜单类任务靠识别重试自愈）。最终方案：
仅当窗口非前台且点击落在关卡界面 Start 按钮区域时补发第二次点击
（第一次触发激活被吞，第二次落在激活完成后生效），其余输入不变；
`guard_input_focus` 保持“输入后归还焦点”，KWin focusguard 脚本继续
负责防止游戏激活打断用户输入。
