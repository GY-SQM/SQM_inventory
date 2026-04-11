@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo [SQM AGENT TEAM] MASTER AUTO RUN
echo ==========================================

if not exist logs mkdir logs
if not exist agent_team\results mkdir agent_team\results
if not exist agent_team\verify mkdir agent_team\verify
if not exist agent_team\debug mkdir agent_team\debug

echo [1/4] Environment check
where claude >nul 2>nul
if errorlevel 1 goto :claudefail

python --version
if errorlevel 1 goto :pythonfail

echo [2/4] Start Step Example
powershell -ExecutionPolicy Bypass -File scripts\run_step.ps1 -StepId B01 -TaskFile agent_team\tasks\B01.md
if errorlevel 1 goto :stepfail

echo [3/4] Optional Telegram notify
if exist scripts\telegram_notify_template.py (
    python scripts\telegram_notify_template.py
)

echo [4/4] DONE
echo SQM AGENT TEAM RUN COMPLETE
goto :end

:claudefail
echo [FAIL] Claude Code not found
exit /b 2

:pythonfail
echo [FAIL] Python not found
exit /b 3

:stepfail
echo [FAIL] Step execution failed
exit /b 4

:end
endlocal
pause
