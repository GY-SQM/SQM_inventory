@echo off
chcp 65001 > nul

set "PROJECT=D:\program\Sqm jaego\Claude_SQM_v870"
set "CLAUDE=C:\Users\kidon\.local\bin\claude.exe"

cd /d "%PROJECT%"
echo.
echo ROOT: %CD%
echo.

if not exist "react_api\main.py" (
    echo [FAIL] react_api not found
    exit /b 1
)
echo [OK] react_api

if not exist ".env" (
    echo [FAIL] .env not found
    exit /b 1
)
echo [OK] .env

if not exist "scripts\telegram_bridge.py" (
    echo [FAIL] telegram_bridge.py not found
    exit /b 1
)
echo [OK] telegram_bridge.py

if not exist "scripts\watchdog.py" (
    echo [FAIL] watchdog.py not found
    exit /b 1
)
echo [OK] watchdog.py

if not exist "MASTER.md" (
    echo [FAIL] MASTER.md not found
    exit /b 1
)
echo [OK] MASTER.md found

"%CLAUDE%" --version > nul 2>&1
if errorlevel 1 (
    echo [FAIL] Claude not found
    exit /b 1
)
echo [OK] Claude Code OK

echo.
echo [ALL PRE-TESTS PASSED]
echo.

if not exist "logs" mkdir logs

echo ============================================
echo   1. Telegram Bridge + Watchdog
echo   2. Claude Direct Run
echo   3. Exit
echo ============================================
echo.
choice /C 123 /T 10 /D 1 /M "Select (auto 1 after 10sec)"
if errorlevel 3 goto end
if errorlevel 2 goto direct
goto bridge

:bridge
echo.
echo [STEP 1] Claude Code new window opening...
start "ClaudeCode" cmd /c "chcp 65001 > nul && cd /d "%PROJECT%" && "%CLAUDE%" --dangerously-skip-permissions"
timeout /t 3 > nul
echo [STEP 2] Starting Watchdog + Bridge...
python "%PROJECT%\scripts\watchdog.py"
goto end

:direct
echo.
"%CLAUDE%" --dangerously-skip-permissions
goto end

:end
echo Done: %date% %time%
