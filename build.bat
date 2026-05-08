@echo off
REM ================================================================
REM  MouseMover build script (size-optimized, no Pillow/pystray)
REM  - Pure ctypes Win32 tray, no third-party runtime deps
REM  - Auto-downloads UPX if missing (for ~50%% size reduction)
REM  - Single .exe output around 4-6 MB
REM ================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "LOGFILE=build.log"
> "%LOGFILE%" echo === MouseMover build log ===
>> "%LOGFILE%" echo DATE=%DATE% TIME=%TIME%
>> "%LOGFILE%" echo CWD=%CD%

echo.
echo ================================================================
echo  MouseMover build (size-optimized)
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
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   Found: %%v

REM -------------------------------------------------------------- [2]
call :step "[2/6] Installing PyInstaller"
python -m pip install --upgrade pip 1>>"%LOGFILE%" 2>&1
python -m pip install --upgrade pyinstaller 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "PyInstaller install failed. Check build.log."
    goto :end
)

REM -------------------------------------------------------------- [3]
call :step "[3/6] Preparing UPX (size compression)"
set "UPX_OPT=--noupx"
set "UPX_DIR_OPT="
where upx 1>nul 2>&1
if not errorlevel 1 (
    echo   UPX found in PATH
    set "UPX_OPT="
    goto :upx_ready
)
if exist "upx\upx.exe" (
    echo   UPX found in local upx\ folder
    set "UPX_OPT="
    set "UPX_DIR_OPT=--upx-dir=upx"
    goto :upx_ready
)
echo   UPX not found - attempting auto-download from GitHub...
powershell -NoProfile -Command "try { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip' -OutFile 'upx.zip' -ErrorAction Stop; Expand-Archive -Path 'upx.zip' -DestinationPath '.' -Force; Move-Item -Force 'upx-4.2.4-win64' 'upx'; Remove-Item 'upx.zip'; exit 0 } catch { exit 1 }" 1>>"%LOGFILE%" 2>&1
if exist "upx\upx.exe" (
    echo   UPX downloaded successfully
    set "UPX_OPT="
    set "UPX_DIR_OPT=--upx-dir=upx"
) else (
    echo   UPX download failed - building without UPX (size will be ~7-8 MB instead of ~4-5 MB)
    echo   To enable UPX manually: download from https://upx.github.io/ and place upx.exe in PATH
)
:upx_ready

REM -------------------------------------------------------------- [4]
call :step "[4/6] Preparing icon"
if not exist icon.ico (
    call :fail "icon.ico not found. Cannot embed app icon."
    goto :end
)
echo   Using icon.ico

REM -------------------------------------------------------------- [5]
call :step "[5/6] Cleaning previous build artifacts"
if exist build rmdir /s /q build 1>>"%LOGFILE%" 2>&1
if exist dist rmdir /s /q dist 1>>"%LOGFILE%" 2>&1
if errorlevel 1 (
    call :fail "Cannot delete dist folder. If MouseMover.exe is running, exit it first."
    goto :end
)
if exist MouseMover.spec del /q MouseMover.spec

REM -------------------------------------------------------------- [6]
call :step "[6/6] Building .exe with PyInstaller"
echo   Running PyInstaller (this takes ~30 seconds)...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name MouseMover ^
    --icon=icon.ico ^
    --strip ^
    !UPX_OPT! ^
    !UPX_DIR_OPT! ^
    --exclude-module tkinter ^
    --exclude-module unittest ^
    --exclude-module test ^
    --exclude-module pydoc ^
    --exclude-module doctest ^
    --exclude-module xml ^
    --exclude-module xmlrpc ^
    --exclude-module email ^
    --exclude-module html ^
    --exclude-module http ^
    --exclude-module urllib ^
    --exclude-module pdb ^
    --exclude-module pkg_resources ^
    --exclude-module setuptools ^
    --exclude-module distutils ^
    automouse.py 1>>"%LOGFILE%" 2>&1

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
for %%I in (dist\MouseMover.exe) do (
    set /a SIZE_MB=%%~zI / 1048576
    set /a SIZE_KB=%%~zI / 1024
    echo   Output: %%~fI
    echo   Size:   !SIZE_MB! MB ^(!SIZE_KB! KB / %%~zI bytes^)
)
echo.
echo  HOW TO RUN: Double-click dist\MouseMover.exe
echo   - App icon appears in system tray (taskbar right side, hidden icons)
echo   - Hover over icon: shows "MouseMover" tooltip
echo   - Right-click: shows status + settings + Exit menu
echo ================================================================
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
