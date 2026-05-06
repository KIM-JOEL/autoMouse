@echo off
REM autoMouse 빌드 스크립트 (Windows 전용)
REM 사전 준비: Python 3.9 이상이 PATH에 등록되어 있어야 합니다. (https://www.python.org/downloads/)

setlocal
cd /d "%~dp0"

echo [1/3] PyInstaller 설치 확인...
python -m pip install --upgrade pip >nul
python -m pip install --upgrade pyinstaller || goto :error

echo [2/3] 기존 빌드 산출물 정리...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist automouse.spec del /q automouse.spec

echo [3/3] .exe 빌드 (백그라운드 실행, 단일 파일)...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name automouse ^
    automouse.py || goto :error

echo.
echo ========================================
echo  빌드 완료: dist\automouse.exe
echo  - 더블클릭하면 백그라운드에서 실행됩니다.
echo  - 종료하려면 작업 관리자에서 automouse.exe 프로세스를 종료하세요.
echo  - 동작 로그: 실행 파일과 같은 폴더의 automouse.log
echo  - 부팅 시 자동 실행: dist\automouse.exe 의 바로가기를
echo    "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\Startup" 폴더에 복사하세요.
echo ========================================
endlocal
exit /b 0

:error
echo.
echo [실패] 빌드 중 오류가 발생했습니다.
endlocal
exit /b 1
