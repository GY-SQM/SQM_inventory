# SQM v864.3 PyWebView Migration — 핸드오프 문서 (Phase 7 진입용)

> **작성일**: 2026-04-26
> **기준 커밋**: `ed46b67` (HEAD → claude/v864-3-sprint0) — 134 commits total
> **진행률**: Phase 0~6 완료 (약 85%), Phase 7 실사용 대기

---

## 복붙 명령어 (새 세션 시작용)

```
나는 Nam Ki-dong 사장님이다.
SQM v864.3 마이그레이션 — Phase 7 (실사용 테스트) 진입.

프로젝트 폴더: D:\program\SQM_inventory\Claude_SQM_v864_3
v864.2 원본 참조: D:\program\sqm_2_upload_clean_v864_2

━━━ 필수 참조 파일 ━━━
1. CLAUDE.md (프로젝트 규칙 + 8-Phase 로드맵)
2. HANDOFF_v864_3_CURRENT.md (이 파일 — 현재 진행 상황 전체)
3. REPORTS/phase5_regression.json (회귀 테스트 87/87 PASS)
4. REPORTS/playwright_all_menus.json (UI 전수검사 99/99 PASS)
5. docs/handoff/feature_matrix.json (85개 기능 매핑)
6. docs/handoff/v864_2_structure.json (v864.2 UI 구조)

━━━ 완료 상황 (Phase 0~6) ━━━
Phase 0: Safety Net (pytest, smoke test) ✅
Phase 1: UI Manifest + 85 기능 매핑 ✅
Phase 1c: UI 요소 복구 (메뉴/툴바/사이드바) ✅
Phase 2: TOP 3 엔드포인트 + 런타임 검증 ✅
Phase 3: Dashboard KPI 실데이터 + 건강성 가시화 ✅
Phase 4: 사이드바 9탭 + 메뉴 79개 + PDF 입고 배선 ✅
Phase 5: 회귀 테스트 87/87 PASS (100%) ✅
Phase 6: PyInstaller EXE 빌드 (33MB, spec+bat 완성) ✅

━━━ 남은 작업 ━━━
Phase 7: 사장님 실사용 1주 + 버그 수집
Phase 8: 공식 릴리스 (CHANGELOG + GY Logis 전환)

━━━ 규칙 ━━━
- engine_modules/ 수정 금지 (v864.2 원본 그대로)
- v864.2와 동일한 UI + 기능이 목표
- 질문하지 말고 Ruby가 판단해서 진행
- 모든 수정 후 Playwright 검증 필수

지시 사항: _______________
```

---

## 1. 프로젝트 개요

**목표**: Tkinter + ttkbootstrap 기반 v864.2를 → PyWebView + HTML/CSS/JS + FastAPI 기반 v864.3으로 마이그레이션. **UI와 기능 모두 v864.2와 100% 동일**해야 함.

**기술 스택**:
| 계층 | v864.2 (원본) | v864.3 (마이그레이션) |
|------|---------------|----------------------|
| Desktop Shell | Tkinter + ttkbootstrap | PyWebView 5.1.0 |
| Backend | 직접 Python 호출 | FastAPI 0.104.1 + Uvicorn |
| Frontend | Tkinter 위젯 | Vanilla HTML/CSS/JS |
| Data | pandas + openpyxl + SQLite | 동일 |
| Packaging | PyInstaller | 동일 |

---

## 2. v864.2 원본 구조 (참조 경로: `D:\program\sqm_2_upload_clean_v864_2`)

### 핵심 모듈
| 폴더 | 파일 수 | 역할 |
|------|---------|------|
| gui_app_modular/ | 122 | Tkinter 앱 (메인, 다이얼로그 43개, 핸들러 15개, 믹스인 17개, 탭 13개) |
| engine_modules/ | 36 | 비즈니스 로직 (DB, 재고, 정합성, 입출고, 톤백) |
| features/ | 35 | AI 파싱, 알림, 보고서 |
| parsers/ | 10+ | 문서 파서 (PDF, Excel, 피킹리스트) |
| utils/ | 10+ | 유틸리티 (날짜, 포맷터, 에러 알림) |
| core/ | 8 | 바코드 스캔, 컬럼 레지스트리, 상수 |

