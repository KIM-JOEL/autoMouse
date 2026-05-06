@echo off
REM ================================================================
REM  MouseMover build script (ASCII-only, works on any Windows)
REM  - Logs each step to build.log AND to the console
REM  - Window stays open after success or failure (pause at end)
REM ================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "LOGFILE=build.log"
> "%LOGFILE%" echo === MouseMover build log ===
>> "%LOGFILE%" echo DATE=%DATE% TIME=%TIME%
>> "%LOGFILE%" echo CWD=%CD%
>> "%LOGFILE%" echo USER=%USERNAME%

echo.
echo ================================================================
echo  MouseMover build starting...
echo  Log file: %CD%\%LOGFILE%
echo ================================================================

REM -------------------------------------------------------------- [1]
call :step "[1/6] Checking Python installation"
where python 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "Python not found in PATH."
    echo.
    echo  HOW TO FIX: Install Python 3.9+ from https://www.python.org/downloads/
    echo  On the installer screen, CHECK the box: 'Add Python to PATH'
    goto :end
)
python --version 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "python --version failed. Python installation may be corrupted."
    goto :end
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   Found: %%v

REM -------------------------------------------------------------- [2]
call :step "[2/6] Upgrading pip"
python -m pip install --upgrade pip 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "pip upgrade failed. Possible cause: corporate proxy/firewall. Check build.log."
    goto :end
)

REM -------------------------------------------------------------- [3]
call :step "[3/6] Installing dependencies (pyinstaller, pystray, Pillow)"
python -m pip install --upgrade pyinstaller pystray Pillow 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "Dependency install failed. Check build.log for pip error details."
    goto :end
)

REM -------------------------------------------------------------- [4]
call :step "[4/6] Preparing icon"
if exist icon.ico (
    echo   Using existing icon.ico
    >> "%LOGFILE%" echo icon.ico found - using as is
) else (
    if exist icon.png (
        echo   icon.png found - auto-converting to icon.ico
        python -c "from PIL import Image; im=Image.open('icon.png').convert('RGBA'); im.save('icon.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])" 1>>"%LOGFILE%" 2>&1
        if errorlevel 1 (
            call :fail "Failed to convert icon.png to icon.ico. Check build.log."
            goto :end
        )
    ) else (
        echo   No icon.ico/icon.png found - will use built-in fallback icon
        >> "%LOGFILE%" echo no icon files - using fallback
    )
)

REM -------------------------------------------------------------- [5]
call :step "[5/6] Cleaning previous build artifacts"
if exist build (
    rmdir /s /q build 1>>"%LOGFILE%" 2>&1
    if errorlevel 1 (
        call :fail "Cannot delete 'build' folder. Another process may be using it."
        goto :end
    )
)
if exist dist (
    rmdir /s /q dist 1>>"%LOGFILE%" 2>&1
    if errorlevel 1 (
        call :fail "Cannot delete 'dist' folder. If MouseMover.exe is running, stop it first."
        goto :end
    )
)
if exist MouseMover.spec del /q MouseMover.spec

REM -------------------------------------------------------------- [6]
call :step "[6/6] Building .exe with PyInstaller"
set "ICON_OPT="
set "DATA_OPT="
if exist icon.ico (
    set "ICON_OPT=--icon=icon.ico"
    set "DATA_OPT=--add-data icon.ico;."
)
echo   Running: python -m PyInstaller --onefile --noconsole --name MouseMover !ICON_OPT! !DATA_OPT! automouse.py
>> "%LOGFILE%" echo CMD: python -m PyInstaller --onefile --noconsole --name MouseMover !ICON_OPT! !DATA_OPT! automouse.py

python -m PyInstaller --onefile --noconsole --name MouseMover !ICON_OPT! !DATA_OPT! automouse.py 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "PyInstaller build failed. Check the last 50 lines of build.log."
    goto :end
)
if not exist dist\MouseMover.exe (
    call :fail "Build command succeeded but dist\MouseMover.exe was not created."
    goto :end
)

REM ----------------------------------------------------------- SUCCESS
echo.
echo ================================================================
echo  [SUCCESS] Build complete!
for %%I in (dist\MouseMover.exe) do echo   Output: %%~fI  (%%~zI bytes)
echo   Log:    %CD%\%LOGFILE%
echo.
echo  HOW TO RUN: Double-click dist\MouseMover.exe
echo   - App icon appears in system tray (taskbar right side, hidden icons)
echo   - Hover over icon: shows "MouseMover" tooltip
echo   - Right-click: shows status + settings + Exit menu
echo ================================================================
>> "%LOGFILE%" echo === BUILD SUCCESS ===
goto :end


REM ============================== subroutines ==============================
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
echo  Details: %CD%\%LOGFILE%  (check the last lines)
echo ================================================================
>> "%LOGFILE%" echo === FAIL: %~1 ===
exit /b 0

:end
echo.
echo  Press any key to close this window...
pause >nul
endlocal
exit /b 0
