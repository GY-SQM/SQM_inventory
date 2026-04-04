@echo off
chcp 65001 >nul
title SQM v867 Master Runner

echo ============================================
echo   SQM v867 Master Runner
echo   %date% %time%
echo ============================================
echo.

cd /d "%~dp0"
set "LOG=logs\run_log.txt"

:: logs 디렉토리 확인
if not exist logs mkdir logs

:: ===== Pre-Test =====
echo [Pre-Test] 시작...
echo %date% %time% [Pre-Test] 시작 >> %LOG%

:: 1. .env 확인
if not exist .env (
    echo [FAIL] .env 파일 없음
    echo %date% %time% [FAIL] .env 없음 >> %LOG%
    goto :fail
)
echo   [OK] .env 존재

:: 2. MASTER.md 확인
if not exist "MASTER_FINAL_v867_통합완성본.md" (
    echo [FAIL] MASTER 파일 없음
    echo %date% %time% [FAIL] MASTER 없음 >> %LOG%
    goto :fail
)
echo   [OK] MASTER 파일 존재

:: 3. Bridge 파일 확인
if not exist "scripts\telegram_bridge.py" (
    echo [FAIL] telegram_bridge.py 없음
    echo %date% %time% [FAIL] bridge 없음 >> %LOG%
    goto :fail
)
echo   [OK] Bridge 파일 존재

:: 4. requests 패키지 확인
python -c "import requests" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] requests 패키지 설치 중...
    pip install requests -q
)
echo   [OK] requests 패키지

:: 5. 절전 방지
powercfg -change -standby-timeout-ac 0
powercfg -change -monitor-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0
echo   [OK] 절전 방지 설정

echo.
echo [Pre-Test] 모두 통과!
echo %date% %time% [Pre-Test] 모두 통과 >> %LOG%
echo.

:: ===== 실행 모드 선택 =====
echo 실행 모드:
echo   1. Telegram Bridge (권장 - 원격 모니터링 가능)
echo   2. Claude 직접 실행 (질문 없이 자동 진행)
echo   3. 종료
echo.
set /p MODE="선택 (1/2/3): "

if "%MODE%"=="1" (
    echo.
    echo Telegram Bridge 실행...
    echo %date% %time% Bridge 실행 >> %LOG%
    python scripts\telegram_bridge.py
) else if "%MODE%"=="2" (
    echo.
    echo Claude 직접 실행...
    echo %date% %time% Claude 직접 실행 >> %LOG%
    claude --dangerously-skip-permissions -p "이 파일을 읽고 모든 지시를 수행하라: MASTER_FINAL_v867_통합완성본.md"
) else (
    echo 종료.
)

:: 절전 복구
powercfg -change -standby-timeout-ac 30
powercfg -change -monitor-timeout-ac 10

goto :end

:fail
echo.
echo ============================================
echo   Pre-Test 실패. 다음 단계 진행 금지.
echo ============================================
echo %date% %time% [ABORT] Pre-Test 실패 >> %LOG%
pause

:end
echo.
echo %date% %time% 실행 완료 >> %LOG%
