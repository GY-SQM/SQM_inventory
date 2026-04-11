@echo off
chcp 65001 >nul
echo.
echo ================================================
echo  SQM v8.7.1 완전 자동 배치 스크립트
echo  생성일: 2026-04-08
echo  - 파일 배치 + pm2 등록 + React 빌드 전부 자동
echo ================================================
echo.

:: ── 경로 설정 (%~dp0으로 자동 감지, 다르면 PROJECT만 수정) ──
set DEPLOY=%~dp0
set PROJECT=%~dp0.

:: ── 프로젝트 존재 확인 ───────────────────────────────────────
if not exist "%PROJECT%" (
    echo [오류] 프로젝트 폴더 없음:
    echo   %PROJECT%
    echo deploy.bat 상단 PROJECT 변수를 수정하세요.
    pause & exit /b 1
)

:: ============================================================
:: STEP 1. 기존 파일 백업
:: ============================================================
echo [STEP 1/6] 기존 파일 백업 중...
set BACKUP=%PROJECT%\backup\p2bc_%date:~0,4%%date:~5,2%%date:~8,2%
mkdir "%BACKUP%" 2>nul
for %%f in (
    "features\repositories\inbound_repository.py"
    "features\repositories\outbound_repository.py"
    "react_api\main.py"
    "react_api\routes\outbound_write.py"
    "web\src\App.jsx"
    "web\vite.config.js"
    "engine_modules\query_cache.py"
) do (
    if exist "%PROJECT%\%%~f" (
        copy /y "%PROJECT%\%%~f" "%BACKUP%\" >nul
        echo   백업: %%~f
    )
)
echo   완료 → %BACKUP%
echo.

:: ============================================================
:: STEP 2. 디렉토리 생성
:: ============================================================
echo [STEP 2/6] 디렉토리 생성 중...
for %%d in (
    "features\repositories"
    "features\services"
    "tests"
    "docs"
    "react_api\utils"
    "react_api\routes"
    "web\src\pages"
    "web\src\components"
) do mkdir "%PROJECT%\%%~d" 2>nul

if not exist "%PROJECT%\features\repositories\__init__.py" type nul > "%PROJECT%\features\repositories\__init__.py"
if not exist "%PROJECT%\features\services\__init__.py"     type nul > "%PROJECT%\features\services\__init__.py"
echo   완료
echo.

:: ============================================================
:: STEP 3. Python 파일 배치 (20개)
:: ============================================================
echo [STEP 3/6] Python 파일 배치 중...

copy /y "%DEPLOY%features\repositories\base_repository.py"      "%PROJECT%\features\repositories\base_repository.py"      >nul && echo   [OK] base_repository.py
copy /y "%DEPLOY%features\repositories\inbound_repository.py"   "%PROJECT%\features\repositories\inbound_repository.py"   >nul && echo   [OK] inbound_repository.py
copy /y "%DEPLOY%features\repositories\outbound_query.py"       "%PROJECT%\features\repositories\outbound_query.py"       >nul && echo   [OK] outbound_query.py
copy /y "%DEPLOY%features\repositories\outbound_repository.py"  "%PROJECT%\features\repositories\outbound_repository.py"  >nul && echo   [OK] outbound_repository.py
copy /y "%DEPLOY%features\repositories\inventory_repository.py" "%PROJECT%\features\repositories\inventory_repository.py" >nul && echo   [OK] inventory_repository.py
copy /y "%DEPLOY%features\services\outbound_state_rules.py"     "%PROJECT%\features\services\outbound_state_rules.py"     >nul && echo   [OK] outbound_state_rules.py
copy /y "%DEPLOY%features\services\outbound_service.py"         "%PROJECT%\features\services\outbound_service.py"         >nul && echo   [OK] outbound_service.py
copy /y "%DEPLOY%react_api\main.py"                             "%PROJECT%\react_api\main.py"                             >nul && echo   [OK] react_api\main.py  (에러알림+시작/종료)
copy /y "%DEPLOY%react_api\utils\telegram_alert.py"             "%PROJECT%\react_api\utils\telegram_alert.py"             >nul && echo   [OK] telegram_alert.py
copy /y "%DEPLOY%react_api\routes\outbound_write.py"            "%PROJECT%\react_api\routes\outbound_write.py"            >nul && echo   [OK] outbound_write.py  (/confirm 엔드포인트 포함)
copy /y "%DEPLOY%engine_modules\db_optimize.py"                 "%PROJECT%\engine_modules\db_optimize.py"                 >nul && echo   [OK] db_optimize.py
copy /y "%DEPLOY%engine_modules\query_cache.py"                 "%PROJECT%\engine_modules\query_cache.py"                 >nul && echo   [OK] query_cache.py  (TTL 지능화)
copy /y "%DEPLOY%scripts\backup_scheduler.py"                   "%PROJECT%\scripts\backup_scheduler.py"                   >nul && echo   [OK] backup_scheduler.py
copy /y "%DEPLOY%scripts\sqm_bot.py"                            "%PROJECT%\scripts\sqm_bot.py"                            >nul && echo   [OK] sqm_bot.py  (봇 v2)
copy /y "%DEPLOY%tests\test_p2b_outbound_refactor.py"           "%PROJECT%\tests\test_p2b_outbound_refactor.py"           >nul && echo   [OK] test_p2b_outbound_refactor.py

