@echo off

echo.
echo  ========================================
echo   Claude AutoPilot - SQM v8.7.1
echo   Telegram Bridge Start
echo  ========================================
echo.

python --version >/dev/null 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

python -c "import requests" >/dev/null 2>&1
if errorlevel 1 (
    pip install requests
)

powercfg /change standby-timeout-ac 0 >/dev/null 2>&1
powercfg /change monitor-timeout-ac 0 >/dev/null 2>&1

echo  [ALL CHECKS PASSED]
echo  Telegram: /help /status /progress /log /restart /stop
echo.

python "%~dp0scripts\telegram_bridge.py" "%~dp0MASTER.md"

echo.
echo [Done] Bridge stopped
pause
