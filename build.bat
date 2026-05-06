@echo off
REM ================================================================
REM  MouseMover 빌드 스크립트
REM  - 단계별로 진행 상황과 에러를 화면 + build.log 에 기록
REM  - 어느 단계에서 실패했는지 즉시 확인 가능
REM  - 종료 시 창이 자동으로 닫히지 않도록 pause
REM ================================================================
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "LOGFILE=build.log"
> "%LOGFILE%" echo === MouseMover build log ===
>> "%LOGFILE%" echo DATE=%DATE% TIME=%TIME%
>> "%LOGFILE%" echo CWD=%CD%
>> "%LOGFILE%" echo USER=%USERNAME%

echo.
echo ================================================================
echo  MouseMover 빌드 시작
echo  로그 파일: %CD%\%LOGFILE%
echo ================================================================

REM -------------------------------------------------------------- [1]
call :step "[1/6] Python 설치 확인"
where python 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "Python 이 PATH 에 없습니다. https://www.python.org/downloads/ 에서 Python 3.9+ 설치 후 'Add Python to PATH' 체크박스 필수"
    goto :end
)
python --version 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "python --version 호출 실패. 설치된 Python 이 손상되었을 수 있습니다."
    goto :end
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   감지: %%v

REM -------------------------------------------------------------- [2]
call :step "[2/6] pip 업그레이드"
python -m pip install --upgrade pip 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "pip 업그레이드 실패. 사내망/프록시 차단일 수 있음. build.log 마지막 부분 확인"
    goto :end
)

REM -------------------------------------------------------------- [3]
call :step "[3/6] 의존 패키지 설치 (pyinstaller, pystray, Pillow)"
python -m pip install --upgrade pyinstaller pystray Pillow 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "의존 패키지 설치 실패. build.log 마지막 부분에 pip 에러 메시지 있음"
    goto :end
)

REM -------------------------------------------------------------- [4]
call :step "[4/6] 아이콘 준비"
if exist icon.ico (
    echo   icon.ico 사용
    >> "%LOGFILE%" echo icon.ico exists - using as is
) else (
    if exist icon.png (
        echo   icon.png 발견 - icon.ico 자동 생성
        python -c "from PIL import Image; im=Image.open('icon.png').convert('RGBA'); im.save('icon.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])" 1>>"%LOGFILE%" 2>&1
        if errorlevel 1 (
            call :fail "icon.png -> icon.ico 변환 실패. build.log 확인"
            goto :end
        )
    ) else (
        echo   icon.ico/icon.png 없음 - 코드 내장 폴백 아이콘 사용
        >> "%LOGFILE%" echo no icon files - fallback will be used
    )
)

REM -------------------------------------------------------------- [5]
call :step "[5/6] 기존 빌드 산출물 정리"
if exist build (
    rmdir /s /q build 1>>"%LOGFILE%" 2>&1
    if errorlevel 1 (
        call :fail "build 폴더 삭제 실패. 다른 프로세스 점유 여부 확인"
        goto :end
    )
)
if exist dist (
    rmdir /s /q dist 1>>"%LOGFILE%" 2>&1
    if errorlevel 1 (
        call :fail "dist 폴더 삭제 실패. dist\MouseMover.exe 실행 중이면 먼저 종료"
        goto :end
    )
)
if exist MouseMover.spec del /q MouseMover.spec

REM -------------------------------------------------------------- [6]
call :step "[6/6] PyInstaller 빌드"
set "ICON_OPT="
set "DATA_OPT="
if exist icon.ico (
    set "ICON_OPT=--icon=icon.ico"
    set "DATA_OPT=--add-data icon.ico;."
)
echo   명령: python -m PyInstaller --onefile --noconsole --name MouseMover !ICON_OPT! !DATA_OPT! automouse.py
>> "%LOGFILE%" echo CMD: python -m PyInstaller --onefile --noconsole --name MouseMover !ICON_OPT! !DATA_OPT! automouse.py
python -m PyInstaller --onefile --noconsole --name MouseMover !ICON_OPT! !DATA_OPT! automouse.py 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "PyInstaller 빌드 실패. build.log 마지막 50줄에 PyInstaller 출력 있음"
    goto :end
)
if not exist dist\MouseMover.exe (
    call :fail "빌드 명령은 성공했으나 dist\MouseMover.exe 가 생성되지 않음"
    goto :end
)

REM ----------------------------------------------------------- 성공
echo.
echo ================================================================
echo  [SUCCESS] 빌드 성공
for %%I in (dist\MouseMover.exe) do echo     산출물: %%~fI  (%%~zI bytes)
echo     로그:   %CD%\%LOGFILE%
echo.
echo  실행: dist\MouseMover.exe 더블클릭
echo   - 시스템 트레이(작업표시줄 우측 ^^ 숨겨진 아이콘)에 마우스 아이콘 등장
echo   - 호버 시 "MouseMover" 툴팁 표시
echo   - 우클릭: 상태/설정/종료 메뉴
echo ================================================================
>> "%LOGFILE%" echo === BUILD SUCCESS ===
goto :end


REM ============================== 서브루틴 ==============================
:step
echo.
echo --- %~1 ---
>> "%LOGFILE%" echo.
>> "%LOGFILE%" echo === %~1 ===
exit /b 0

:fail
echo.
echo ================================================================
echo  [FAIL] %~1
echo  상세 로그: %CD%\%LOGFILE%  (마지막 부분 확인)
echo ================================================================
>> "%LOGFILE%" echo === FAIL: %~1 ===
exit /b 0

:end
echo.
echo (창을 닫으려면 아무 키나 누르세요)
pause >nul
endlocal
exit /b 0
