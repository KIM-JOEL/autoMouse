# MouseMover

회사 절전 프로그램의 화면보호기 전환을 방지하는 Windows 시스템 트레이 앱.

일정 시간 입력이 없으면 마우스를 자동으로 미세하게 움직여 유휴 타이머를 리셋합니다.

---

## 기능

- 설정한 시간(기본 4분) 동안 입력이 없으면 마우스를 **5px 이동 후 즉시 원복**
- `mouse_event` Win32 API로 실제 입력 이벤트 주입 → OS 유휴 타이머 정상 리셋
- 시스템 트레이(작업표시줄 우측 숨겨진 아이콘)에서 상주
- 트레이 아이콘 호버 → **"MouseMover"** 툴팁
- 트레이 아이콘 우클릭 메뉴:
  - 실행 상태 (마지막 이동 시각 / 누적 횟수)
  - 설정 표시 (임계값 / 이동 픽셀)
  - Exit

---

## 실행 방법

**빌드 없이 바로 쓰기** — `dist\MouseMover.exe` 파일만 있으면 어느 Windows PC에서든 동작합니다. Python 등 별도 설치 불필요.

1. [Releases](../../releases) 또는 `dist\MouseMover.exe` 다운로드
2. 더블클릭
3. 트레이 아이콘(숨겨진 아이콘 `^`) 확인
4. 종료: 트레이 아이콘 우클릭 → **Exit**

**부팅 시 자동 실행**

`MouseMover.exe` 바로가기를 아래 폴더에 복사:
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

---

## 설정 변경 후 재빌드

`automouse.py` 상단 상수를 수정 후 `build.bat`을 다시 실행합니다.

```python
IDLE_THRESHOLD_SEC = 4 * 60   # 유휴 임계값 (초). 4 * 60 = 4분
NUDGE_PIXELS      = 5         # 마우스 이동 픽셀
CHECK_INTERVAL_SEC = 15       # 유휴 시간 점검 주기 (초)
```

---

## 빌드 방법

### 사전 준비

- [Python 3.9+](https://www.python.org/downloads/) 설치
  - 설치 화면에서 **"Add Python to PATH"** 체크 필수

### 빌드

```
build.bat  (더블클릭)
```

단계별 진행 상황이 표시되며 실패 시 원인과 힌트가 출력됩니다.  
상세 로그는 같은 폴더의 `build.log`에 기록됩니다.

산출물: `dist\MouseMover.exe` (단일 파일, 약 15MB)

---

## 로그

실행 파일과 같은 폴더에 `automouse.log`가 생성됩니다.

```
[2026-05-08 09:00:00] MouseMover started
[2026-05-08 09:00:00] MouseMover worker started - threshold 4min, nudge 5px, interval 15s
[2026-05-08 09:04:01] idle=240s -> nudge (count=1, post_idle=0.00s)
[2026-05-08 09:08:02] idle=240s -> nudge (count=2, post_idle=0.00s)
```

`post_idle=0.00s` — 마우스 이동 직후 유휴 시간이 0으로 리셋된 것을 의미합니다.

---

## 파일 구성

```
automouse.py   # 메인 소스 (설정 상수 포함)
build.bat      # Windows 빌드 스크립트 (PyInstaller)
icon.ico       # 앱 아이콘 (멀티해상도 16~256px)
icon.png       # 아이콘 소스 (투명 배경 크롭본)
```
