import ctypes
import os
import sys
import threading
import time
from ctypes import wintypes
from datetime import datetime

import pystray
from PIL import Image, ImageDraw

APP_NAME = "MouseMover"
IDLE_THRESHOLD_SEC = 4 * 60
NUDGE_PIXELS = 5
CHECK_INTERVAL_SEC = 15

MOUSEEVENTF_MOVE = 0x0001


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", _base_dir())
    return os.path.join(base, rel)


LOG_FILE = os.path.join(_base_dir(), "automouse.log")


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def get_idle_seconds() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(ctypes.byref(lii)):
        return 0.0
    return (kernel32.GetTickCount() - lii.dwTime) / 1000.0


def nudge_mouse() -> None:
    # SetCursorPos 는 커서 좌표만 텔레포트하고 입력 이벤트를 큐에 넣지 않아
    # GetLastInputInfo / 화면보호기 타이머가 리셋되지 않음.
    # mouse_event 는 실제 입력 이벤트를 주입하므로 OS 가 "사용자 입력" 으로 인식.
    user32.mouse_event(MOUSEEVENTF_MOVE, NUDGE_PIXELS, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_MOVE, -NUDGE_PIXELS, 0, 0, 0)


class State:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.nudge_count = 0
        self.last_nudge: datetime | None = None
        self.started_at = datetime.now()


def worker(state: State, icon) -> None:
    log(
        f"{APP_NAME} worker started - threshold {IDLE_THRESHOLD_SEC // 60}min, "
        f"nudge {NUDGE_PIXELS}px, interval {CHECK_INTERVAL_SEC}s"
    )
    while not state.stop.is_set():
        try:
            idle = get_idle_seconds()
            if idle >= IDLE_THRESHOLD_SEC:
                nudge_mouse()
                # 입력 주입이 정상이면 0초 근처가 찍힘 (검증용)
                post_idle = get_idle_seconds()
                state.nudge_count += 1
                state.last_nudge = datetime.now()
                log(
                    f"idle={int(idle)}s -> nudge "
                    f"(count={state.nudge_count}, post_idle={post_idle:.2f}s)"
                )
                try:
                    icon.update_menu()
                except Exception as e:
                    log(f"update_menu failed: {e!r}")
                if state.stop.wait(CHECK_INTERVAL_SEC):
                    break
            else:
                remaining = IDLE_THRESHOLD_SEC - idle
                if state.stop.wait(min(CHECK_INTERVAL_SEC, max(1.0, remaining))):
                    break
        except Exception as e:
            log(f"worker error: {e!r}")
            if state.stop.wait(CHECK_INTERVAL_SEC):
                break
    log(f"{APP_NAME} worker stopped")


def load_icon_image() -> Image.Image:
    for name in ("icon.ico", "icon.png"):
        path = _resource_path(name)
        if os.path.exists(path):
            try:
                return Image.open(path)
            except Exception as e:
                log(f"icon load failed ({name}): {e!r}")
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=(30, 144, 255, 255), outline=(255, 255, 255, 255), width=2)
    draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))
    return img


def build_menu(state: State, on_exit) -> pystray.Menu:
    def status_text(_item):
        if state.last_nudge is None:
            return f"Running (count: 0) - started {state.started_at:%H:%M:%S}"
        return (
            f"Running - last move {state.last_nudge:%H:%M:%S} "
            f"(count: {state.nudge_count})"
        )

    def threshold_text(_item):
        return f"Idle threshold: {IDLE_THRESHOLD_SEC // 60} min / Move: {NUDGE_PIXELS}px"

    return pystray.Menu(
        pystray.MenuItem(status_text, None, enabled=False),
        pystray.MenuItem(threshold_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit),
    )


def main() -> int:
    state = State()
    icon_image = load_icon_image()

    def on_exit(icon, _item):
        log("user requested exit")
        state.stop.set()
        icon.stop()

    icon = pystray.Icon(
        APP_NAME,
        icon_image,
        APP_NAME,
        build_menu(state, on_exit),
    )

    t = threading.Thread(target=worker, args=(state, icon), daemon=True)
    t.start()

    log(f"{APP_NAME} started")
    icon.run()

    state.stop.set()
    t.join(timeout=2)
    log(f"{APP_NAME} stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
