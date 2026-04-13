@echo off
REM run_claude.bat — Claude Code 자동 실행

REM 절전 방지
powercfg -change -standby-timeout-ac 0
powercfg -change -monitor-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0

REM Claude Code 실행
cd /d "F:\프로그램\Sqm 재고관리\Claude_SQM_v862_FULL"
claude --dangerously-skip-permissions ^
  --system-prompt-file Claude_Code_SQM_MASTER.md

REM 작업 완료 후 절전 복구 (기본 30분)
powercfg -change -standby-timeout-ac 30
powercfg -change -monitor-timeout-ac 10

echo.
echo === 작업 완료 ===
echo Enter 누르면 창이 닫힙니다.
pause
