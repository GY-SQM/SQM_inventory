# SQM v869 — v864 기능 완전 이관 자동실행 MASTER
# 작성일: 2026-04-05
# 목적: v864 데스크톱에 존재하던 사용자 가시 기능을 v869 React에 누락 없이 이관
# 총 단계: 12단계 (S1~S12)

================================================================
## 0. 절대 실행 규칙 ★★★ 반드시 읽고 시작할 것 ★★★
================================================================

### 자율 실행 규칙
- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기/삭제 자동 승인
- 테스트 실패 시 자동 수정 후 재시도
- ★ 중단 없이 끝까지 수행 — S1부터 S12까지
- ★ 한 단계 완료 즉시 다음 단계 시작 — 절대 멈추지 말 것
- ★ 사용자 응답 대기(input()) 절대 금지 — 컴퓨터 앞에 아무도 없음
- ★ 작업 완료 보고 후 즉시 다음 단계 진행
- ★ "다음으로 진행할까요?" 같은 확인 요청 절대 금지
- ★ AskUserQuestion 도구 사용 절대 금지

### Telegram 사용 규칙
✅ 허용:
  - 단계 완료 알림
  - 오류 발생 즉시 알림
❌ 금지:
  - 열린 질문, 방향 의견 요청

### 단계 완료 기록 규칙
각 단계 완료 시 반드시 두 줄 실행:
  python -c "open('logs/completed_steps.txt','a').write('단계ID_PASS\n')"
  python scripts/telegram_notify.py "완료 메시지"

### 강제 테스트 규칙
구현 → 테스트 → 실패시 수정 → 재테스트 → 통과 → 다음 단계

### 프로젝트 구조 이해
- 프로젝트 루트: F:\프로그램\Sqm 재고관리\Claude_SQM_v869
- 프론트엔드: web/src/ (React + Vite)
- 백엔드 API: react_api/ (FastAPI)
- DB: data/sqm.db (SQLite)
- 기존 핵심 파일 절대 삭제 금지
- react_api/routes/tools.py — export/도구 API
- web/src/components/MenuBar.jsx — 전체 메뉴 구조
- web/src/App.jsx — 라우터 + 사이드바 + 액션 핸들러

================================================================

## 1. 작업 단계 정의

================================================================
S1 — 사전 점검: 메뉴/라우트 맵 생성
================================================================
목적: v869 현재 상태를 정확히 파악하여 이후 패치의 기준 자료를 만든다
작업:
  - web/src/App.jsx 의 Route 목록 전체 추출
  - web/src/components/MenuBar.jsx 의 menuData 전체 action 목록 추출
  - App.jsx 의 handleMenuAction switch문에서 action→navigate 매핑 추출
  - SIDEBAR_TABS 의 항목 추출
  - 결과를 logs/S1_menu_route_map.md 에 정리
  - 누락/부분반영/완전반영 상태 판정표 작성
확인: logs/S1_menu_route_map.md 파일이 존재하고 내용이 비어있지 않음

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S1_PASS\n')"
  python scripts/telegram_notify.py "✅ [S1] 메뉴/라우트 맵 완료 → S2 시작"

================================================================
S2 — 총괄 재고 리스트 메뉴 노출 복구 (P0)
================================================================
목적: /cargo Route는 있으나 MenuBar/Sidebar에서 직접 진입할 수 없는 문제 해결
작업:
  - MenuBar.jsx 의 menuData에 총괄 재고 리스트 항목 추가
    위치: View 메뉴 또는 도구 메뉴 내 적절한 위치
    라벨: '📋  총괄 재고 리스트'
    action: 'navCargo'
  - App.jsx 의 handleMenuAction에 navCargo case가 이미 있는지 확인 (있으면 유지)
  - SIDEBAR_TABS에 cargo 항목 추가 (summary 근처)
    { key: 'cargo', icon: '📋', label: 'Cargo', path: '/cargo', color: '#60a5fa' }
  - CargoOverviewPage.jsx 가 빈 페이지가 아닌지 확인, 최소 데이터 조회 구현 확인
확인: 
  - MenuBar에서 총괄 재고 리스트 메뉴가 보이는지 코드 확인
  - Sidebar에서 Cargo 탭이 보이는지 코드 확인
  - /cargo Route 진입 시 페이지 렌더링 확인

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S2_PASS\n')"
  python scripts/telegram_notify.py "✅ [S2] 총괄 재고 리스트 메뉴 노출 완료 → S3 시작"

