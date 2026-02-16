@echo off
chcp 65001 >nul 2>&1
title SQM 재고관리 시스템 v3.9.3

:: Python 확인
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

:: 작업 디렉토리 설정
cd /d "%~dp0"

:: ★★★ 유일한 진입점: run_app.py ★★★
if exist "run_app.py" (
    python run_app.py %*
) else (
    python -m gui_app_modular %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [오류] 프로그램이 비정상 종료되었습니다.
    pause
)