:: 문서
copy /y "%DEPLOY%docs\OPERATION_CHECKLIST.md"     "%PROJECT%\docs\OPERATION_CHECKLIST.md"     >nul
copy /y "%DEPLOY%docs\TELEGRAM_BOT_TEST.md"       "%PROJECT%\docs\TELEGRAM_BOT_TEST.md"       >nul
copy /y "%DEPLOY%docs\GWANGYANG_SCAN_SCENARIO.md" "%PROJECT%\docs\GWANGYANG_SCAN_SCENARIO.md" >nul
copy /y "%DEPLOY%docs\P2B_REFACTOR_REPORT.md"     "%PROJECT%\docs\P2B_REFACTOR_REPORT.md"     >nul
copy /y "%DEPLOY%docs\P2C_POLICY.md"              "%PROJECT%\docs\P2C_POLICY.md"              >nul
echo   문서 5개 완료
echo.

:: ============================================================
:: STEP 4. React 파일 배치 (4개)
:: ============================================================
echo [STEP 4/6] React 파일 배치 중...
copy /y "%DEPLOY%web\src\App.jsx"                        "%PROJECT%\web\src\App.jsx"                        >nul && echo   [OK] App.jsx  (/mobile 라우트 포함)
copy /y "%DEPLOY%web\src\pages\MobileDashboard.jsx"      "%PROJECT%\web\src\pages\MobileDashboard.jsx"      >nul && echo   [OK] MobileDashboard.jsx  (신규)
copy /y "%DEPLOY%web\src\components\BarcodeScanner.jsx"  "%PROJECT%\web\src\components\BarcodeScanner.jsx"  >nul && echo   [OK] BarcodeScanner.jsx  (신규)
copy /y "%DEPLOY%web\vite.config.js"                     "%PROJECT%\web\vite.config.js"                     >nul && echo   [OK] vite.config.js  (LAN접속+PWA준비)
echo.

:: ============================================================
:: STEP 5. Import 확인 + pytest
:: ============================================================
echo [STEP 5/6] 검증 중...
cd /d "%PROJECT%"

python -c "from features.repositories.base_repository import BaseRepository; print('  [OK] BaseRepository')" 2>nul || echo   [WARN] BaseRepository import 실패
python -c "from features.services.outbound_service import OutboundService; print('  [OK] OutboundService')" 2>nul || echo   [WARN] OutboundService import 실패
python -c "from features.repositories.inventory_repository import InventoryRepository; print('  [OK] InventoryRepository')" 2>nul || echo   [WARN] InventoryRepository import 실패

echo.
echo   pytest 실행 중 (27개 TC)...
pytest tests\test_p2b_outbound_refactor.py -q --tb=short 2>&1
if errorlevel 1 (
    echo.
    echo   [WARN] 일부 테스트 실패 — docs\OPERATION_CHECKLIST.md 확인
) else (
    echo   [OK] pytest 전체 통과
)
echo.

:: ============================================================
:: STEP 6. pm2 서비스 등록 + React 빌드
:: ============================================================
echo [STEP 6/6] 서비스 등록 + React 빌드 중...

:: pm2 존재 확인
where pm2 >nul 2>&1
if errorlevel 1 (
    echo   [SKIP] pm2 없음 — npm install -g pm2 후 수동 등록
    echo     pm2 start scripts\backup_scheduler.py --interpreter python --name sqm-backup
    echo     pm2 start scripts\sqm_bot.py --interpreter python --name sqm-bot
) else (
    :: sqm-backup 등록/재시작
    pm2 describe sqm-backup >nul 2>&1
    if errorlevel 1 (
        pm2 start "%PROJECT%\scripts\backup_scheduler.py" --interpreter python --name sqm-backup --cwd "%PROJECT%" >nul
        echo   [OK] sqm-backup 신규 등록
    ) else (
        pm2 restart sqm-backup >nul
        echo   [OK] sqm-backup 재시작
    )

    :: sqm-bot 등록/재시작
    pm2 describe sqm-bot >nul 2>&1
    if errorlevel 1 (
        pm2 start "%PROJECT%\scripts\sqm_bot.py" --interpreter python --name sqm-bot --cwd "%PROJECT%" >nul
        echo   [OK] sqm-bot 신규 등록
    ) else (
        pm2 restart sqm-bot >nul
        echo   [OK] sqm-bot 재시작 (봇 v2 적용)
    )

    :: sqm-api 재시작 (새 main.py 적용)
    pm2 describe sqm-api >nul 2>&1
    if not errorlevel 1 (
        pm2 restart sqm-api >nul
        echo   [OK] sqm-api 재시작 (에러알림 적용)
    )

    pm2 save >nul
    echo   [OK] pm2 설정 저장
)
echo.

