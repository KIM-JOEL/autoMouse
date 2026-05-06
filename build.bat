@echo off
REM MouseMover 빌드 스크립트 (Windows 전용)
REM 사전 준비: Python 3.9 이상이 PATH에 등록되어 있어야 합니다.

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [1/4] 의존 패키지 설치...
python -m pip install --upgrade pip >nul
python -m pip install --upgrade pyinstaller pystray Pillow || goto :error

echo [2/4] 아이콘 준비...
REM icon.ico 가 없고 icon.png 가 있으면 .ico 자동 생성
if not exist icon.ico (
    if exist icon.png (
        echo   icon.png 감지 - icon.ico 자동 생성 중...
        python -c "from PIL import Image; im = Image.open('icon.png').convert('RGBA'); im.save('icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])" || goto :error
    ) else (
        echo   icon.ico / icon.png 없음 - 기본 생성 아이콘 사용
    )
)

echo [3/4] 기존 빌드 산출물 정리...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MouseMover.spec del /q MouseMover.spec

echo [4/4] .exe 빌드 (백그라운드 실행, 단일 파일)...
set ICON_OPT=
set DATA_OPT=
if exist icon.ico (
    set ICON_OPT=--icon=icon.ico
    set DATA_OPT=--add-data icon.ico;.
)

python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name MouseMover ^
    !ICON_OPT! ^
    !DATA_OPT! ^
    automouse.py || goto :error

echo.
echo ========================================
echo  빌드 완료: dist\MouseMover.exe
echo  - 더블클릭하면 시스템 트레이(숨겨진 아이콘)에 등록됩니다.
echo  - 아이콘에 마우스를 올리면 "MouseMover" 툴팁이 표시됩니다.
echo  - 우클릭하면 상태 표시 + [종료] 메뉴가 나옵니다.
echo  - 동작 로그: 실행 파일과 같은 폴더의 automouse.log
echo  - 부팅 시 자동 실행: 바로가기를
echo    "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\Startup"
echo    폴더에 복사하세요.
echo ========================================
endlocal
exit /b 0

:error
echo.
echo [실패] 빌드 중 오류가 발생했습니다.
endlocal
exit /b 1
