#if !defined(_WIN32) && ASST_WITH_X11

#include "LinuxWindowController.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <sstream>
#include <thread>

#include <X11/keysym.h>

#include "Config/GeneralConfig.h"
#include "SwipeHelper.hpp"
#include "Utils/Logger.hpp"

namespace asst
{
// 解析 window_name 的 X 显示前缀（":1:Arknights" / ":1.0:Arknights" / "host:1:Arknights"）。
// 无前缀或前缀不完整时原样返回标题（display 为空 → 使用进程的 DISPLAY）。
static void split_display_prefix(const std::string& window_name, std::string& display, std::string& title)
{
    display.clear();
    title = window_name;

    size_t digits_pos = std::string::npos;
    if (!window_name.empty() && window_name[0] == ':') {
        digits_pos = 1;
    }
    else {
        const size_t colon = window_name.find(':');
        if (colon == std::string::npos || colon == 0) {
            return;
        }
        digits_pos = colon + 1;
    }

    const auto is_digit = [](char c) {
        return c >= '0' && c <= '9';
    };

    size_t i = digits_pos;
    while (i < window_name.size() && is_digit(window_name[i])) {
        ++i;
    }
    if (i == digits_pos) {
        return;
    }
    if (i < window_name.size() && window_name[i] == '.') {
        ++i;
        const size_t frac_start = i;
        while (i < window_name.size() && is_digit(window_name[i])) {
            ++i;
        }
        if (i == frac_start) {
            return;
        }
    }
    if (i >= window_name.size() || window_name[i] != ':') {
        return;
    }

    display = window_name.substr(0, i);
    title = window_name.substr(i + 1);
}

LinuxWindowController::LinuxWindowController(const AsstCallback& callback [[maybe_unused]], Assistant* inst) :
    InstHelper(inst)
{
    LogTraceFunction;
}

LinuxWindowController::~LinuxWindowController()
{
    LogTraceFunction;

    if (m_display != nullptr) {
        XCloseDisplay(m_display);
        m_display = nullptr;
    }
}

bool LinuxWindowController::attach(const std::string& window_name, bool focus_for_keys)
{
    LogTraceFunction;

    m_inited = false;
    m_focus_for_keys = focus_for_keys;

    std::string display_spec;
    std::string title;
    split_display_prefix(window_name, display_spec, title);
    if (title.empty()) {
        Log.error("Empty window title after display prefix:", window_name);
        return false;
    }
    m_isolated = !display_spec.empty();
    if (m_isolated) {
        Log.info("Attaching on X display", display_spec, "window:", title);
    }

    if (m_display != nullptr) {
        XCloseDisplay(m_display);
        m_display = nullptr;
    }

    m_display = XOpenDisplay(display_spec.empty() ? nullptr : display_spec.c_str());
    if (m_display == nullptr) {
        Log.error("Failed to open X display", display_spec.empty() ? "(from DISPLAY)" : display_spec.c_str());
        return false;
    }

    // 静默 X11 错误，避免窗口被销毁等竞态打印大量错误
    XSetErrorHandler([](Display*, XErrorEvent*) -> int { return 0; });

    // 隔离显示上启用 XTest 真实输入注入（扩展缺失时回退 XSendEvent 合成事件）
    m_use_xtest = false;
    if (m_isolated) {
#if defined(ASST_WITH_XTEST)
        int opcode = 0, first_event = 0, first_error = 0;
        if (XQueryExtension(m_display, "XTEST", &opcode, &first_event, &first_error)) {
            m_use_xtest = true;
            Log.info("XTest extension available on isolated display, using real input injection");
        }
        else {
            Log.warn("XTest extension unavailable on isolated display, falling back to synthetic events");
        }
#else
        Log.warn("Built without XTest support, falling back to synthetic events");
#endif
    }

    if (!find_window(title)) {
        Log.error("Failed to find window:", title);
        return false;
    }

    if (!refresh_geometry()) {
        Log.error("Failed to get window geometry");
        return false;
    }

    // 尝试截图；游戏转场/切换分辨率瞬间窗口可能上报临时尺寸（如 1278x699），
    // 直接交给上层分辨率校验会把一次瞬时抖动变成连接失败，这里重试至尺寸稳定
    cv::Mat image;
    for (int attempt = 0;; ++attempt) {
        if (!refresh_geometry() || !capture_window(image)) {
            Log.error("Failed to capture window");
            return false;
        }
        constexpr double eps = 1e-3;
        const bool size_ok = m_width >= 1280 && m_height >= 720 &&
                             std::fabs(16.0 / 9.0 - static_cast<double>(m_width) / m_height) < eps;
        if (size_ok) {
            break;
        }
        if (attempt >= 19) {
            Log.error("Window size stays unsupported:", m_width, "x", m_height);
            return false;
        }
        Log.warn("Transient window size, retrying:", m_width, "x", m_height);
        std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }

    std::stringstream ss;
    ss << std::hex << m_window;
    m_uuid = ss.str();

    m_inited = true;
    return true;
}

bool LinuxWindowController::connect(
    const std::string& adb_path [[maybe_unused]],
    const std::string& address [[maybe_unused]],
    const std::string& config [[maybe_unused]])
{
    Log.error("LinuxWindowController does not support connect(), use attach() instead");
    return false;
}

bool LinuxWindowController::inited() const noexcept
{
    return m_inited && m_display != nullptr && m_window != 0;
}

const std::string& LinuxWindowController::get_uuid() const
{
    return m_uuid;
}

bool LinuxWindowController::screencap(cv::Mat& image_payload, bool allow_reconnect [[maybe_unused]])
{
    LogTraceFunction;

    if (!inited()) {
        return false;
    }

    return capture_window(image_payload);
}

bool LinuxWindowController::capture_window(cv::Mat& image_payload)
{
    if (!refresh_geometry()) {
        return false;
    }

    XImage* image = XGetImage(m_display, m_window, 0, 0, m_width, m_height, AllPlanes, ZPixmap);
    if (image == nullptr) {
        Log.error("XGetImage failed");
        return false;
    }

    cv::Mat mat(m_height, m_width, CV_8UC3);
    const unsigned long r_mask = image->red_mask;
    const unsigned long g_mask = image->green_mask;
    const unsigned long b_mask = image->blue_mask;

    // 常见 32bpp/24bpp BGRA/BGR（XWayland 默认，小端序），直接按字节拷贝
    const int bytes_per_pixel = image->bits_per_pixel / 8;
    const bool fast_path = image->byte_order == LSBFirst && bytes_per_pixel >= 3 &&
                           r_mask == 0xFF0000 && g_mask == 0xFF00 && b_mask == 0xFF;

    if (fast_path) {
        for (int y = 0; y < m_height; ++y) {
            const uchar* src = reinterpret_cast<const uchar*>(image->data + y * image->bytes_per_line);
            uchar* dst = mat.ptr<uchar>(y);
            for (int x = 0; x < m_width; ++x) {
                dst[x * 3] = src[x * bytes_per_pixel + 0];
                dst[x * 3 + 1] = src[x * bytes_per_pixel + 1];
                dst[x * 3 + 2] = src[x * bytes_per_pixel + 2];
            }
        }
    }
    else {
        const int r_shift = r_mask ? __builtin_ctzl(r_mask) : 0;
        const int g_shift = g_mask ? __builtin_ctzl(g_mask) : 0;
        const int b_shift = b_mask ? __builtin_ctzl(b_mask) : 0;
        for (int y = 0; y < m_height; ++y) {
            uchar* dst = mat.ptr<uchar>(y);
            for (int x = 0; x < m_width; ++x) {
                unsigned long pixel = XGetPixel(image, x, y);
                dst[x * 3] = static_cast<uchar>((pixel & b_mask) >> b_shift);
                dst[x * 3 + 1] = static_cast<uchar>((pixel & g_mask) >> g_shift);
                dst[x * 3 + 2] = static_cast<uchar>((pixel & r_mask) >> r_shift);
            }
        }
    }

    XDestroyImage(image);
    image_payload = std::move(mat);
    return true;
}

bool LinuxWindowController::start_game(const std::string& client_type [[maybe_unused]])
{
    // 游戏由用户在外部启动，这里作为无操作返回成功，使 StartUp 任务流程可以继续
    Log.warn("start_game is a no-op on LinuxWindowController (launch the game externally)");
    return true;
}

bool LinuxWindowController::stop_game(const std::string& client_type [[maybe_unused]])
{
    Log.warn("stop_game is a no-op on LinuxWindowController");
    return true;
}

bool LinuxWindowController::click(const Point& p)
{
    LogTraceFunction;

    if (!inited()) {
        return false;
    }

    guard_input_focus([&]() {
        // 与 Win32Controller 对齐：down/up 之间保持一小段时间，游戏才能识别为完整点击
        constexpr int click_delay_ms = 50;

        send_button(ButtonPress, p.x, p.y, Button1);
        std::this_thread::sleep_for(std::chrono::milliseconds(click_delay_ms));
        send_button(ButtonRelease, p.x, p.y, Button1);
        std::this_thread::sleep_for(std::chrono::milliseconds(click_delay_ms));

        // 2026-08 客户端：窗口非前台时，与激活过程同时到达的点击会被吞掉
        //（Windows 激活点击语义）。实测仅影响“一次性”点击（如编队前的
        // Start 按钮）：点击被吞后流程继续但界面未变。菜单类任务有识别重试
        // 能自愈，Start 按钮则是单击即走。对这一区域补一次点击：
        // 第一次触发激活（被吞），第二次落在激活完成后，必然生效。
        // XTest 注入的是真实事件，不存在吞点击，无需补击
        if (!m_use_xtest && is_battle_start_button(p) && !window_focused()) {
            Log.info("battle-start click while unfocused: sending a second click");
            std::this_thread::sleep_for(std::chrono::milliseconds(150));
            send_button(ButtonPress, p.x, p.y, Button1);
            std::this_thread::sleep_for(std::chrono::milliseconds(click_delay_ms));
            send_button(ButtonRelease, p.x, p.y, Button1);
            std::this_thread::sleep_for(std::chrono::milliseconds(click_delay_ms));
        }

        park_cursor();
    });
    return true;
}

bool LinuxWindowController::is_battle_start_button(const Point& p) const
{
    // 720p 识别空间中的“开始类”按钮区域（实测：关卡界面 Start 1151,645；
    // 编队界面 MISSION START 1061,499,86,55）。均为一次性流程点击，
    // 被激活吞点击后无重试兜底。click() 收到的是窗口坐标
    // （ControlScaleProxy 已按窗口分辨率缩放），按实际窗口尺寸换算区域。
    if (m_width <= 0 || m_height <= 0) {
        return false;
    }
    const double sx = static_cast<double>(m_width) / 1280.0;
    const double sy = static_cast<double>(m_height) / 720.0;
    return p.x >= static_cast<int>(1000 * sx) && p.y >= static_cast<int>(480 * sy);
}

bool LinuxWindowController::window_focused() const
{
    Window focus = 0;
    int revert = 0;
    if (m_display == nullptr) {
        return false;
    }
    XGetInputFocus(m_display, &focus, &revert);
    return focus == m_window;
}

void LinuxWindowController::park_cursor()
{
    // 主界面有跟随游戏内光标的视差（陀螺仪）效果：光标位置不同，菜单按钮的
    // 像素就不同，模板分数随之漂移。每次点击/滑动后把游戏内光标停回固定点
    // （主界面左下角 BREAKING NEWS 附近，720p 约 (8, 668)），让视差回到
    // 采集模板时的姿态。对战斗无影响：底左角无交互元素，且这只是 hover。
    if (m_width <= 0 || m_height <= 0) {
        return;
    }
    const int px = static_cast<int>(8.0 * m_width / 1280.0);
    const int py = static_cast<int>(668.0 * m_height / 720.0);
    send_motion(px, py, 0);
}

bool LinuxWindowController::input(const std::string& text)
{
    LogTraceFunction;

    if (!inited()) {
        return false;
    }

    for (unsigned char c : text) {
        if (c < 0x20 || c > 0x7e) {
            continue; // 仅支持可打印 ASCII
        }
        char buf[2] = { static_cast<char>(c), '\0' };
        KeySym keysym = XStringToKeysym(buf);
        if (keysym == NoSymbol) {
            continue;
        }
        const bool need_shift = std::isupper(c) != 0 || std::strchr("~!@#$%^&*()_+{}|:\"<>?", c) != nullptr;
        if (need_shift) {
            send_key(XK_Shift_L, true);
        }
        send_key(keysym, true);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        send_key(keysym, false);
        if (need_shift) {
            send_key(XK_Shift_L, false);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    return true;
}

bool LinuxWindowController::swipe(
    const Point& p1,
    const Point& p2,
    int duration,
    bool extra_swipe,
    double slope_in,
    double slope_out,
    bool with_pause [[maybe_unused]])
{
    LogTraceFunction;

    if (!inited()) {
        return false;
    }

    int x1 = p1.x;
    int y1 = p1.y;
    const int x2 = p2.x;
    const int y2 = p2.y;

    // 起点不能在屏幕外，但是终点可以
    if (m_width > 0 && m_height > 0) {
        if (x1 < 0 || x1 >= m_width || y1 < 0 || y1 >= m_height) {
            Log.warn("swipe point1 is out of range", x1, y1);
            x1 = std::clamp(x1, 0, m_width - 1);
            y1 = std::clamp(y1, 0, m_height - 1);
        }
    }

    bool ret = false;
    guard_input_focus([&]() {
        send_button(ButtonPress, x1, y1, Button1);

        const auto& opt = Config.get_options();
        const int actual_duration = duration > 0 ? duration : opt.minitouch_swipe_default_duration;

        auto bounds_check = [this](int x, int y) {
            if (m_width <= 0 || m_height <= 0) {
                return true;
            }
            return x >= 0 && x <= m_width && y >= 0 && y <= m_height;
        };

        // XSendEvent 只是把事件塞进队列，游戏按事件到达的节奏产生拖拽物理；
        // 若一次性全部发出，游戏只会看到瞬移（点按而非拖动），所以每步之间必须真实 sleep
        constexpr int DefaultSwipeDelay = 10; // ms

        auto move_func = [this](int x, int y) {
            send_motion(x, y, Button1Mask);
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            return true;
        };

        ret = interpolate_swipe(
            x1, y1, x2, y2, actual_duration, DefaultSwipeDelay, slope_in, slope_out, move_func, bounds_check);

        if (ret && extra_swipe && opt.minitouch_extra_swipe_duration > 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(opt.minitouch_swipe_extra_end_delay));
            interpolate_swipe(
                x2,
                y2,
                x2,
                y2 - opt.minitouch_extra_swipe_dist,
                opt.minitouch_extra_swipe_duration,
                DefaultSwipeDelay,
                slope_in,
                slope_out,
                move_func,
                bounds_check);
        }

        send_button(ButtonRelease, x2, y2, Button1);
        // 不在滑动后 park：松手后的惯性/位移判定仍在进行，额外的移动事件会打断滑动
    });
    return ret;
}

bool LinuxWindowController::inject_input_event(const InputEvent& event)
{
    LogTraceFunction;

    switch (event.type) {
    case InputEvent::Type::TOUCH_DOWN: {
        unsigned int button = event.pointerId == 1 ? Button2 : (event.pointerId == 2 ? Button3 : Button1);
        send_button(ButtonPress, event.point.x, event.point.y, button);
        return true;
    }
    case InputEvent::Type::TOUCH_UP: {
        unsigned int button = event.pointerId == 1 ? Button2 : (event.pointerId == 2 ? Button3 : Button1);
        send_button(ButtonRelease, event.point.x, event.point.y, button);
        return true;
    }
    case InputEvent::Type::TOUCH_MOVE:
        send_motion(event.point.x, event.point.y, Button1Mask);
        return true;
    case InputEvent::Type::KEY_DOWN:
        send_key(static_cast<KeySym>(event.keycode), true);
        return true;
    case InputEvent::Type::KEY_UP:
        send_key(static_cast<KeySym>(event.keycode), false);
        return true;
    case InputEvent::Type::WAIT_MS:
        std::this_thread::sleep_for(std::chrono::milliseconds(event.milisec));
        return true;
    case InputEvent::Type::TOUCH_RESET:
    case InputEvent::Type::COMMIT:
        return true;
    case InputEvent::Type::UNKNOWN:
    default:
        Log.error("unknown input event type");
        return false;
    }
}

bool LinuxWindowController::press_esc()
{
    LogTraceFunction;

    if (!inited()) {
        return false;
    }

    send_key(XK_Escape, true);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    send_key(XK_Escape, false);
    return true;
}

ControlFeat::Feat LinuxWindowController::support_features() const noexcept
{
    return ControlFeat::PRECISE_SWIPE;
}

std::pair<int, int> LinuxWindowController::get_screen_res() const noexcept
{
    return { m_width, m_height };
}

bool LinuxWindowController::find_window(const std::string& window_name)
{
    const Window root = DefaultRootWindow(m_display);

    Window best = 0;
    unsigned long best_area = 0;

    std::vector<Window> stack;
    stack.push_back(root);

    while (!stack.empty()) {
        const Window current = stack.back();
        stack.pop_back();

        Window root_ret = 0;
        Window parent = 0;
        Window* children = nullptr;
        unsigned int child_count = 0;
        if (!XQueryTree(m_display, current, &root_ret, &parent, &children, &child_count)) {
            continue;
        }

        for (unsigned int i = 0; i < child_count; ++i) {
            stack.push_back(children[i]);
        }
        if (children != nullptr) {
            XFree(children);
        }

        if (current == root) {
            continue;
        }

        if (get_window_name(current) != window_name) {
            continue;
        }

        XWindowAttributes attr;
        if (!XGetWindowAttributes(m_display, current, &attr) || attr.map_state != IsViewable) {
            continue;
        }

        const unsigned long area = static_cast<unsigned long>(attr.width) * attr.height;
        if (area > best_area) {
            best_area = area;
            best = current;
        }
    }

    if (best == 0) {
        Log.error("Window not found:", window_name);
        return false;
    }

    m_window = best;
    return true;
}

std::string LinuxWindowController::get_window_name(Window window) const
{
    // 优先 _NET_WM_NAME (UTF-8)，失败则回退 WM_NAME
    const Atom utf8_string = XInternAtom(m_display, "UTF8_STRING", 0);
    const Atom net_wm_name = XInternAtom(m_display, "_NET_WM_NAME", 0);

    Atom type_ret = 0;
    int format = 0;
    unsigned long item_count = 0;
    unsigned long bytes_after = 0;
    unsigned char* prop = nullptr;
    if (XGetWindowProperty(
            m_display,
            window,
            net_wm_name,
            0,
            1024,
            0,
            utf8_string,
            &type_ret,
            &format,
            &item_count,
            &bytes_after,
            &prop) == 0 &&
        prop != nullptr) {
        std::string name(reinterpret_cast<char*>(prop), item_count);
        XFree(prop);
        if (!name.empty()) {
            return name;
        }
    }

    // 回退到 WM_NAME (STRING)
    if (XGetWindowProperty(
            m_display,
            window,
            XA_WM_NAME,
            0,
            1024,
            0,
            XA_STRING,
            &type_ret,
            &format,
            &item_count,
            &bytes_after,
            &prop) == 0 &&
        prop != nullptr) {
        std::string name(reinterpret_cast<char*>(prop), item_count);
        XFree(prop);
        if (!name.empty()) {
            return name;
        }
    }

    return {};
}

bool LinuxWindowController::refresh_geometry()
{
    XWindowAttributes attr;
    if (!XGetWindowAttributes(m_display, m_window, &attr)) {
        Log.error("XGetWindowAttributes failed");
        return false;
    }
    if (attr.map_state != IsViewable) {
        Log.error("Window is not viewable");
        return false;
    }
    m_width = attr.width;
    m_height = attr.height;
    return true;
}

void LinuxWindowController::send_button(int type, int x, int y, unsigned int button)
{
#if defined(ASST_WITH_XTEST)
    // 隔离显示：XTest 注入真实事件。真实按键事件落在虚拟指针所在窗口，
    // 游戏全屏占满隔离显示，先把指针移到目标点即可；Wine 无法把真实
    // 事件当激活点击吞掉。虚拟指针只存在于隔离显示，不影响桌面光标
    if (m_use_xtest) {
        XTestFakeMotionEvent(m_display, -1, x, y, CurrentTime);
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        XTestFakeButtonEvent(m_display, button, type == ButtonPress ? 1 : 0, CurrentTime);
        XFlush(m_display);
        return;
    }
#endif
    XButtonEvent ev = {};
    ev.type = type;
    ev.display = m_display;
    ev.window = m_window;
    ev.root = DefaultRootWindow(m_display);
    ev.subwindow = 0;
    ev.time = CurrentTime;
    ev.x = x;
    ev.y = y;
    ev.x_root = 0;
    ev.y_root = 0;
    ev.same_screen = 1;
    ev.button = button;
    ev.state = (type == ButtonRelease) ? Button1Mask : 0;
    XSendEvent(
        m_display,
        m_window,
        1,
        (type == ButtonPress) ? ButtonPressMask : ButtonReleaseMask,
        reinterpret_cast<XEvent*>(&ev));
    XFlush(m_display);
}

void LinuxWindowController::send_motion(int x, int y, unsigned int state [[maybe_unused]])
{
#if defined(ASST_WITH_XTEST)
    // 拖动中的按钮掩码由 XTest 依据已按下的物理按键自动维护，无需显式 state
    if (m_use_xtest) {
        XTestFakeMotionEvent(m_display, -1, x, y, CurrentTime);
        XFlush(m_display);
        return;
    }
#endif
    XMotionEvent ev = {};
    ev.type = MotionNotify;
    ev.display = m_display;
    ev.window = m_window;
    ev.root = DefaultRootWindow(m_display);
    ev.subwindow = 0;
    ev.time = CurrentTime;
    ev.x = x;
    ev.y = y;
    ev.x_root = 0;
    ev.y_root = 0;
    ev.same_screen = 1;
    ev.state = state;
    ev.is_hint = NotifyNormal;
    XSendEvent(m_display, m_window, 1, PointerMotionMask, reinterpret_cast<XEvent*>(&ev));
    XFlush(m_display);
}

void LinuxWindowController::send_key(KeySym keysym, bool press)
{
    if (m_focus_for_keys || (m_isolated && !window_focused())) {
        ensure_focus();
    }

    KeyCode keycode = XKeysymToKeycode(m_display, keysym);
    if (keycode == 0) {
        Log.warn("No keycode for keysym:", static_cast<unsigned long>(keysym));
        return;
    }

#if defined(ASST_WITH_XTEST)
    // 真实键盘事件投递给当前聚焦窗口，上面的 ensure_focus 已保证聚焦
    if (m_use_xtest) {
        XTestFakeKeyEvent(m_display, keycode, press ? 1 : 0, CurrentTime);
        XFlush(m_display);
        return;
    }
#endif
    XKeyEvent ev = {};
    ev.type = press ? KeyPress : KeyRelease;
    ev.display = m_display;
    ev.window = m_window;
    ev.root = DefaultRootWindow(m_display);
    ev.subwindow = 0;
    ev.time = CurrentTime;
    ev.same_screen = 1;
    ev.keycode = keycode;
    ev.state = 0;
    XSendEvent(m_display, m_window, 1, press ? KeyPressMask : KeyReleaseMask, reinterpret_cast<XEvent*>(&ev));
    XFlush(m_display);
}

// 发送 _NET_ACTIVE_WINDOW 消息（窗口管理器激活窗口的标准路径）。
// gamescope 丢弃内部焦点时，X 焦点可能仍在游戏窗口上，但 Wine 的内部
// 活动状态已失同步，会把下一个合成点击当激活点击吞掉；重新走一遍激活
// 流程能让 Wine 恢复活动状态。
void LinuxWindowController::activate_window()
{
    if (m_display == nullptr || m_window == 0) {
        return;
    }
    XEvent ev = {};
    ev.xclient.type = ClientMessage;
    ev.xclient.send_event = 1;
    ev.xclient.display = m_display;
    ev.xclient.window = m_window;
    ev.xclient.message_type = XInternAtom(m_display, "_NET_ACTIVE_WINDOW", 0);
    ev.xclient.format = 32;
    ev.xclient.data.l[0] = 1; // source indication: application
    ev.xclient.data.l[1] = 0; // timestamp
    ev.xclient.data.l[2] = 0; // requestor's currently active window
    XSendEvent(m_display, DefaultRootWindow(m_display), 0, SubstructureRedirectMask | SubstructureNotifyMask, &ev);
    XFlush(m_display);
}

void LinuxWindowController::guard_input_focus(const std::function<void()>& action)
{
    // 隔离显示模式：先把焦点交给游戏窗口（Wine 视其为活动窗口，不再吞掉首个
    // 合成点击），游戏自身的激活请求也只作用于隔离显示内部，无需归还焦点
    if (m_isolated) {
        activate_window();
        if (!window_focused()) {
            ensure_focus();
        }
        action();
        return;
    }

    // focus_for_keys 为 true 时用户明确希望游戏持有键盘焦点，不做任何干预
    if (m_focus_for_keys) {
        action();
        return;
    }

    // Wine 会把发给非活动窗口的合成点击当作“用户点击”，随后请求激活/抢占焦点，
    // KWin 的防焦点窃取挡不住它（点击携带了新鲜的 user time）。
    // 因此在合成输入前记录当前焦点窗口，若输入后游戏抢走了焦点就还回去，
    // 保证无人值守时不会打断用户在其他窗口的输入。
    Window prev_focus = 0;
    int prev_revert = 0;
    XGetInputFocus(m_display, &prev_focus, &prev_revert);

    action();

    if (prev_focus == 0 || prev_focus == m_window || prev_focus == PointerRoot) {
        return;
    }
    Window cur_focus = 0;
    int cur_revert = 0;
    XGetInputFocus(m_display, &cur_focus, &cur_revert);
    if (cur_focus != m_window) {
        return;
    }
    // 目标窗口可能已被销毁；先确认其仍然存在，避免 BadWindow 走默认错误处理
    XWindowAttributes attrs {};
    if (XGetWindowAttributes(m_display, prev_focus, &attrs) == 0) {
        return;
    }
    XSetInputFocus(m_display, prev_focus, RevertToParent, CurrentTime);
    XFlush(m_display);
}


bool LinuxWindowController::ensure_focus()
{
    if (m_display == nullptr || m_window == 0) {
        return false;
    }
    XSetInputFocus(m_display, m_window, RevertToParent, CurrentTime);
    XFlush(m_display);
    return true;
}
} // namespace asst

#endif // !defined(_WIN32) && ASST_WITH_X11
