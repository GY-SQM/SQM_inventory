@echo off
chcp 65001 >nul
title SQM_Desktop
cd /d "%~dp0"

echo ============================================
echo   SQM Desktop App - pywebview Start
echo ============================================
echo.

py -3.12 --version >nul 2>&1
if not errorlevel 1 goto use312

py -3.13 --version >nul 2>&1
if not errorlevel 1 goto use313

python --version >nul 2>&1
if not errorlevel 1 goto usepy

echo [ERROR] Python not found.
pause
exit /b 1

:use312
echo [INFO] Using: py -3.12
py -3.12 "%~dp0run_desktop.py"
goto check

:use313
echo [INFO] Using: py -3.13
py -3.13 "%~dp0run_desktop.py"
goto check

:usepy
echo [INFO] Using: python
python "%~dp0run_desktop.py"
goto check

:check
if errorlevel 1 (
    echo.
    echo [ERROR] SQM Desktop failed. Check log above.
    pause
)
