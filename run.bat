@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    py run.py
) else (
    python run.py
)

if errorlevel 1 (
    echo.
    echo [ERROR] run.py 실행 중 오류가 발생했습니다.
    pause
)

endlocal
