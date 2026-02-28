@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo SQM Patch Dry-Run Check Script
echo ============================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] git 실행 파일을 찾을 수 없습니다.
    echo Git for Windows 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

set FAILED=0

call :check_one "paste_table_dialog.patch"
call :check_one "outbound_handlers.patch"
call :check_one "outbound_mixin.patch"
call :check_one "allocation_dialog.patch"

echo.
if "%FAILED%"=="0" (
    echo [OK] 모든 패치가 적용 가능한 상태입니다.
) else (
    echo [WARN] 일부 패치는 현재 상태에서 적용 불가입니다.
    echo        파일 변경/중복 적용 여부를 확인하세요.
)
echo.
pause
exit /b %FAILED%

:check_one
set PATCH_FILE=%~1

if not exist "%PATCH_FILE%" (
    echo [MISS] %PATCH_FILE% 파일이 없습니다.
    set FAILED=1
    goto :eof
)

echo [CHECK] %PATCH_FILE%
git apply --check --whitespace=nowarn "%PATCH_FILE%"
if errorlevel 1 (
    echo [FAIL] %PATCH_FILE%
    set FAILED=1
) else (
    echo [PASS] %PATCH_FILE%
)
echo.
goto :eof