### 메뉴 구조 (menu_registry.py 기준)
| 메뉴 | 항목 수 | 핵심 기능 |
|------|---------|----------|
| 출고 | 14 | 즉시출고, 빠른출고, 피킹, Allocation, 승인, Sales Order |
| 파일 | 25 | 입고(PDF/Excel), D/O, 반품, 내보내기, 백업, 도구 |
| 보고서 | 12 | 거래명세서, Detail of Outbound, DN, LOT 상세, PDF |
| 도구 | 35 | 제품마스터, PDF변환, 정합성, Gemini AI, DB보호, 고급 |
| View | 11 | 탭이동(9개) + 새로고침 + 테마 |
| 도움말 | 6 | 사용법, 단축키, 상태안내, 버전 |
| 품목 | 3 | 재고요약, LOT조회, 입출고현황 |
| **합계** | **~106** | (toolbar 7개 + 우상단 3개 별도) |

### 다이얼로그 목록 (gui_app_modular/dialogs/ — 43개)
v864.2에서 Tkinter Toplevel 다이얼로그로 구현된 것들:
- allocation_approval_dialog, allocation_template_dialog
- barcode_scan_upload_dialog, bulk_outbound_dialog
- column_mapper_dialog, dn_cross_check_dialog
- do_update_dialog, email_config_dialog
- help_dialogs, inbound_dialog_base, inbound_history_dialog
- info_dialogs, location_upload_preview
- lot_allocation_audit_mixin, lot_detail_dialog
- onestop_inbound, onestop_outbound
- outbound_preview_dialog, outbound_scheduled_dialog
- pdf_convert_dialog, picking_template_dialog
- product_inventory_report, product_master_helper
- quick_outbound_paste_dialog, return_dialog
- return_statistics_dialog, review_center
- sales_order_dialog, scan_result_dialog
- settlement_dialog, snapshot_chart_dialog
- swap_report_dialog, test_runner_dialog
- theme_selector, tonbag_location_dialog 등

---

## 3. v864.3 현재 상태 (Phase 6 완료 시점)

### 파일 구조
```
Claude_SQM_v864_3/
├── main_webview.py          ← PyWebView 진입점 (300줄)
├── frontend/
│   ├── index.html           ← 7개 메뉴 + 9개 사이드바 + 7개 툴바 (100 data-action)
│   ├── js/sqm-inline.js     ← 9,002줄 단일 IIFE (132 ENDPOINTS, 47 모달)
│   └── css/                 ← design-system.css + v864-layout.css
├── backend/api/             ← FastAPI (19개 .py, 라우터 17개)
│   ├── __init__.py          ← app = FastAPI(), 17 라우터 등록
│   ├── actions.py           ← 정합성, 백업, LOT Excel, 복원
│   ├── actions2.py          ← 입고취소, 위치이동, 출고확정
│   ├── actions3.py          ← DB최적화, 로그정리, D/O업데이트, 반품, DB초기화
│   ├── queries.py           ← 12 GET (입고/승인/출고/백업/감사/재고추이/품목)
│   ├── queries2.py          ← 6 GET (일일/월간/최근/반품/출고확정)
│   ├── queries3.py          ← 5 GET (Sales Order DN, 교차검증, D/O, 청구서)
│   ├── allocation_api.py    ← Excel 업로드, 승인반영
│   ├── inventory_api.py     ← /api/inventory, /api/tonbags, /api/scan
│   ├── info.py              ← 사용법, 단축키, 상태안내, 백업가이드, 버전
│   ├── dashboard.py         ← KPI stats + alerts
│   ├── inbound.py           ← PDF/Excel 입고
│   └── ...
├── engine_modules/          ← v864.2 원본 (수정 금지)
├── features/                ← v864.2 원본 (수정 금지)
├── parsers/                 ← v864.2 원본 (수정 금지)
├── utils/                   ← v864.2 원본 (수정 금지)
├── gui_app_modular/         ← v864.2 원본 (EXE 번들용)
├── data/db/sqm_inventory.db ← SQLite DB (v864.2와 동일 스키마)
├── build/SQM_v864_3.spec    ← PyInstaller spec
├── dist/SQM_v864_3.exe      ← 33MB 단일 EXE (테스트 빌드)
└── scripts/                 ← 테스트 스크립트
    ├── phase5_regression_test.py   (87/87 PASS)
    └── test_all_menus_playwright.py (99/99 PASS)
```

