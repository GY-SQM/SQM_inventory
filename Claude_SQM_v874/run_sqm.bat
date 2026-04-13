@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: ── 1단계: 자기 자신을 최소화 상태로 재실행 ──
if /i not "%~1"=="--go" (
    start /min "" cmd /c ""%~f0" --go"
    exit
)

:: ── 2단계: 필수 파일 점검 (최소화 상태에서 실행) ──
set FAIL=0
if not exist ".env" set FAIL=1
if not exist "data\db\sqm_inventory.db" set FAIL=1
if not exist "react_api\main.py" set FAIL=1
if not exist "web\dist\index.html" set FAIL=1

if %FAIL%==1 (
    echo [ERROR] 필수 파일 누락. 관리자에게 문의하세요.
    pause
    exit /b 1
)

:: ── 3단계: Python 선택 (3.12 우선) ──
set PY=
py -3.12 -c "import clr; import webview" >nul 2>&1
if not errorlevel 1 (
    start "" pyw -3.12 "%~dp0run_desktop.py"
    exit
)
py -3.13 -c "import clr; import webview" >nul 2>&1
if not errorlevel 1 (
    start "" pyw -3.13 "%~dp0run_desktop.py"
    exit
)

:: ── 4단계: pythonnet 없으면 브라우저 모드 ──
set PY=python
py -3.12 --version >nul 2>&1 && set PY=py -3.12
py -3.13 --version >nul 2>&1 && set PY=py -3.13

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
timeout /t 1 /nobreak >nul
start "SQM-Server" cmd /k "cd /d "%~dp0" && set PYTHONPATH=%~dp0 && %PY% run_react_api.py"
timeout /t 5 /nobreak >nul
start http://localhost:8000
