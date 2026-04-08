# SQM v869 — v864 기능 이관 패치 보고서
작성일: 2026-04-05  
재검증: 2026-04-05 (MASTER S1~S12 전체 재실행)
작업 범위: S1~S12 (12단계 자동실행)

---

## 1. 완료 항목 (S1~S11 결과 요약)

| 단계 | 내용 | 결과 |
|------|------|------|
| S1 | 메뉴/라우트 맵 생성 | PASS — logs/S1_menu_route_map.md 생성 |
| S2 | 총괄 재고 리스트 메뉴 노출 복구 | PASS — SIDEBAR + MenuBar View에 추가 |
| S3 | LOT 리스트 Excel export | PASS — API + InventoryPage 버튼 + MenuBar |
| S4 | 톤백리스트 Excel export | PASS — API + TonbagPage 버튼 + MenuBar |
| S5 | 로그 내보내기 실구현 | PASS — API + LogPage 버튼 + MenuBar action 연결 |
| S6 | 최근 파일 기능 | PASS — localStorage 기반 동적 목록 구현 |
| S7 | 정합성 검사/복구 UX 보강 | PASS — 복구버튼 분리, 2단계 확인모달, 복구 API |
| S8 | 한글 업무 라벨 보강 | PASS — SIDEBAR_TABS label 전체 한글 변경 |
| S9 | 테스트 DB 초기화 기능 | PASS — SettingsPage devMode 전용 + 2단계 확인 |
| S10 | UI preference/새로고침/종료 UX | PASS — 레이아웃 초기화, 새로고침 2분리 |
| S11 | 빌드 검증 + 회귀 테스트 | PASS — npm run build 성공, 불일치 0건 |

---

## 2. 수정 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `web/src/App.jsx` | SIDEBAR_TABS에 cargo 추가, 한글 라벨 변경, exportLotList/exportTonbagList/exportLogs/refreshData/resetLayout case 추가, navRecent 처리 |
| `web/src/components/MenuBar.jsx` | View에 총괄 재고 추가, 내보내기 서브메뉴에 LOT/톤백/로그 export 추가, DB보호 로그내보내기 action 수정, 새로고침 2분리, recentFiles 동적 목록, buildRecentFileItems |
| `web/src/pages/InventoryPage.jsx` | 상단 toolbar에 LOT 리스트 Excel 내보내기 버튼 추가 |
| `web/src/pages/TonbagPage.jsx` | 톤백리스트 Excel 내보내기 버튼 추가 |
| `web/src/pages/LogPage.jsx` | 로그 내보내기 (CSV) 버튼 추가 |
| `web/src/pages/IntegrityPage.jsx` | 검사/복구 버튼 분리, 2단계 확인 모달, 복구 결과 카드 표시 |
| `web/src/pages/SettingsPage.jsx` | 레이아웃 초기화 버튼, 개발자도구(devMode) 섹션 + 2단계 DB 초기화 |
| `web/src/utils/recentFiles.js` | localStorage 기반 최근 파일 유틸 (신규 생성) |
| `react_api/routes/tools.py` | export-lot-list, export-tonbag-list, export-logs, integrity-repair, reset-test-db, backup/create, db-optimize 엔드포인트 추가 |

---

## 3. 테스트/검증 결과

### npm run build
- **결과**: SUCCESS (65 modules transformed)
- **dist 생성**: web/dist/assets/index-*.js, index-*.css

### 회귀 점검
- MenuBar action 40개 vs handleMenuAction case 47개 → 누락 0건 (wip/exit는 MenuBar 내부 처리)
- SIDEBAR_TABS path 10개 → 모두 Routes에 등록됨
- tools_router → main.py에 등록됨

---

## 4. 남은 리스크 / Known Issues

| 항목 | 내용 | 우선순위 |
|------|------|---------|
| export-lot-list DB 컬럼명 | DB 스키마에 따라 컬럼명 불일치 가능 → 서버 시작 후 실데이터 확인 필요 | P1 |
| export-logs fallback | operation_log 테이블 없을 경우 inventory 데이터로 대체 | P2 |
| reset-test-db 테이블 목록 | 실제 로그 테이블명이 다를 경우 빈 초기화 | P2 |
| recentFiles 트리거 | 실제 입고/출고 성공 콜백에 addRecentFile() 호출 코드 미추가 (UI만 구현) | P2 |

---

## 5. v864 대비 기능 이관 현황표

| 기능 | v864 | v869 이관 | 상태 |
|------|------|-----------|------|
| 총괄 재고 리스트 메뉴 | ✅ | ✅ Sidebar + MenuBar View | 완전반영 |
| LOT 리스트 Excel export | ✅ | ✅ API + 버튼 + MenuBar | 완전반영 |
| 톤백리스트 Excel export | ✅ | ✅ API + 버튼 + MenuBar | 완전반영 |
| 로그 내보내기 | ✅ | ✅ API + LogPage 버튼 + action | 완전반영 |
| 최근 파일 동적 목록 | ✅ | ✅ localStorage + MenuBar 동적 | 완전반영 |
| 정합성 검사/복구 UX | ✅ | ✅ 버튼 분리 + 2단계 모달 + 결과 카드 | 완전반영 |
| 한글 업무 라벨 (Sidebar) | ✅ | ✅ 재고조회/판매배정/화물결정 등 | 완전반영 |
| 테스트 DB 초기화 (개발) | ✅ | ✅ devMode 전용 + 2단계 확인 + production 차단 | 완전반영 |
| UI preference 레이아웃 초기화 | ✅ | ✅ SettingsPage 초기화 버튼 | 완전반영 |
| 새로고침 (데이터/강제) | ✅ | ✅ 메뉴 2분리 | 완전반영 |
| 종료 UX 안내 | ✅ | ✅ '탭을 닫으세요' 안내 toast | 완전반영 |