:: React 빌드
echo   React 빌드 중 (npm run build)...
cd /d "%PROJECT%\web"
where npm >nul 2>&1
if errorlevel 1 (
    echo   [SKIP] npm 없음 — 수동으로 cd web ^&^& npm run dev 실행
) else (
    npm run build >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] npm build 실패 — npm run dev 로 개발 서버 실행 필요
    ) else (
        echo   [OK] React 빌드 완료
    )
)
echo.

:: ============================================================
:: 완료
:: ============================================================
echo ================================================
echo  [완료] 모든 작업 자동 완료!
echo.
echo  확인 사항:
echo  1. @Claude_kdnbot 에서 /상태 입력 → API+DB 정상 확인
echo  2. 스마트폰: http://[내PC-IP]:5173/mobile 접속
echo  3. pm2 list → sqm-api, sqm-backup, sqm-bot 모두 online
echo ================================================
echo.
pause

:: ── 추가 개선 파일 배치 ─────────────────────────────────────
copy /y "%DEPLOY%react_api\dashboard_read_service.py"                "%PROJECT%\react_api\dashboard_read_service.py"                >nul && echo   [OK] dashboard_read_service.py  (QueryCache 연결)
copy /y "%DEPLOY%react_api\services\inventory_read_service.py"       "%PROJECT%\react_api\services\inventory_read_service.py"       >nul && echo   [OK] inventory_read_service.py  (윈도우함수 적용)