### ENDPOINTS 현황 (sqm-inline.js)
| 구분 | 수량 | 상태 |
|------|------|------|
| 총 ENDPOINTS | 132 | JS 라우터에 등록됨 |
| WIP (준비 중) | **0** | 전부 실구현 완료 |
| NOT_READY | **0** | menubar.py 우회 완료 |
| 모달 함수 | 47 | showXxxModal() |
| data-action 버튼 | 100 | HTML에 등록됨 |

### 테스트 결과
| 테스트 | 결과 |
|--------|------|
| Playwright UI 전수검사 | **99/99 PASS** (7 메뉴, 79 항목, 9 사이드바, 7 툴바) |
| Phase 5 회귀 테스트 | **87/87 PASS** (스키마, API, 무결성, UI, Feature Matrix, 데이터 비교) |
| JS syntax (node --check) | PASS |
| Python syntax (5 파일) | ALL PASS |

---

## 4. Phase별 완료 이력

### Phase 0: Safety Net (2026-04-21)
- pytest 인프라, smoke test, config_sql.py

### Phase 1~1c: UI Manifest + 복구 (2026-04-21)
- feature_matrix.json (85개 기능), design_tokens.json, v864_2_structure.json
- index.html 메뉴/사이드바/툴바 HTML 골격

### Phase 2: TOP 3 엔드포인트 (2026-04-21)
- /api/health, /api/inventory, /api/dashboard/stats
- favicon, CSS, 런타임 검증

### Phase 3: Dashboard KPI (2026-04-21~22)
- 5단계 카드 + 매트릭스, 실데이터 연동
- 상태바 Engine 모듈 카운터

### Phase 4: 전체 기능 활성화 (2026-04-22~24)
- 9탭 전부 동작 (Inventory 24열, Allocation/Picked/Sold 2단 구조)
- 메뉴 79개 실구현 (WIP 16개 → 0개)
- NOT_READY 5개 → 0개
- 14개 JS 네이티브 모달 추가
- 반품 2탭 다이얼로그, 복원 모달, 품목 3종 모달

### Phase 5: 회귀 테스트 (2026-04-24~25)
- DB Schema Parity: v864.2 vs v864.3 테이블/컬럼 일치
- API Health: 32개 GET 전부 200 OK
- Data Integrity: API 응답 = DB 실데이터
- Playwright: 9탭 + KPI + 2단구조 검증
- Feature Matrix: WIP 0개, 커버리지 100%
- **87/87 PASS (100%)**

### Phase 6: EXE 빌드 (2026-04-25)
- build/SQM_v864_3.spec 완성 (backend/data/gui_app_modular 포함)
- hiddenimports 보강 (starlette, anyio, clr_loader, fitz 등)
- 테스트 빌드 33MB EXE 생성 성공
- 빌드.bat 제공 (사장님 더블클릭 빌드)

---

## 5. v864.2 대비 미구현 / 차이점 목록

### 완전 동등 (v864.2 = v864.3)
- 사이드바 9탭 (Inventory, Allocation, Picked, Outbound, Return, Move, Dashboard, Log, Scan)
- 상단 메뉴 7개 (출고, 파일, 보고서, 도구, View, 도움말, 품목)
- 툴바 7개 버튼 (PDF입고, 즉시출고, 반품, 재고조회, 정합성, 백업, 설정)
- 키보드 단축키 (F5, Ctrl+I, Ctrl+O 등)
- 우클릭 메뉴, 테이블 정렬, 더블클릭 LOT 상세
- Dark/Light 테마 토글

