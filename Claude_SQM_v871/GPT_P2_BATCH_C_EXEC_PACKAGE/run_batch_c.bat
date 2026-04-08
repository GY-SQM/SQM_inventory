@echo off
setlocal

echo ========================================
echo [BATCH C] Repository Migration Auto Run
echo ========================================

if not exist repositories\base_repository.py goto :missing
if not exist repositories\inventory_repository.py goto :missing
if not exist repositories\inbound_repository.py goto :missing
if not exist repositories\outbound_repository.py goto :missing
if not exist scripts\verify_batch_c.py goto :missing

echo [1/4] py_compile
python -m py_compile repositories/base_repository.py repositories/inventory_repository.py repositories/inbound_repository.py repositories/outbound_repository.py
if errorlevel 1 goto :fail

echo [2/4] pytest
python -m pytest tests/test_base_repository.py tests/test_inventory_repository.py -q
if errorlevel 1 goto :fail

echo [3/4] verify_batch_c
python scripts/verify_batch_c.py
if errorlevel 1 goto :fail

echo [4/4] DONE
echo BATCH C PASS
goto :end

:missing
echo REQUIRED FILE MISSING
exit /b 2

:fail
echo BATCH C FAIL
exit /b 1

:end
endlocal
pause
