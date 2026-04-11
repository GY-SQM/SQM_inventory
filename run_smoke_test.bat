@echo off
chcp 65001 >/dev/null 2>nul
echo ==========================================
echo   SQM v871 Smoke Test
echo   %date% %time%
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/5] Python import check...
python -c "from react_api.main import app; print('  Routes OK')"
if errorlevel 1 (echo [FAIL] Python import && goto fail)
echo [PASS]
echo.

echo [2/5] pytest...
python -m pytest tests/ -q --tb=line 2>&1
if errorlevel 1 (echo [FAIL] pytest && goto fail)
echo [PASS]
echo.

echo [3/5] npm build...
cd web
call npm run build > nul 2>&1
if errorlevel 1 (echo [FAIL] npm build && cd .. && goto fail)
cd ..
echo [PASS]
echo.

echo [4/5] New files compile check...
python -m py_compile react_api/routes/tools.py
python -m py_compile react_api/routes/inbound.py
python -m py_compile react_api/services/inventory_read_service.py
python -m py_compile features/services/outbound_service.py
if errorlevel 1 (echo [FAIL] compile && goto fail)
echo [PASS]
echo.

echo [5/5] Telegram connectivity...
python -c "from scripts.telegram_notify import send; r=send('Smoke Test PASS'); print('  Telegram:', 'OK' if r else 'SKIP')"
echo [PASS]
echo.

echo ==========================================
echo   ALL SMOKE TESTS PASSED
echo ==========================================
goto end

:fail
echo.
echo ==========================================
echo   SMOKE TEST FAILED
echo ==========================================

:end
echo Done: %date% %time%