### 기능은 있지만 v864.2 다이얼로그보다 단순한 것
| 기능 | v864.2 | v864.3 현재 | 비고 |
|------|--------|-------------|------|
| 이메일 설정 | SMTP 실 연동 다이얼로그 | 설정 폼 (저장만) | Phase 7에서 보완 가능 |
| 자동 백업 설정 | 스케줄러 연동 | 설정 폼 (저장만) | 동일 |
| 입고/피킹 템플릿 | CRUD 다이얼로그 | 설정 폼 | 동일 |
| 문서 변환 (OCR) | Tesseract 연동 | 파일 선택 UI만 | OCR 엔진 별도 필요 |
| Gemini AI 채팅 | 실시간 채팅 | 버전 정보 표시 | API 키 필요 |
| 테마 선택 | 17개 테마 다이얼로그 | Dark/Light 2종 | 확장 가능 |
| 글꼴 크기 | 3단계 (11/13/16pt) | 미구현 | CSS 변수로 추가 가능 |

### v864.2에만 있는 기능 (v864.3 미포함)
| 기능 | v864.2 위치 | 우선순위 |
|------|------------|---------|
| Swap 리포트 | swap_report_dialog.py | 낮음 (optional) |
| Sales Order 업로드 | sales_order_dialog.py | 중간 |
| 개발자 모드 토글 | keybindings_mixin.py | 낮음 |
| 운영 DB 스키마 점검 | toolbar_mixin.py | 낮음 |
| 대시보드 자동갱신 30초 | toolbar_mixin.py | 중간 (JS setInterval 추가만) |

---

## 6. Phase 7 실행 계획

### 목표
사장님이 GY Logis 광양 현장에서 1주간 실사용하면서 버그 수집

### 사전 준비
1. `.venv`에서 정식 EXE 빌드 (`빌드.bat` 더블클릭)
2. `dist/SQM_v864_3.exe`를 광양 PC에 복사
3. `data/db/sqm_inventory.db`를 EXE 옆에 배치 (또는 EXE 내장)

### 일일 점검
- 매일 사용 후 `sqm_debug.log` 확인
- 이슈 발생 시 REPORTS/PHASE7_DAY{N}.md에 기록
- Critical 버그는 즉시 핫픽스 → 재빌드

### 종료 기준
- 7일간 Critical 버그 0건
- 사장님 "이거 쓸 만하다" 승인

---

## 7. Phase 8 릴리스 계획

1. CHANGELOG.md 작성
2. version.py 업데이트 (v8.6.4.3)
3. 최종 EXE 빌드
4. git tag v864.3-RELEASE
5. GY Logis 현장 전환 공지
6. v864.2 EXE 백업 유지 (24시간 혼용 운영 후 완전 전환)

---

## 8. 롤백 시나리오

| 상황 | 명령어 | 복원 지점 |
|------|--------|----------|
| Phase 7 치명 버그 | v864.2 EXE로 임시 복구 | 사장님 구버전 사용 |
| 특정 커밋 버그 | `git revert <hash>` | 해당 기능만 되돌림 |
| 전체 초기화 | `git reset --hard 5f7f5ff` | Phase 2 완전 종료 지점 |

---

## 9. 핵심 수치 요약

| 항목 | 수치 |
|------|------|
| 총 커밋 | 134 |
| sqm-inline.js | 9,002줄 |
| ENDPOINTS | 132개 |
| 모달 함수 | 47개 |
| API 라우터 | 17개 (19 .py 파일) |
| HTML data-action | 100개 |
| Playwright 테스트 | 99/99 PASS |
| 회귀 테스트 | 87/87 PASS |
| EXE 크기 | 33MB |
| WIP 잔여 | 0 |
| NOT_READY 잔여 | 0 |

---

**작성**: Ruby (Claude Opus 4.6)
**기준일**: 2026-04-26
**다음 Phase**: 7 (실사용 테스트)
