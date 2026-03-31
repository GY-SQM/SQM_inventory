@echo off
chcp 65001 >nul
echo ============================================================
echo   SQM v8.5.5 (P1) — 사문 파일 삭제 스크립트
echo   생성: 2026-03-25
echo   총 삭제: ~40개 파일/폴더 (~13,800줄 제거)
echo ============================================================
echo.
echo ★ 이 스크립트는 SQM 루트 폴더에서 실행하세요.
echo ★ 삭제 전 현재 폴더를 확인합니다.
echo.

:: 안전 확인: run.py가 있는 폴더인지 체크
if not exist "run.py" (
    echo ❌ 오류: run.py가 없습니다. SQM 루트 폴더에서 실행하세요!
    pause
    exit /b 1
)
if not exist "version.py" (
    echo ❌ 오류: version.py가 없습니다. SQM 루트 폴더에서 실행하세요!
    pause
    exit /b 1
)

echo ✅ SQM 루트 폴더 확인 완료.
echo.
echo 삭제를 시작하려면 아무 키나 누르세요. 취소하려면 Ctrl+C
pause >nul

echo.
echo ── [1/7] 루트 잔류 파일 삭제 ──────────────────────────────
if exist "auto_tooltip.py"                      del "auto_tooltip.py"                      && echo   ✅ auto_tooltip.py
if exist "ui_constants.py"                      del "ui_constants.py"                      && echo   ✅ ui_constants.py
if exist "onestop_inbound.py"                   del "onestop_inbound.py"                   && echo   ✅ onestop_inbound.py
if exist "onestop_inbound_candidate_patch.py"   del "onestop_inbound_candidate_patch.py"   && echo   ✅ onestop_inbound_candidate_patch.py
if exist "sqm_audit_report.txt"                 del "sqm_audit_report.txt"                 && echo   ✅ sqm_audit_report.txt
if exist "PATCH_README.txt"                     del "PATCH_README.txt"                     && echo   ✅ PATCH_README.txt

echo.
echo ── [2/7] core/ 사문 파일 삭제 ─────────────────────────────
if exist "core\barcode_label_generator.py"      del "core\barcode_label_generator.py"      && echo   ✅ core\barcode_label_generator.py

echo.
echo ── [3/7] parsers/ 사문 파일 삭제 ──────────────────────────
if exist "parsers\msc_do_parser.py"             del "parsers\msc_do_parser.py"             && echo   ✅ parsers\msc_do_parser.py
if exist "parsers\maersk_do_parser.py"          del "parsers\maersk_do_parser.py"          && echo   ✅ parsers\maersk_do_parser.py
if exist "parsers\do_dispatcher.py"             del "parsers\do_dispatcher.py"             && echo   ✅ parsers\do_dispatcher.py
if exist "parsers\document_parser_modular\PATCH_README.txt" del "parsers\document_parser_modular\PATCH_README.txt" && echo   ✅ parsers\document_parser_modular\PATCH_README.txt

echo.
echo ── [4/7] engine_modules/ 사문 파일 삭제 ───────────────────
if exist "engine_modules\integrity_engine.py"   del "engine_modules\integrity_engine.py"   && echo   ✅ engine_modules\integrity_engine.py

echo.
echo ── [5/7] features/pdf_parser/ 사문 파일 삭제 ──────────────
if exist "features\pdf_parser\pdf_field_extractor.py" del "features\pdf_parser\pdf_field_extractor.py" && echo   ✅ features\pdf_parser\pdf_field_extractor.py

echo.
echo ── [6/7] dialogs/ 사문 파일 삭제 ──────────────────────────
if exist "gui_app_modular\dialogs\Claude_allocation_stress_test_v712.py" del "gui_app_modular\dialogs\Claude_allocation_stress_test_v712.py" && echo   ✅ Claude_allocation_stress_test_v712.py

echo.
echo ── [7/7] 폴더 전체 삭제 ──────────────────────────────────
if exist "sqm_parsing_runtime" (
    rmdir /s /q "sqm_parsing_runtime"           && echo   ✅ sqm_parsing_runtime\ (전체)
)
if exist "files" (
    rmdir /s /q "files"                         && echo   ✅ files\ (전체)
)

echo.
echo ── [부록] 비코드 파일 삭제 (스크린샷/로그) ────────────────
if exist "debug-934e53.log"                     del "debug-934e53.log"                     && echo   ✅ debug-934e53.log
if exist "logs\sqm_inventory.log"               del "logs\sqm_inventory.log"               && echo   ✅ logs\sqm_inventory.log
for %%f in (Snipaste_*.png) do (
    del "%%f" && echo   ✅ %%f
)
:: 한글 파일명 스크린샷
for %%f in (*스크린샷*.png) do (
    del "%%f" && echo   ✅ %%f
)

echo.
echo ============================================================
echo   P1 삭제 완료!
echo   다음 단계: version.py를 패치 파일로 덮어쓰기
echo   그 후: python -m pytest 실행하여 테스트 확인
echo ============================================================
pause
