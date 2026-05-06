import ctypes
import os
import sys
import time
from ctypes import wintypes
from datetime import datetime

IDLE_THRESHOLD_SEC = 9 * 60
NUDGE_PIXELS = 5
CHECK_INTERVAL_SEC = 15

LOG_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)),
    "automouse.log",
)


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
    try:
        print(line, flush=True)
    except Exception:
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


def main() -> int:
    log(
        f"automouse 시작 - 유휴 임계값 {IDLE_THRESHOLD_SEC // 60}분, "
        f"이동 {NUDGE_PIXELS}px, 점검 주기 {CHECK_INTERVAL_SEC}s"
    )
    while True:
        try:
            idle = get_idle_seconds()
            if idle >= IDLE_THRESHOLD_SEC:
                nudge_mouse()
                log(f"유휴 {int(idle)}초 감지 - 마우스 {NUDGE_PIXELS}px 이동")
                time.sleep(CHECK_INTERVAL_SEC)
            else:
                remaining = IDLE_THRESHOLD_SEC - idle
                time.sleep(min(CHECK_INTERVAL_SEC, max(1.0, remaining)))
        except KeyboardInterrupt:
            log("automouse 종료 (KeyboardInterrupt)")
            return 0
        except Exception as e:
            log(f"오류: {e!r}")
            time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    sys.exit(main())
