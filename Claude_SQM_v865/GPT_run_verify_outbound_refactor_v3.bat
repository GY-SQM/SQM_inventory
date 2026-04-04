@echo off
setlocal

REM ============================================================
REM GPT_run_verify_outbound_refactor_v3.bat
REM Usage:
REM   1) Put this .bat in the same folder as GPT_verify_outbound_refactor_v3.py
REM   2) Run with no argument inside the target repo folder
REM      or pass the repo folder as the first argument
REM
REM Examples:
REM   GPT_run_verify_outbound_refactor_v3.bat
REM   GPT_run_verify_outbound_refactor_v3.bat "F:\프로그램\Sqm 재고관리\Claude_SQM_v864_20260329_FULL"
REM ============================================================

chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "PY_SCRIPT=%SCRIPT_DIR%GPT_verify_outbound_refactor_v3.py"

if not exist "%PY_SCRIPT%" (
    echo [ERROR] Python verification script not found:
    echo         %PY_SCRIPT%
    echo.
    echo Put this .bat in the same folder as GPT_verify_outbound_refactor_v3.py
    pause
    exit /b 1
)

set "REPO_DIR=%~1"
if "%REPO_DIR%"=="" set "REPO_DIR=%CD%"

if not exist "%REPO_DIR%" (
    echo [ERROR] Repo folder does not exist:
    echo         %REPO_DIR%
    pause
    exit /b 1
)

set "JSON_OUT=%REPO_DIR%\verify_outbound_refactor_report.json"

echo ============================================================
echo Running outbound refactor verification
echo ------------------------------------------------------------
echo Script : %PY_SCRIPT%
echo Repo   : %REPO_DIR%
echo Report : %JSON_OUT%
echo ============================================================
echo.

python "%PY_SCRIPT%" --repo "%REPO_DIR%" --json-out "%JSON_OUT%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ============================================================
echo Finished with exit code: %EXIT_CODE%
echo ============================================================

if exist "%JSON_OUT%" (
    echo JSON report saved:
    echo %JSON_OUT%
)

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [WARN] Verification finished with warnings or failures.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo [OK] Verification completed successfully.
pause
exit /b 0
