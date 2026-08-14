// 快速连点测试：验证 guard_input_focus 在战斗节奏下是否稳定
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <X11/Xlib.h>
#include "AsstCaller.h"

static void on_msg(AsstMsgId msg, const char* details_json, void* arg) { (void)msg; (void)details_json; (void)arg; }

int main(int argc, char** argv)
{
    if (argc < 3) { fprintf(stderr, "usage: bursttest <resource> <window> [n_clicks]\n"); return 2; }
    int n = argc >= 4 ? atoi(argv[3]) : 15;
    if (!AsstLoadResource(argv[1])) { fprintf(stderr, "load resource failed\n"); return 1; }
    AsstHandle h = AsstCreateEx(on_msg, NULL);
    AsstAsyncAttachWindowByName(h, argv[2], 0, 1);
    if (!AsstConnected(h)) { fprintf(stderr, "attach failed\n"); return 1; }
    Display* dpy = XOpenDisplay(NULL);
    for (int i = 0; i < n; ++i) {
        AsstAsyncClick(h, 640, 360, 1);
        usleep(100000);
        Window cur; int r;
        XGetInputFocus(dpy, &cur, &r);
        printf("click %2d -> focus=0x%lx %s\n", i + 1, cur, cur == 113246209 ? "GAME" : (cur == 2097152 ? "USER" : "other"));
    }
    XCloseDisplay(dpy);
    AsstDestroy(h);
    return 0;
}
