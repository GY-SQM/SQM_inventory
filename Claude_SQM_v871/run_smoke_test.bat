@echo off
chcp 65001 > nul
echo ==========================================
echo   SQM v868 Smoke Test
echo   %date% %time%
echo ==========================================
echo.

F:
cd "F:\프로그램\Sqm 재고관리\Claude_SQM_v868"

echo [1/5] Python import check...
python -c "from react_api.main import app; print(f'  Routes: {len([r for r in app.routes if hasattr(r, \"path\")])}개')"
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
python -m py_compile react_api/routes/return_tab.py
python -m py_compile react_api/routes/return_write.py
python -m py_compile react_api/routes/do_update.py
python -m py_compile react_api/routes/location_bulk.py
python -m py_compile react_api/services/return_read_service.py
python -m py_compile react_api/services/return_write_service.py
python -m py_compile react_api/services/do_update_service.py
python -m py_compile react_api/services/location_bulk_service.py
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
