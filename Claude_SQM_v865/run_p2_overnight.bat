@echo off
echo Starting...
powershell -NoExit -ExecutionPolicy Bypass -File "F:\프로그램\Sqm 재고관리\Claude_SQM_v865\run_p2_overnight.ps1"
if errorlevel 1 (
    echo ERROR: PowerShell failed
    pause
)
pause
