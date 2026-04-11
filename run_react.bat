@echo off
chcp 65001 >nul
title SQM React - One Click Start

echo ============================================
echo   SQM React - API + Web UI Start
echo ============================================
echo.

cd /d "%~dp0"

:: 필수 파일 확인
if not exist "react_api\main.py" ( echo [FAIL] react_api\main.py not found & pause & exit /b 1 )
if not exist "web\dist\index.html" ( echo [FAIL] web\dist\index.html not found & pause & exit /b 1 )
echo [OK] All files verified
echo.

:: .env 로드 (존재하면)
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "line=%%a"
        if not "!line:~0,1!"=="#" (
            set "%%a=%%b" 2>nul
        )
    )
)

echo [1/1] FastAPI Server starting (serves API + React UI)...
echo   - FastAPI가 web/dist/ 를 직접 서빙합니다 (Vite 불필요)
echo.

:: FastAPI 서버 시작 (백그라운드)
start "SQM-Server" cmd /k "cd /d "%~dp0" && set PYTHONPATH=%~dp0 && python run_react_api.py"

:: 서버 준비 대기
echo   서버 시작 대기 중...
timeout /t 4 /nobreak >nul

:: 브라우저 열기
start http://localhost:8000

echo.
echo ============================================
echo   [READY] SQM React UI
echo   Browser: http://localhost:8000
echo ============================================
echo.
echo 종료하려면 아무 키나 누르세요...
pause >nul

:: 서버 종료
taskkill /fi "WINDOWTITLE eq SQM-Server*" /f >nul 2>&1
echo Done.
