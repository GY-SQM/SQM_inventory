@echo off
set "APP_DIR=%~dp0"
set "PYW=C:\Users\남기동\AppData\Local\Programs\Python\Python313\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw.exe"
cd /d "%APP_DIR%"
start "" "%PYW%" "%APP_DIR%main_webview.py"
exit /b 0
