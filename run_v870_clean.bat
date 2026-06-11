@echo off
chcp 65001 > nul
cd /d "%~dp0"
title SQM Inventory v8.7.2

echo.
echo ====================================================
echo  SQM Inventory v8.7.2
echo  루트 : %CD%
echo  실행 : r1.bat (or r1.vbs) 을 사용하세요.
echo ====================================================
echo.

wscript //nologo "%~dp0r1.vbs"

endlocal
