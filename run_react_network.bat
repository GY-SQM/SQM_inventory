@echo off
chcp 65001 >nul
title SQM v871

cd /d "%~dp0"

set PYTHON=python
set API_PORT=8000

echo ============================================
echo   SQM v871 - Check
echo ============================================

if not exist ".env" ( echo [FAIL] .env not found & exit /b 1 )
echo [OK] .env
if not exist "data\db\sqm_inventory.db" ( echo [FAIL] DB not found & exit /b 1 )
echo [OK] DB
if not exist "react_api\main.py" ( echo [FAIL] react_api\main.py not found & exit /b 1 )
echo [OK] react_api
if not exist "web\dist\index.html" ( echo [FAIL] web\dist\index.html not found & exit /b 1 )
echo [OK] web dist
echo.

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%API_PORT% "') do taskkill /PID %%a /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo [1/1] Backend + Web UI starting (port %API_PORT%)...
echo   - FastAPI가 web/dist/ 를 직접 서빙합니다 (Vite 불필요)
start "SQM-Backend" cmd /k "cd /d "%~dp0" && set PYTHONPATH=%~dp0 && %PYTHON% run_react_api.py"
timeout /t 4 /nobreak >nul

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127\|169"') do (
    set PC_IP=%%a
    goto :found
)
:found
set PC_IP=%PC_IP: =%

start http://localhost:%API_PORT%

echo.
echo ============================================
echo   [READY]
echo   PC:    http://localhost:%API_PORT%
echo   Phone: http://%PC_IP%:%API_PORT%
echo ============================================
echo.
echo Press any key to STOP...
pause >nul

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%API_PORT% "') do taskkill /PID %%a /F >nul 2>&1
echo Done.
pause >nul
