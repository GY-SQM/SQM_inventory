@echo off
chcp 65001 > nul
title SQM v8.6.9 재고관리 서버

echo.
echo ========================================
echo   SQM v8.6.9 재고관리 서버 시작
echo ========================================
echo.

:: 현재 배치파일 위치로 이동
cd /d "%~dp0"

:: Python 경로
set PYTHON=C:\Python314\python.exe

:: Python 존재 확인
if not exist "%PYTHON%" (
    echo [오류] Python을 찾을 수 없습니다: %PYTHON%
    echo C:\Python314 에 Python이 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

:: 서버 시작
echo [시작] FastAPI 서버를 시작합니다...
echo [접속] 브라우저에서 http://localhost:8000 으로 접속하세요
echo.
echo [주의] 이 창을 닫으면 서버가 종료됩니다!
echo        최소화만 하세요.
echo.

"%PYTHON%" run_react_api.py

:: 서버가 종료되면 (오류 시)
echo.
echo [종료] 서버가 종료되었습니다.
echo 오류가 있으면 위 메시지를 Ruby에게 복사해서 보내주세요.
pause
