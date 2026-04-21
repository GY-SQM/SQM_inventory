@echo off
chcp 65001 > nul
title SQM Inventory v8.6.4.3 - 광양창고
cd /d "%~dp0"
echo.
echo ====================================================
echo  SQM Inventory v8.6.4.3 - 광양창고
echo ====================================================
echo.
echo  진입점: main_webview.py
echo  포트  : http://127.0.0.1:8765
echo.
python main_webview.py
if errorlevel 1 (
    echo.
    echo [ERROR] 실행 실패. 다음을 확인하세요:
    echo   1. Python 3.10+ 설치     ^(python --version^)
    echo   2. 의존성 설치           ^(pip install -r requirements_webview.txt^)
    pause
)
