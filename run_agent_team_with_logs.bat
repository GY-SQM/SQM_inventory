@echo off
chcp 65001 >nul
setlocal

if not exist logs mkdir logs

set STEP_ID=%1
if "%STEP_ID%"=="" set STEP_ID=B01

echo ==========================================
echo [SQM AGENT TEAM] RUN WITH LOGS
echo STEP: %STEP_ID%
echo ==========================================

powershell -ExecutionPolicy Bypass -File scripts\run_step.ps1 -StepId %STEP_ID% -TaskFile agent_team\tasks\%STEP_ID%.md

echo Finished.
pause