:: ── ADMIN_TOKEN 보안 점검 ─────────────────────────────────────
echo.
echo [보안] ADMIN_TOKEN 점검 중...
python -c "
import os
token = ''
try:
    with open(r'%PROJECT%\.env', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('ADMIN_TOKEN='):
                token = line.strip().split('=',1)[1]; break
except Exception:
    pass
weak = ['sqm_admin_2026','admin','password','sqm','1234','test']
if not token or token.lower() in weak or len(token) < 12:
    print('  [WARNING] ADMIN_TOKEN 취약! .env 파일에서 변경하세요')
    print('  권장: ADMIN_TOKEN=SQM@Gwangyang#2026!Secure')
else:
    print(f'  [OK] ADMIN_TOKEN 설정됨 ({len(token)}자)')
" 2>nul || echo   [SKIP]

:: ── 추가 파일 배치 ───────────────────────────────────────────
copy /y "%DEPLOY%react_api\routes\dashboard.py" "%PROJECT%\react_api\routes\dashboard.py" >nul && echo   [OK] dashboard.py  (QueryCache 적용)

:: ── 1순위 React 페이지 배치 ─────────────────────────────────
echo.
echo [추가] React 1순위 페이지 배치...
copy /y "%DEPLOY%web\src\pages\InventoryPage.jsx"  "%PROJECT%\web\src\pages\InventoryPage.jsx"  >nul && echo   [OK] InventoryPage.jsx  (입고버튼 추가)
copy /y "%DEPLOY%web\src\pages\PickedPage.jsx"     "%PROJECT%\web\src\pages\PickedPage.jsx"     >nul && echo   [OK] PickedPage.jsx     (출고확정 버튼 추가)
copy /y "%DEPLOY%web\src\pages\AllocationPage.jsx" "%PROJECT%\web\src\pages\AllocationPage.jsx" >nul && echo   [OK] AllocationPage.jsx (예약실행/취소 버튼 추가)
copy /y "%DEPLOY%web\src\api\writeApi.js"          "%PROJECT%\web\src\api\writeApi.js"          >nul && echo   [OK] writeApi.js        (confirmOutbound 추가)

:: ── Q1/Q2/Q3 개선 파일 배치 ──────────────────────────────────
copy /y "%DEPLOY%react_api\schemas\dashboard.py"      "%PROJECT%\react_api\schemas\dashboard.py"      >nul && echo   [OK] schemas/dashboard.py  (con_return 필드 추가)
copy /y "%DEPLOY%react_api\dashboard_read_service.py" "%PROJECT%\react_api\dashboard_read_service.py" >nul && echo   [OK] dashboard_read_service.py (con_return 쿼리 추가)
copy /y "%DEPLOY%web\src\pages\DashboardPage.jsx"     "%PROJECT%\web\src\pages\DashboardPage.jsx"     >nul && echo   [OK] DashboardPage.jsx  (KPI카드+Con Return경고+30초갱신)

:: ── 단기 React 페이지 배치 ───────────────────────────────────
copy /y "%DEPLOY%web\src\pages\OutboundPage.jsx"       "%PROJECT%\web\src\pages\OutboundPage.jsx"       >nul && echo   [OK] OutboundPage.jsx       (출고실행버튼)
copy /y "%DEPLOY%web\src\pages\SoldPage.jsx"           "%PROJECT%\web\src\pages\SoldPage.jsx"           >nul && echo   [OK] SoldPage.jsx           (취소버튼+날짜필터)
copy /y "%DEPLOY%web\src\pages\TonbagPage.jsx"         "%PROJECT%\web\src\pages\TonbagPage.jsx"         >nul && echo   [OK] TonbagPage.jsx         (위치수정인라인)
copy /y "%DEPLOY%web\src\pages\CargoOverviewPage.jsx"  "%PROJECT%\web\src\pages\CargoOverviewPage.jsx"  >nul && echo   [OK] CargoOverviewPage.jsx  (다크테마+KPI)
copy /y "%DEPLOY%web\src\pages\OutboundHistoryPage.jsx""%PROJECT%\web\src\pages\OutboundHistoryPage.jsx">nul && echo   [OK] OutboundHistoryPage.jsx(날짜필터)
copy /y "%DEPLOY%web\src\pages\ProductMasterPage.jsx"  "%PROJECT%\web\src\pages\ProductMasterPage.jsx"  >nul && echo   [OK] ProductMasterPage.jsx  (CRUD완성)

:: ── PyInstaller 데스크탑 앱 빌드 파일 ────────────────────────
copy /y "%DEPLOY%build_exe.bat"    "%PROJECT%\build_exe.bat"    >nul && echo   [OK] build_exe.bat       (EXE 빌드 스크립트)
copy /y "%DEPLOY%sqm_desktop.spec" "%PROJECT%\sqm_desktop.spec" >nul && echo   [OK] sqm_desktop.spec    (PyInstaller 스펙)

:: ── Q1/Q2/Q3 추가 파일 ───────────────────────────────────────
copy /y "%DEPLOY%web\src\pages\IntegrityPage.jsx"      "%PROJECT%\web\src\pages\IntegrityPage.jsx"      >nul && echo   [OK] IntegrityPage.jsx  (자동실행+DB최적화버튼)
copy /y "%DEPLOY%web\src\pages\LogPage.jsx"            "%PROJECT%\web\src\pages\LogPage.jsx"            >nul && echo   [OK] LogPage.jsx        (레벨필터+날짜필터)
copy /y "%DEPLOY%web\src\pages\SummaryPage.jsx"        "%PROJECT%\web\src\pages\SummaryPage.jsx"        >nul && echo   [OK] SummaryPage.jsx    (Excel+30초갱신)
copy /y "%DEPLOY%web\src\pages\MovePage.jsx"           "%PROJECT%\web\src\pages\MovePage.jsx"           >nul && echo   [OK] MovePage.jsx       (이동실행+이력)
copy /y "%DEPLOY%web\src\pages\HelpPage.jsx"           "%PROJECT%\web\src\pages\HelpPage.jsx"           >nul && echo   [OK] HelpPage.jsx       (검색+모바일가이드)
copy /y "%DEPLOY%sqm_desktop.spec"                     "%PROJECT%\sqm_desktop.spec"                     >nul && echo   [OK] sqm_desktop.spec   (v2 run.py폴백+광양배포)
copy /y "%DEPLOY%build_exe.bat"                        "%PROJECT%\build_exe.bat"                        >nul && echo   [OK] build_exe.bat      (v2 광양패키지생성)

:: ── ①②③ 파일 배치 ──────────────────────────────────────────
copy /y "%DEPLOY%web\src\pages\TemplatesPage.jsx" "%PROJECT%\web\src\pages\TemplatesPage.jsx" >nul && echo   [OK] TemplatesPage.jsx  (다크배경 완성)
copy /y "%DEPLOY%run_desktop.py"       "%PROJECT%\run_desktop.py"         >nul && echo   [OK] run_desktop.py     (pywebview 데스크탑)
copy /y "%DEPLOY%sqm_web_desktop.spec" "%PROJECT%\sqm_web_desktop.spec"   >nul && echo   [OK] sqm_web_desktop.spec
copy /y "%DEPLOY%build_all.bat"        "%PROJECT%\build_all.bat"          >nul && echo   [OK] build_all.bat      (①②③ 전체 빌드)
if not exist "%PROJECT%\electron" mkdir "%PROJECT%\electron"
copy /y "%DEPLOY%electron\main.js"     "%PROJECT%\electron\main.js"       >nul && echo   [OK] electron\main.js
