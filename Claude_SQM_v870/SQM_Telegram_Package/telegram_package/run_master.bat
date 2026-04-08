@echo off
F:
cd "프로그램\Sqm 재고관리\Claude_SQM_v868"
echo ROOT: %CD%
if not exist "react_api\main.py" goto fail1
echo [OK] react_api found
if not exist ".env" goto fail2
echo [OK] .env found
if not exist "scripts\telegram_bridge.py" goto fail3
echo [OK] bridge found
if not exist "SQM_무중단_작업지시서.md" goto fail4
echo [OK] MASTER found
echo.
echo [ALL PRE-TESTS PASSED]
echo.
echo 1. Telegram Bridge (Recommended)
echo 2. Claude Direct Run
echo 3. Exit
echo.
set /p MODE=Choice (1/2/3): 
if "%MODE%"=="1" goto bridge
if "%MODE%"=="2" goto direct
goto end

:bridge
echo Starting Telegram Bridge...
python scripts\telegram_bridge.py
goto end

:direct
echo Starting Claude Direct Run...
claude --dangerously-skip-permissions -p "Execute SQM_master"
goto end

:fail1
echo [FAIL] react_api not found
pause
exit /b 1

:fail2
echo [FAIL] .env not found
pause
exit /b 1

:fail3
echo [FAIL] telegram_bridge.py not found
pause
exit /b 1

:fail4
echo [FAIL] MASTER file not found
pause
exit /b 1

:end
echo.
echo Done.
pause
