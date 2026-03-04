@echo off
:: SQM 재고관리 시스템 - 공식 실행 (엔트리: run.py)
title SQM Inventory Manager
color 0A
cls

echo ======================================================
echo    SQM 재고관리 시스템 시작 중...
echo    (진입점: run.py)
echo ======================================================
echo.

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python이 설치되어 있지 않거나 PATH에 없습니다.
    pause
    exit /b 1
)

python run.py

if %errorlevel% neq 0 (
    echo.
    echo ------------------------------------------------------
    echo [오류] 프로그램이 비정상 종료되었습니다.
    echo logs 폴더의 최신 로그를 확인하세요.
    echo ------------------------------------------------------
    pause
)

exit /b %errorlevel%
