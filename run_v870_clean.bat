@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

title SQM Inventory V870 CLEAN

echo.
echo ====================================================
echo  SQM Inventory V870 CLEAN - canonical launcher
echo ====================================================
echo  ROOT  : %CD%
echo  ENTRY : main_webview.py
echo  PORT  : auto ^(starts from http://127.0.0.1:8765^)
echo ====================================================
echo.

pythonw main_webview.py

if errorlevel 1 (
    echo.
    echo [ERROR] 실행 실패. 위 오류 메시지를 먼저 확인하세요.
    echo.
    echo [해결 방법]
    echo   1. 이미 열린 SQM 창이 있으면 그 창을 사용하거나 먼저 닫으세요.
    echo   2. 창이 없으면 작업 관리자에서 python.exe 또는 pythonw.exe 중 SQM 관련 프로세스를 끝내세요.
    echo   3. PID 확인: netstat -ano ^| findstr :8765
    echo   4. 관리자 권한 CMD에서 강제 종료: taskkill /F /PID ^<확인한 PID^>
    echo   5. 종료 후 run.bat를 다시 실행하세요.
    echo.
    echo [기본 점검]
    echo   - Python 설치 여부: python --version
    echo   - 의존성 설치: pip install -r requirements_webview.txt
    echo   - 로그 파일: sqm_debug.log
    pause
)
endlocal
