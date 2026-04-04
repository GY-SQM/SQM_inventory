@echo off
setlocal

REM Usage:
REM   GPT_Run_Claude_Stage.bat B00 auto_tasks\B00_prepare.md
REM   GPT_Run_Claude_Stage.bat B03 auto_tasks\B03_status_guard.md

if "%~1"=="" (
    echo [ERROR] Stage ID is required. Example: B00
    exit /b 1
)

if "%~2"=="" (
    echo [ERROR] Prompt file path is required. Example: auto_tasks\B00_prepare.md
    exit /b 1
)

set "STAGE_ID=%~1"
set "PROMPT_FILE=%~2"
set "SCRIPT_DIR=%~dp0"
set "PS1_FILE=%SCRIPT_DIR%GPT_Run_Claude_Stage.ps1"

if not exist "%PS1_FILE%" (
    echo [ERROR] PowerShell script not found: "%PS1_FILE%"
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_FILE%" -StageId "%STAGE_ID%" -PromptFile "%PROMPT_FILE%"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
    echo [ERROR] Stage %STAGE_ID% finished with exit code %EXITCODE%.
    exit /b %EXITCODE%
)

echo [OK] Stage %STAGE_ID% finished.
exit /b 0
