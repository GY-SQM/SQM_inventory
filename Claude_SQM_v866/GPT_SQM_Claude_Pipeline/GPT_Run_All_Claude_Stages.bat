@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul

REM =============================================================
REM GPT_Run_All_Claude_Stages.bat
REM 목적:
REM   - B00 ~ B13 단계를 순차 실행
REM   - 각 단계 시작 / 성공 / 실패를 텔레그램으로 알림
REM   - 내부적으로 GPT_Run_Claude_Stage.bat 호출
REM   - 실제 Claude 실행 명령:
REM     claude --dangerously-skip-permissions --system-prompt-file "파일이름.md"
REM =============================================================

set "PROJECT_ROOT=%~dp0"
pushd "%PROJECT_ROOT%" >nul

REM ===== 텔레그램 설정 =====
set "TELEGRAM_BOT_TOKEN=8665850610:AAFx9Jcti2_jCKqjs1ZxFcHd18FtywO5-h8"
set "TELEGRAM_CHAT_ID=538125119"
set "TELEGRAM_PS1=%PROJECT_ROOT%GPT_Send_Telegram.ps1"

REM ===== 단계 실행기 =====
set "STAGE_RUNNER=%PROJECT_ROOT%GPT_Run_Claude_Stage.bat"

if not exist "%STAGE_RUNNER%" (
    echo [ERROR] GPT_Run_Claude_Stage.bat 파일이 없습니다.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] 실행 중단 - GPT_Run_Claude_Stage.bat 파일이 없습니다."
    popd >nul
    exit /b 1
)

if not exist "%TELEGRAM_PS1%" (
    echo [ERROR] GPT_Send_Telegram.ps1 파일이 없습니다.
    popd >nul
    exit /b 1
)

REM ===== 실행 모드 =====
set "RUN_MODE=%~1"
if "%RUN_MODE%"=="" set "RUN_MODE=FULL"

set "RUN_LIST="
if /I "%RUN_MODE%"=="FULL" set "RUN_LIST=B00 B01 B02 B03 B04 B05 B06 B07 B08 B09 B10 B11 B12 B13"
if /I "%RUN_MODE%"=="P0"   set "RUN_LIST=B00 B01 B02 B03 B04"
if /I "%RUN_MODE%"=="P1"   set "RUN_LIST=B05 B06 B07 B08 B09"
if /I "%RUN_MODE%"=="P2"   set "RUN_LIST=B10 B11 B12 B13"

if "%RUN_LIST%"=="" (
    echo [ERROR] 잘못된 실행 모드입니다. FULL / P0 / P1 / P2 중 하나를 사용하세요.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] 실행 중단 - 잘못된 실행 모드: %RUN_MODE%"
    popd >nul
    exit /b 1
)

echo =========================================
echo SQM Claude Stage Master Runner
echo Project : %PROJECT_ROOT%
echo Mode    : %RUN_MODE%
echo Stages  : %RUN_LIST%
echo =========================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] 전체 실행 시작 - Mode=%RUN_MODE% / Stages=%RUN_LIST%"

for %%S in (%RUN_LIST%) do (
    call :RUN_STAGE %%S
    if errorlevel 1 (
        echo [STOP] %%S 단계에서 실패하여 전체 실행을 중단합니다.
        powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] 전체 실행 중단 - %%S 단계 실패"
        popd >nul
        exit /b 1
    )
)

echo =========================================
echo 모든 단계 실행 완료
echo =========================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] 전체 실행 완료 - Mode=%RUN_MODE%"

popd >nul
exit /b 0

:RUN_STAGE
set "STAGE=%~1"
set "PROMPT_FILE="
call :RESOLVE_PROMPT_FILE "%STAGE%"

if "%PROMPT_FILE%"=="" (
    echo [ERROR] %STAGE% 에 대응하는 프롬프트 파일을 찾지 못했습니다.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] %STAGE% 실패 - 프롬프트 파일 미확인"
    exit /b 1
)

if not exist "%PROMPT_FILE%" (
    echo [ERROR] 프롬프트 파일이 없습니다: %PROMPT_FILE%
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] %STAGE% 실패 - 프롬프트 파일 없음"
    exit /b 1
)

echo.
echo -----------------------------------------
echo [%STAGE%] 시작
echo Prompt: %PROMPT_FILE%
echo -----------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] %STAGE% 시작"

call "%STAGE_RUNNER%" %STAGE% "%PROMPT_FILE%"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo [ERROR] %STAGE% 단계 실행 실패 (RC=%RC%)
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] %STAGE% 실패 - RC=%RC%"
    exit /b 1
)

echo [OK] %STAGE% 단계 통과
powershell -NoProfile -ExecutionPolicy Bypass -File "%TELEGRAM_PS1%" -BotToken "%TELEGRAM_BOT_TOKEN%" -ChatId "%TELEGRAM_CHAT_ID%" -Message "[SQM] %STAGE% 통과"
exit /b 0

:RESOLVE_PROMPT_FILE
set "STAGE_NAME=%~1"
set "STAGE_NAME=%STAGE_NAME:\=%"
set "STAGE_NAME=%STAGE_NAME:"=%"

if /I "%STAGE_NAME%"=="B00" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B00_prepare.md"
if /I "%STAGE_NAME%"=="B01" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B01_audit.md"
if /I "%STAGE_NAME%"=="B02" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B02_tx_guard.md"
if /I "%STAGE_NAME%"=="B03" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B03_status_guard.md"
if /I "%STAGE_NAME%"=="B04" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B04_integrity_guard.md"
if /I "%STAGE_NAME%"=="B05" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B05_outbound_handlers_split.md"
if /I "%STAGE_NAME%"=="B06" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B06_advanced_dialogs_split.md"
if /I "%STAGE_NAME%"=="B07" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B07_onestop_inbound_exceptions.md"
if /I "%STAGE_NAME%"=="B08" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B08_query_dedup.md"
if /I "%STAGE_NAME%"=="B09" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B09_refresh_after_cleanup.md"
if /I "%STAGE_NAME%"=="B10" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B10_quality_cleanup.md"
if /I "%STAGE_NAME%"=="B11" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B11_perf_tuning.md"
if /I "%STAGE_NAME%"=="B12" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B12_architecture_boundary.md"
if /I "%STAGE_NAME%"=="B13" set "PROMPT_FILE=%PROJECT_ROOT%auto_tasks\B13_final_validation.md"
exit /b 0
