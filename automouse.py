import ctypes
import os
import sys
import threading
import time
from ctypes import (
    POINTER, Structure, WINFUNCTYPE, byref, c_int, c_void_p, sizeof, wintypes,
)
from datetime import datetime

APP_NAME = "MouseMover"
IDLE_THRESHOLD_SEC = 4 * 60
NUDGE_PIXELS = 5
CHECK_INTERVAL_SEC = 15

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1

NIM_ADD = 0x0
NIM_DELETE = 0x2
NIF_MESSAGE = 0x1
NIF_ICON = 0x2
NIF_TIP = 0x4

MF_STRING = 0x0
MF_SEPARATOR = 0x800
MFS_DISABLED = 0x3
TPM_RIGHTBUTTON = 0x0002

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x10

MOUSEEVENTF_MOVE = 0x0001

IDM_STATUS = 1001
IDM_THRESHOLD = 1002
IDM_EXIT = 1003

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32


class POINT(Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class LASTINPUTINFO(Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


WNDPROC = WINFUNCTYPE(c_int, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSEXW(Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class NOTIFYICONDATAW(Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
    ]


class MSG(Structure):
    _fields_ = [
        ("hWnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


# 64-bit 안전성을 위해 핸들 반환 함수에 restype 명시
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.restype = wintypes.LPARAM
user32.LoadImageW.restype = wintypes.HANDLE
user32.LoadIconW.restype = wintypes.HICON
user32.CreatePopupMenu.restype = wintypes.HMENU
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
shell32.ExtractIconExW.restype = wintypes.UINT


class State:
    def __init__(self):
        self.stop = threading.Event()
        self.nudge_count = 0
        self.last_nudge = None
        self.started_at = datetime.now()
        self.nid = None


state = State()


def get_idle_seconds():
    lii = LASTINPUTINFO()
    lii.cbSize = sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(byref(lii)):
        return 0.0
    return (kernel32.GetTickCount() - lii.dwTime) / 1000.0


def nudge_mouse():
    user32.mouse_event(MOUSEEVENTF_MOVE, NUDGE_PIXELS, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_MOVE, -NUDGE_PIXELS, 0, 0, 0)


def worker():
    while not state.stop.is_set():
        try:
            idle = get_idle_seconds()
            if idle >= IDLE_THRESHOLD_SEC:
                nudge_mouse()
                state.nudge_count += 1
                state.last_nudge = datetime.now()
                if state.stop.wait(CHECK_INTERVAL_SEC):
                    break
            else:
                remaining = IDLE_THRESHOLD_SEC - idle
                if state.stop.wait(min(CHECK_INTERVAL_SEC, max(1.0, remaining))):
                    break
        except Exception:
            if state.stop.wait(CHECK_INTERVAL_SEC):
                break


def load_app_icon():
    if getattr(sys, "frozen", False):
        large = wintypes.HICON()
        small = wintypes.HICON()
        shell32.ExtractIconExW(sys.executable, 0, byref(large), byref(small), 1)
        return small.value or large.value or 0
    here = os.path.dirname(os.path.abspath(__file__))
    ico = os.path.join(here, "icon.ico")
    if os.path.exists(ico):
        return user32.LoadImageW(None, ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
    return user32.LoadIconW(None, ctypes.c_wchar_p(32512))  # IDI_APPLICATION


def show_context_menu(hwnd):
    h_menu = user32.CreatePopupMenu()
    if state.last_nudge is None:
        status = f"Running (count: 0) - started {state.started_at:%H:%M:%S}"
    else:
        status = (
            f"Running - last move {state.last_nudge:%H:%M:%S} "
            f"(count: {state.nudge_count})"
        )
    threshold = f"Idle threshold: {IDLE_THRESHOLD_SEC // 60} min / Move: {NUDGE_PIXELS}px"
    user32.AppendMenuW(h_menu, MF_STRING | MFS_DISABLED, IDM_STATUS, status)
    user32.AppendMenuW(h_menu, MF_STRING | MFS_DISABLED, IDM_THRESHOLD, threshold)
    user32.AppendMenuW(h_menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(h_menu, MF_STRING, IDM_EXIT, "Exit")

    pt = POINT()
    user32.GetCursorPos(byref(pt))
    user32.SetForegroundWindow(hwnd)
    user32.TrackPopupMenu(h_menu, TPM_RIGHTBUTTON, pt.x, pt.y, 0, hwnd, None)
    user32.DestroyMenu(h_menu)


def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_TRAYICON:
        if lparam in (WM_RBUTTONUP, WM_LBUTTONUP):
            show_context_menu(hwnd)
            return 0
    elif msg == WM_COMMAND:
        if (wparam & 0xFFFF) == IDM_EXIT:
            user32.DestroyWindow(hwnd)
            return 0
    elif msg == WM_DESTROY:
        if state.nid is not None:
            shell32.Shell_NotifyIconW(NIM_DELETE, byref(state.nid))
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


WND_PROC_INSTANCE = WNDPROC(wnd_proc)


def main():
    h_inst = kernel32.GetModuleHandleW(None)

    wc = WNDCLASSEXW()
    wc.cbSize = sizeof(WNDCLASSEXW)
    wc.lpfnWndProc = WND_PROC_INSTANCE
    wc.hInstance = h_inst
    wc.lpszClassName = "MouseMoverWindowClass"
    if not user32.RegisterClassExW(byref(wc)):
        return 1

    hwnd = user32.CreateWindowExW(
        0, "MouseMoverWindowClass", APP_NAME, 0,
        0, 0, 0, 0, None, None, h_inst, None,
    )
    if not hwnd:
        return 1

    h_icon = load_app_icon()

    nid = NOTIFYICONDATAW()
    nid.cbSize = sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    nid.hIcon = h_icon
    nid.szTip = APP_NAME
    shell32.Shell_NotifyIconW(NIM_ADD, byref(nid))
    state.nid = nid

    threading.Thread(target=worker, daemon=True).start()

    msg = MSG()
    while user32.GetMessageW(byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(byref(msg))
        user32.DispatchMessageW(byref(msg))

    state.stop.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
