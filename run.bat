@echo off
:: [RUBI System Bootloader v2.9.67]
title SQM Inventory Manager v2.9.91
color 0A
cls

echo ======================================================
echo    SQM Integrated Management System Starting...
echo    (Engine: v2.9.67 / Commander: main.py)
echo ======================================================
echo.

:: 1. Set working directory
cd /d "%~dp0"

:: 2. Check Python environment
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit
)

:: 3. Launch Main Engine
echo [INFO] Loading System Engine (core)...
python main.py

:: 4. Error Handling
if %errorlevel% neq 0 (
    echo.
    echo ------------------------------------------------------
    echo [CRITICAL ERROR] Program terminated unexpectedly.
    echo Please check the latest log in 'logs' folder.
    echo ------------------------------------------------------
    pause
)

exit