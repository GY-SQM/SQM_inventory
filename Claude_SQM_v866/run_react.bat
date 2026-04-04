@echo off
chcp 65001 >nul
title SQM React - One Click Start

echo ============================================
echo   SQM React - API + Frontend Start
echo ============================================
echo.

cd /d "%~dp0"

echo [1/2] API Server starting (port 8000)...
start "SQM API Server" cmd /c "cd /d "%~dp0" && python -m uvicorn react_api.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] React Frontend starting (port 5173)...
start "SQM React Frontend" cmd /c "cd /d "%~dp0web" && npx vite --host 127.0.0.1 --port 5173"

timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo   Ready!
echo   Browser: http://127.0.0.1:5173
echo ============================================
echo.

start http://127.0.0.1:5173

echo Press any key to STOP both servers...
pause >nul

echo Stopping servers...
taskkill /fi "WINDOWTITLE eq SQM API Server" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq SQM React Frontend" /f >nul 2>&1
echo Done.
