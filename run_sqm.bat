@echo off
chcp 65001 >nul
title SQM v871 - 재고관리 시스템

cd /d "%~dp0"

echo ============================================
echo   SQM v871 재고관리 시스템
echo ============================================
echo.

:: ── 필수 파일 점검 ──────────────────────────────────
echo [점검] 필수 파일 확인 중...
set FAIL=0

if not exist ".env" (
    echo   [FAIL] .env 파일 없음
    set FAIL=1
) else ( echo   [OK] .env )

if not exist "data\db\sqm_inventory.db" (
    echo   [FAIL] DB 파일 없음 (data\db\sqm_inventory.db)
    set FAIL=1
) else ( echo   [OK] DB )

if not exist "react_api\main.py" (
    echo   [FAIL] react_api\main.py 없음
    set FAIL=1
) else ( echo   [OK] react_api )

if not exist "web\dist\index.html" (
    echo   [FAIL] web\dist\index.html 없음 (React UI 빌드 필요)
    set FAIL=1
) else ( echo   [OK] web dist )

if %FAIL%==1 (
    echo.
    echo   [ERROR] 필수 파일이 누락되었습니다.
    echo   관리자에게 문의하세요.
    pause
    exit /b 1
)

echo   [ALL OK] 점검 통과
echo.

:: ── Python 확인 ──────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python이 설치되지 않았습니다.
    echo   Python 3.9 이상을 설치하세요.
    pause
    exit /b 1
)

:: ── 실행 방식 선택 ───────────────────────────────────
echo [실행] SQM 시작 중...
echo.

:: pywebview가 있으면 데스크톱 모드, 없으면 브라우저 모드
python -c "import webview" >nul 2>&1
if errorlevel 1 (
    goto :BROWSER_MODE
) else (
    goto :DESKTOP_MODE
)

:DESKTOP_MODE
echo   모드: 데스크톱 (pywebview)
echo.
python "%~dp0run_desktop.py"
goto :END

:BROWSER_MODE
echo   모드: 브라우저 (pywebview 미설치)
echo   - FastAPI가 API + React UI 를 함께 서빙합니다
echo.

:: 기존 포트 정리
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
timeout /t 1 /nobreak >nul

:: FastAPI 서버 시작
start "SQM-Server" cmd /k "cd /d "%~dp0" && set PYTHONPATH=%~dp0 && python run_react_api.py"
timeout /t 5 /nobreak >nul

:: 브라우저 열기
start http://localhost:8000

:: IP 주소 표시
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127\|169"') do (
    set PC_IP=%%a
    goto :SHOW_INFO
)
:SHOW_INFO
set PC_IP=%PC_IP: =%

echo.
echo ============================================
echo   [READY] SQM v871 실행 중
echo.
echo   이 PC:  http://localhost:8000
echo   LAN:    http://%PC_IP%:8000
echo   API:    http://localhost:8000/docs
echo ============================================
echo.
echo   종료하려면 아무 키나 누르세요...
pause >nul

:: 서버 종료
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
echo 종료 완료.

:END
