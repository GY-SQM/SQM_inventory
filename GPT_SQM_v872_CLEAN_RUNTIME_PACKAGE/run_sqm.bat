@echo off
chcp 949 > nul

set PROJECT=F:\프로그램\Sqm 재고관리\Claude_SQM_v868
set PYTHON=python
set API_PORT=8000
set WEB_PORT=5173
set API_URL=http://localhost:%API_PORT%
set WEB_URL=http://localhost:%WEB_PORT%

cd /d "%PROJECT%"
echo.
echo [SQM v868] 시작 중...
echo.

:: 사전 점검
if not exist ".env" ( echo [FAIL] .env 없음 & exit /b 1 )
echo [OK] .env
if not exist "data\db\sqm_inventory.db" ( echo [FAIL] DB 없음 & exit /b 1 )
echo [OK] DB
if not exist "react_api\main.py" ( echo [FAIL] react_api\main.py 없음 & exit /b 1 )
echo [OK] react_api
if not exist "web\package.json" ( echo [FAIL] web\package.json 없음 & exit /b 1 )
echo [OK] web
echo.
echo [ALL CHECKS PASSED]
echo.

:: 기존 포트 정리
for %%P in (%API_PORT% %WEB_PORT%) do (
    netstat -ano | findstr ":%%P " | findstr "LISTENING" > nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
            taskkill /F /PID %%a > nul 2>&1
        )
    )
)
timeout /t 1 > nul

:: uvicorn 확인
%PYTHON% -m uvicorn --version > nul 2>&1
if errorlevel 1 ( %PYTHON% -m pip install uvicorn --quiet )

:: [STEP 1] FastAPI 백엔드 서버 (포트 8000)
echo [STEP 1] FastAPI 백엔드 시작 (포트 %API_PORT%)...
start "SQM-Backend" cmd /k "cd /d "%PROJECT%" && set PYTHONPATH=%PROJECT% && %PYTHON% -m uvicorn react_api.main:app --host 127.0.0.1 --port %API_PORT% --reload"
timeout /t 4 > nul

:: [STEP 2] React 프론트엔드 개발 서버 (포트 5173)
echo [STEP 2] React 프론트 시작 (포트 %WEB_PORT%)...
start "SQM-Frontend" cmd /k "cd /d "%PROJECT%\web" && npm run dev"
timeout /t 5 > nul

:: [STEP 3] 브라우저 열기
echo [STEP 3] 브라우저 열기...
start "" "%WEB_URL%"

:: Telegram 알림
if exist "scripts\telegram_notify.py" (
    %PYTHON% scripts\telegram_notify.py "SQM v868 시작! http://localhost:%WEB_PORT%"
)

echo.
echo ============================================
echo   SQM v868 실행 완료!
echo   Frontend: %WEB_URL%
echo   Backend:  %API_URL%
echo   API Docs: %API_URL%/docs
echo ============================================
echo.
echo 종료: 각 서버 창에서 Ctrl+C
echo.
