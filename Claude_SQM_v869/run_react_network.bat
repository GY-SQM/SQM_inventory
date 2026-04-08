@echo off
chcp 65001 >nul
title SQM v869

echo ============================================
echo   SQM v869 - Backend + Frontend Start
echo ============================================
echo.

cd /d "%~dp0"

set API_PORT=8000
set REACT_PORT=5173

if exist ".env" (
    for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
        if "%%a"=="API_PORT"   set API_PORT=%%b
        if "%%a"=="REACT_PORT" set REACT_PORT=%%b
    )
)

echo [PORT] API=%API_PORT%  React=%REACT_PORT%
echo.
echo [CLEAN] Killing existing processes on ports...

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%API_PORT% "') do (
    echo [CLEAN] Port %API_PORT% PID=%%a
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%REACT_PORT% "') do (
    echo [CLEAN] Port %REACT_PORT% PID=%%a
    taskkill /PID %%a /F >nul 2>&1
)
taskkill /fi "WINDOWTITLE eq SQM API Server"    /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq SQM React Frontend" /f >nul 2>&1

echo [CLEAN] OK - waiting 2 sec...
timeout /t 2 /nobreak >nul

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127\|169"') do (
    set PC_IP=%%a
    goto :found_ip
)
:found_ip
set PC_IP=%PC_IP: =%

netsh advfirewall firewall add rule name="SQM React %REACT_PORT%" dir=in action=allow protocol=TCP localport=%REACT_PORT% >nul 2>&1
netsh advfirewall firewall add rule name="SQM API %API_PORT%"     dir=in action=allow protocol=TCP localport=%API_PORT%   >nul 2>&1
echo [OK] Port %API_PORT%, %REACT_PORT% opened

echo.
echo [1/2] Backend starting on port %API_PORT%...
start "SQM API Server" cmd /k "cd /d "%~dp0" && python -m react_api.main"
timeout /t 4 /nobreak >nul

echo [2/2] Frontend starting on port %REACT_PORT%...
start "SQM React Frontend" cmd /k "cd /d "%~dp0web" && npx vite --host 0.0.0.0 --port %REACT_PORT%"
timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo   [READY]
echo   PC:     http://localhost:%REACT_PORT%
echo   Phone:  http://%PC_IP%:%REACT_PORT%
echo ============================================
echo.
start http://localhost:%REACT_PORT%

echo Press any key to STOP...
pause >nul

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%API_PORT% "') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%REACT_PORT% "') do taskkill /PID %%a /F >nul 2>&1
taskkill /fi "WINDOWTITLE eq SQM API Server"    /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq SQM React Frontend" /f >nul 2>&1
netsh advfirewall firewall delete rule name="SQM React %REACT_PORT%" >nul 2>&1
netsh advfirewall firewall delete rule name="SQM API %API_PORT%"     >nul 2>&1
echo Done.
pause >nul
