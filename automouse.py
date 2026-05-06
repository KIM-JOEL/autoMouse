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
IDLE_THRESHOLD_SEC = 9 * 60
NUDGE_PIXELS = 5
CHECK_INTERVAL_SEC = 15


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


def get_cursor_pos() -> tuple[int, int]:
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_cursor_pos(x: int, y: int) -> None:
    user32.SetCursorPos(int(x), int(y))


def nudge_mouse() -> None:
    x, y = get_cursor_pos()
    set_cursor_pos(x + NUDGE_PIXELS, y)
    time.sleep(0.05)
    set_cursor_pos(x, y)


class State:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.nudge_count = 0
        self.last_nudge: datetime | None = None
        self.started_at = datetime.now()


def worker(state: State) -> None:
    log(
        f"{APP_NAME} 워커 시작 - 임계값 {IDLE_THRESHOLD_SEC // 60}분, "
        f"이동 {NUDGE_PIXELS}px, 점검 {CHECK_INTERVAL_SEC}s"
    )
    while not state.stop.is_set():
        try:
            idle = get_idle_seconds()
            if idle >= IDLE_THRESHOLD_SEC:
                nudge_mouse()
                state.nudge_count += 1
                state.last_nudge = datetime.now()
                log(f"유휴 {int(idle)}초 감지 - 마우스 이동 (누적 {state.nudge_count}회)")
                if state.stop.wait(CHECK_INTERVAL_SEC):
                    break
            else:
                remaining = IDLE_THRESHOLD_SEC - idle
                if state.stop.wait(min(CHECK_INTERVAL_SEC, max(1.0, remaining))):
                    break
        except Exception as e:
            log(f"오류: {e!r}")
            if state.stop.wait(CHECK_INTERVAL_SEC):
                break
    log(f"{APP_NAME} 워커 종료")


def load_icon_image() -> Image.Image:
    for name in ("icon.ico", "icon.png"):
        path = _resource_path(name)
        if os.path.exists(path):
            try:
                return Image.open(path)
            except Exception as e:
                log(f"아이콘 로드 실패 ({name}): {e!r}")
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=(30, 144, 255, 255), outline=(255, 255, 255, 255), width=2)
    draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))
    return img


def build_menu(state: State, on_exit) -> pystray.Menu:
    def status_text(_item):
        if state.last_nudge is None:
            return f"실행 중 (이동 0회) - 시작 {state.started_at:%H:%M:%S}"
        return (
            f"실행 중 - 마지막 이동 {state.last_nudge:%H:%M:%S} "
            f"(누적 {state.nudge_count}회)"
        )

    def threshold_text(_item):
        return f"유휴 임계값: {IDLE_THRESHOLD_SEC // 60}분 / 이동: {NUDGE_PIXELS}px"

    return pystray.Menu(
        pystray.MenuItem(status_text, None, enabled=False, default=True),
        pystray.MenuItem(threshold_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", on_exit),
    )


def main() -> int:
    state = State()
    icon_image = load_icon_image()

    def on_exit(icon, _item):
        log("사용자 종료 요청")
        state.stop.set()
        icon.stop()

    icon = pystray.Icon(
        APP_NAME,
        icon_image,
        APP_NAME,
        build_menu(state, on_exit),
    )

    t = threading.Thread(target=worker, args=(state,), daemon=True)
    t.start()

    log(f"{APP_NAME} 시작됨")
    icon.run()

    state.stop.set()
    t.join(timeout=2)
    log(f"{APP_NAME} 종료됨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
