@echo off
chcp 949 > nul

:: ================================================
:: Claude AutoPilot - 범용 실행 파일
:: 1. set PROJECT 와 set CLAUDE 두 줄만 수정하세요
:: ================================================

set PROJECT=여기에_프로젝트_전체경로_입력
set CLAUDE=claude

:: claude.exe 경로 확인 (PowerShell):
:: (Get-Command claude).Source
:: 예시: set CLAUDE=C:\Users\사용자명\.local\bin\claude.exe

:: ================================================
:: 아래는 수정하지 마세요
:: ================================================

cd /d "%PROJECT%"
echo.
echo [Claude AutoPilot] 사전 점검 시작
echo.

if not exist ".env" (
    echo [FAIL] .env 없음
    echo config\.env.template 을 .env 로 복사 후 설정하세요
    exit /b 1
)
echo [OK] .env

if not exist "scripts\telegram_bridge.py" (
    echo [FAIL] scripts\telegram_bridge.py 없음
    exit /b 1
)
echo [OK] telegram_bridge.py

if not exist "scripts\watchdog.py" (
    echo [FAIL] scripts\watchdog.py 없음
    exit /b 1
)
echo [OK] watchdog.py

if not exist "MASTER.md" (
    if not exist "MASTER_FINAL.md" (
        echo [FAIL] MASTER.md 없음
        echo templates\MASTER_TEMPLATE.md 를 MASTER.md 로 복사 후 작성하세요
        exit /b 1
    )
)
echo [OK] MASTER 파일 존재

"%CLAUDE%" --version > nul 2>&1
if errorlevel 1 (
    echo [FAIL] Claude Code 없음: %CLAUDE%
    exit /b 1
)
echo [OK] Claude Code OK

echo.
echo [ALL PRE-TESTS PASSED]
echo.
echo ============================================
echo   1. Telegram Bridge + Watchdog
echo      Claude Code : NEW window
echo      Bridge      : THIS window
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
echo [STEP 1] Claude Code 새 창 실행...
start "Claude Code" cmd /k "cd /d "%PROJECT%" && "%CLAUDE%" --dangerously-skip-permissions"
timeout /t 3 > nul
echo [STEP 2] Watchdog + Bridge 시작...
python "scripts\watchdog.py"
goto end

:direct
echo.
"%CLAUDE%" --dangerously-skip-permissions
goto end

:end
echo Done: %date% %time%
