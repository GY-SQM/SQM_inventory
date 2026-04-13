@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo [SQM FINAL PATCH SEQUENCE]
echo ==========================================

echo Step 0: Patch A Quick Check
type PATCH_A_QUICK_CHECK.md

echo.
echo ==========================================
echo IMPORTANT:
echo 1. Patch A quick check first
echo 2. Then Patch B (B01~B08)
echo 3. Then Patch C (C01~C06)
echo NEVER run A/B/C simultaneously
echo ==========================================
pause
