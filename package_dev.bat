@echo off
setlocal
cd /d "%~dp0"

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell not found.
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "scripts\package_tracks.ps1" -Track dev
if errorlevel 1 (
    echo [ERROR] Dev package failed.
    exit /b 1
)

echo [OK] Dev package completed.
endlocal