================================================================
S3 — LOT 리스트 Excel export 복구 (P0)
================================================================
목적: v864에 있던 LOT 리스트 전용 Excel export를 v869에 구현
작업:
  - react_api/routes/tools.py 에 LOT 리스트 전용 export 엔드포인트 추가
    GET /api/tools/export-lot-list
    응답: Excel(.xlsx) 또는 CSV 파일 다운로드
    필드: LOT_NO, BL_NO, SAP_NO, PRODUCT, STATUS, QTY, BAG_COUNT, SAMPLE_FLAG, INBOUND_DATE
    파일명: SQM_LOT_list_YYYYMMDD_HHMM.xlsx (또는 .csv)
  - openpyxl 사용 (이미 requirements.txt에 있으면 그대로, 없으면 csv로 대체)
  - web/src/pages/InventoryPage.jsx 에 "LOT 리스트 Excel" 내보내기 버튼 추가
    버튼 위치: 페이지 상단 또는 테이블 위 toolbar
    클릭 시: /api/tools/export-lot-list 호출 → 파일 다운로드
  - MenuBar.jsx 의 내보내기 서브메뉴에도 LOT 리스트 Excel 항목 추가
    action: 'exportLotList'
  - App.jsx handleMenuAction에 exportLotList case 추가
확인:
  - 코드에 /api/tools/export-lot-list 엔드포인트가 있는지 확인
  - InventoryPage에 export 버튼이 있는지 확인
  - MenuBar 내보내기 서브메뉴에 LOT 리스트 Excel이 있는지 확인

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S3_PASS\n')"
  python scripts/telegram_notify.py "✅ [S3] LOT 리스트 Excel export 완료 → S4 시작"

================================================================
S4 — 톤백리스트 Excel export 복구 (P0)
================================================================
목적: v864에 있던 톤백리스트 전용 Excel export를 v869에 구현
작업:
  - react_api/routes/tools.py 에 톤백리스트 전용 export 엔드포인트 추가
    GET /api/tools/export-tonbag-list
    필드: TONBAG_NO, LOT_NO, BL_NO, LOCATION, STATUS, WEIGHT, SAMPLE_FLAG, INBOUND_DATE, OUTBOUND_DATE
    파일명: SQM_tonbag_list_YYYYMMDD_HHMM.xlsx (또는 .csv)
  - web/src/pages/TonbagPage.jsx 에 "톤백리스트 Excel" 내보내기 버튼 추가
  - MenuBar.jsx 내보내기 서브메뉴에 톤백리스트 Excel 항목 추가
    action: 'exportTonbagList'
  - App.jsx handleMenuAction에 exportTonbagList case 추가
확인:
  - /api/tools/export-tonbag-list 엔드포인트 코드 존재
  - TonbagPage에 export 버튼 존재
  - MenuBar 내보내기 서브메뉴에 톤백리스트 Excel 존재

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S4_PASS\n')"
  python scripts/telegram_notify.py "✅ [S4] 톤백리스트 Excel export 완료 → S5 시작"

================================================================
S5 — 로그 내보내기 실구현 (P0)
================================================================
목적: MenuBar에 '로그 내보내기' 라벨만 있고 실제 동작이 없는 문제 해결
작업:
  - react_api/routes/tools.py 에 로그 export 엔드포인트 추가
    GET /api/tools/export-logs
    쿼리파라미터: log_type (audit/inventory/operation), format (csv/json)
    파일명: SQM_logs_YYYYMMDD_HHMM.csv
    UTF-8 BOM 포함 (Excel 한글 호환)
  - web/src/pages/LogPage.jsx 에 내보내기 버튼 추가
    버튼 클릭 시: 현재 필터 상태 반영하여 /api/tools/export-logs 호출
  - MenuBar.jsx 의 '💾 로그 내보내기' action을 'exportLogs'로 변경 (현재 'navLog')
  - App.jsx handleMenuAction에 exportLogs case 추가
확인:
  - /api/tools/export-logs 엔드포인트 코드 존재
  - LogPage에 내보내기 버튼 존재
  - MenuBar에서 로그 내보내기 클릭 시 export 동작 연결

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S5_PASS\n')"
  python scripts/telegram_notify.py "✅ [S5] 로그 내보내기 완료 → S6 시작"

================================================================
S6 — 최근 파일 기능 실구현 (P1)
================================================================
목적: '최근 파일' 메뉴가 placeholder 상태인 문제 해결
작업:
  - web/src/hooks/ 또는 web/src/utils/ 에 recentFiles 유틸 생성
    localStorage 기반으로 최근 작업 이력 저장
    저장 항목: { filename, type(입고/출고/보고서/스캔), timestamp, path }
    최대 10개 유지
  - 입고/출고/보고서/스캔 작업 성공 시 recentFiles에 기록 추가
    InboundModal, OutboundModal, ReportsPage, ScanPage 등에서 성공 콜백에 추가
  - MenuBar.jsx 의 '최근 파일' 서브메뉴를 동적으로 생성
    localStorage에서 읽어서 children 배열 동적 구성
    각 항목 클릭 시 해당 타입에 맞는 페이지로 이동
    비어있으면 '(최근 작업 없음)' 표시
