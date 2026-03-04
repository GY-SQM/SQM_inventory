@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo SQM Patch Apply Script
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

call :apply_one "paste_table_dialog.patch"
call :apply_one "outbound_handlers.patch"
call :apply_one "outbound_mixin.patch"
call :apply_one "allocation_dialog.patch"

echo.
if "%FAILED%"=="0" (
    echo [OK] 모든 패치 적용이 완료되었습니다.
) else (
    echo [WARN] 일부 패치 적용에 실패했습니다. 위 로그를 확인하세요.
)
echo.
pause
exit /b %FAILED%

:apply_one
set PATCH_FILE=%~1

if not exist "%PATCH_FILE%" (
    echo [MISS] %PATCH_FILE% 파일이 없습니다.
    set FAILED=1
    goto :eof
)

echo [APPLY] %PATCH_FILE%
git apply --reject --whitespace=nowarn "%PATCH_FILE%"
if errorlevel 1 (
    echo [FAIL] %PATCH_FILE%
    set FAILED=1
) else (
    echo [DONE] %PATCH_FILE%
)
echo.
goto :eof