확인:
  - localStorage에 recentFiles 키 저장 로직 존재
  - MenuBar에서 최근 파일 목록이 동적 구성되는지 코드 확인

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S6_PASS\n')"
  python scripts/telegram_notify.py "✅ [S6] 최근 파일 기능 완료 → S7 시작"

================================================================
S7 — 정합성 검사/복구 UX 보강 (P1)
================================================================
목적: IntegrityPage에서 검사만 있고 복구 동선이 약한 문제 해결
작업:
  - web/src/pages/IntegrityPage.jsx 수정
    검사 버튼과 복구 버튼을 분리
    복구 버튼 클릭 시 확인 모달 표시 (위험 작업 경고)
    "백업 먼저 하시겠습니까?" 안내 문구 포함
    복구 결과를 화면에 카드/표 형태로 표시
  - react_api/routes/tools.py 에 복구 전용 엔드포인트 확인/추가
    POST /api/tools/integrity-repair
    응답: { repaired_count, details }
  - 승인분 예약 반영: ApprovalPage에 예약 반영 버튼이 명확한지 확인
    없으면 추가 (POST /api/approval/apply-reserved)
확인:
  - IntegrityPage에 검사/복구 버튼이 분리되어 있는지
  - 복구 전 확인 모달이 있는지
  - 예약 반영 동선이 존재하는지

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S7_PASS\n')"
  python scripts/telegram_notify.py "✅ [S7] 정합성 검사/복구 UX 완료 → S8 시작"

================================================================
S8 — 한글 업무 라벨 보강 (P1)
================================================================
목적: v864 사용자가 v869 화면을 보고 즉시 기능을 찾을 수 있도록 한글 라벨 보강
작업:
  - App.jsx 의 SIDEBAR_TABS 라벨에 한글 보조명 추가 (괄호 형태)
    { key: 'inventory', label: '재고 조회', ... }
    { key: 'allocation', label: '판매 배정', ... }
    { key: 'picked', label: '화물 결정', ... }
    { key: 'outbound', label: '출고', ... }
    { key: 'return', label: '반품', ... }
    { key: 'move', label: '이동', ... }
    { key: 'dashboard', label: '대시보드', ... }
    { key: 'log', label: '로그', ... }
    { key: 'scan', label: '스캔', ... }
    { key: 'cargo', label: '총괄 재고', ... }
  - 아이콘은 기존 유지, label만 한글로 변경
  - MenuBar 상단 메뉴 라벨은 현재 상태 유지 (이미 한글 포함)
확인:
  - SIDEBAR_TABS 의 label이 한글 업무명으로 변경되었는지

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S8_PASS\n')"
  python scripts/telegram_notify.py "✅ [S8] 한글 라벨 보강 완료 → S9 시작"

================================================================
S9 — 테스트 DB 초기화 기능 (P1)
================================================================
목적: 개발/테스트용 관리자 전용 DB 초기화 기능 추가
작업:
  - web/src/pages/SettingsPage.jsx 에 "개발자 도구" 섹션 추가
    조건: devMode가 true일 때만 표시
    버튼: "테스트 DB 초기화" (빨간색 경고 스타일)
    클릭 시: 2단계 확인 모달
      1단계: "정말 모든 데이터를 삭제하시겠습니까?"
      2단계: "이 작업은 되돌릴 수 없습니다. 백업을 먼저 하세요."
  - react_api/routes/tools.py 에 엔드포인트 추가
    POST /api/tools/reset-test-db
    헤더: X-Confirm-Reset: "CONFIRM_RESET" 필수
    동작: 모든 테이블 데이터 삭제 (스키마 유지)
    응답: { success: true, message, tables_cleared }
    ★ production 환경 감지 시 실행 차단
확인:
  - devMode일 때만 버튼이 보이는지
  - 확인 모달이 2단계인지
  - API에 confirm 헤더 검증이 있는지

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S9_PASS\n')"
  python scripts/telegram_notify.py "✅ [S9] 테스트 DB 초기화 완료 → S10 시작"

================================================================
S10 — UI preference 저장/초기화 + 새로고침/종료 UX (P2)
================================================================
목적: v864의 창 크기 저장/초기화를 웹 레이아웃 저장으로 재해석
작업:
  - localStorage 기반 UI preference 저장 구현
    저장 항목: sidebar collapsed, theme(dark/light), fontScale, 마지막 탭
    앱 시작 시 localStorage에서 복원
  - SettingsPage 또는 Sidebar 하단에 "레이아웃 초기화" 버튼 추가
    클릭 시 localStorage UI preference 키 삭제 → 기본값 복원
  - View 메뉴의 'Refresh (F5)' action 개선
    현재: window.location.reload() 전체 리로드
    개선: 먼저 데이터 refetch 시도, 실패 시에만 전체 리로드
    메뉴에 "새로고침 (데이터)" / "강제 새로고침" 분리
  - 종료 메뉴 UX 개선
    웹앱이므로 실제 종료 불가
    "이 탭을 닫으시겠습니까?" 안내 + 미저장 작업 경고
확인:
  - 새로고침 후 sidebar 상태/theme이 유지되는지 코드 확인
  - 초기화 버튼 존재 확인
  - 새로고침 메뉴가 2가지로 분리되었는지

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S10_PASS\n')"
  python scripts/telegram_notify.py "✅ [S10] UI preference/새로고침/종료 UX 완료 → S11 시작"

================================================================
S11 — 빌드 검증 + 회귀 테스트
================================================================
목적: 모든 변경 사항이 빌드를 통과하고 기존 기능을 깨뜨리지 않았는지 확인
작업:
  - cd web && npm run build 실행
    빌드 실패 시: 오류 분석 → 수정 → 재빌드 → 통과할 때까지 반복
  - 빌드 통과 후 아래 점검:
    1) MenuBar.jsx 의 모든 action이 App.jsx handleMenuAction에 case로 존재하는지
    2) App.jsx 의 모든 Route path가 실제 페이지 컴포넌트를 import하고 있는지
    3) SIDEBAR_TABS의 모든 path가 Route에 등록되어 있는지
    4) 새로 추가한 API 엔드포인트가 react_api/main.py 에 router로 등록되어 있는지
  - 불일치 발견 시: 즉시 수정 → 재빌드
확인:
  - npm run build 성공
  - 불일치 항목 0개

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S11_PASS\n')"
  python scripts/telegram_notify.py "✅ [S11] 빌드 검증 + 회귀 테스트 통과 → S12 시작"

================================================================
S12 — 최종 보고서 작성
================================================================
목적: 전체 작업 결과를 보고서로 정리
작업:
  - MENU_PATCH_REPORT.md 작성 (프로젝트 루트)
    내용:
      1. 이번에 완료한 항목 (S1~S11 결과 요약)
      2. 수정 파일 목록 (파일 경로 + 변경 내용 1줄 요약)
      3. 테스트/검증 결과 (빌드 결과, 불일치 항목)
      4. 남은 리스크/Known Issues
      5. v864 대비 기능 이관 현황표 (완전반영/부분반영/누락 갱신)
  - MENU_PATCH_AUDIT_SUMMARY.md 작성 (프로젝트 루트)
    v864 기능 원장 기준 PASS/FAIL 판정
    각 항목별: 메뉴 노출 여부, 라우트 연결, export 동작, 안전장치
확인:
  - MENU_PATCH_REPORT.md 존재하고 내용 충실
  - MENU_PATCH_AUDIT_SUMMARY.md 존재하고 FAIL 항목 최소화

완료 후 반드시:
  python -c "open('logs/completed_steps.txt','a').write('S12_PASS\n')"
  python scripts/telegram_notify.py "✅ [S12] 최종 보고서 작성 완료"

================================================================
## 2. 최종 완료 처리
================================================================

모든 단계 완료 후:
  python scripts/telegram_notify.py "🎯 SQM v869 v864 기능 이관 전체 완료! S1~S12 모두 PASS. MENU_PATCH_REPORT.md 및 MENU_PATCH_AUDIT_SUMMARY.md 확인하세요."
  python -c "open('logs/completed_steps.txt','a').write('FINAL_COMPLETE\n')"

================================================================
## 3. 절대 원칙 (재확인)
================================================================
- v869 기존 핵심 기능 절대 삭제 금지
- 이미 동작하는 Route/메뉴/모달 깨뜨리지 말 것
- 스타일 변경보다 기능 보존 우선
- 임시 mock UI가 아니라 실제 동작하는 코드로 구현
- placeholder만 추가하고 완료 보고하지 말 것
- openpyxl이 없으면 csv로 대체하고 TODO 표시
- 한 단계에서 막히면 최대 3회 자동 수정 시도 후 기록하고 다음 단계 진행
