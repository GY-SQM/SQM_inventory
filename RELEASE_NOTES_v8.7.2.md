# SQM Inventory v8.7.2 — 전수검사 기반 품질 개선

**릴리즈 날짜**: 2026-06-11
**브랜치**: `main`
**이전 버전**: v8.7.1
**테스트**: 148개 PASS (기존 85 + 신규 63)

---

## 🎯 개요

3-AI(Claude + Codex + Gemini) 전수검사를 통해 발견된 33개 논리 오류를
1~3단계로 나눠 수정하고, B-7 라우터 이관 + E2E/보안/성능 감사까지 완료한
품질 릴리즈입니다. 데이터 무결성 버그 9건 포함.

---

## 🔴 1단계 — 데이터 무결성 (영향도 상, 9건)

### B-1: approve/reject 컬럼 불일치 수정
- **파일**: `backend/api/allocation_api.py:548`
- `reject_allocation`이 `approval_status` 컬럼을 수정하던 버그 → `status` 통일
- approve와 reject가 서로 다른 컬럼을 수정해 상태 추적 불가했던 문제 해결

### B-2: cancel_by_sale_ref inventory_tonbag 미복구
- **파일**: `backend/api/allocation_api.py:629`
- 취소 시 `inventory` 복구만 하고 `inventory_tonbag`은 RESERVED로 방치되던 버그
- `inventory_tonbag` AVAILABLE 복구 UPDATE 추가

### B-3: outbound_confirm current_weight 미차감
- **파일**: `backend/api/actions2.py:225`
- 출고 확정 시 `inventory.current_weight`가 0으로 차감되지 않던 버그
- `current_weight=0` 추가, 예외 시 `rollback()` 추가

### B-4: onestop_complete inventory.status 미갱신
- **파일**: `backend/api/outbound_api.py:852`
- `inventory_tonbag`만 SOLD 처리하고 상위 `inventory.status`는 PICKED 방치
- `by_lot` 루프에 `inventory UPDATE status='SOLD'` 추가

### B-5: inventory_api._db() WAL 미설정
- **파일**: `backend/api/inventory_api.py:32`
- 5초 폴링 중 동시 write 시 "database is locked" 발생 가능
- `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=3000` 추가

### D-1: allocation 이중 예약 차단 인덱스 추가
- **파일**: `engine_modules/db_migration_mixin.py`
- 동일 톤백을 두 고객사가 동시 예약 가능하던 허점
- `idx_alloc_tonbag_no_dup`: `tonbag_id` 단독 UNIQUE partial index 추가

### F-1+F-2: data-route 3중 클릭 바인딩 충돌
- **파일**: `frontend/js/router.js`
- `main.js` + `sqm-inline.js` + `router.js` 3중 바인딩으로 클릭 1회에 페이지 2~3회 렌더
- `router.js initRouter()` 클릭 바인딩 제거, `sqm-inline.js` 단독 권위 라우터로 확정

### F-6: sqm-tonbag.js boot() 중복 실행
- **파일**: `frontend/js/sqm-tonbag.js`
- `sqm-tonbag.js`와 `sqm-inline.js` 두 곳에서 DOMContentLoaded boot() 등록
- KPI API 2회 호출, 초기 페이지 2회 렌더 문제 해결
- `sqm-tonbag.js` boot() DOMContentLoaded 등록 제거, `window.applyStoredFontScale` 노출

### F-10: defineProperty 이름 오타
- **파일**: `frontend/js/sqm-tonbag.js:3862`
- `'window.getCurrentRoute()'` 문자열 오타 property 제거

---

## 🟠 2단계 — 로직 오류 (영향도 중, 12건)

### F-3+F-7: window.API 즉시캡처 버그
- `sqm-aux-modals.js`, `sqm-upload-modals.js`, `sqm-settings-templates.js`
- PyWebView `on_loaded` 이전 실행 시 빈값 캡처 → fetch 실패
- `_api()` 실시간 함수로 교체

### F-4: onImportAllocationTemplate 누락
- `sqm-inline.js` ENDPOINTS에 누락된 액션 추가

### F-5: _currentRoute 분리 변수 불일치
- `window._currentRoute` getter → `window.getCurrentRoute()` 위임으로 단일 정본화

### B-7: /api/allocation 라우터 이중 등록 + 완전 이관
- `__init__.py` alloc_router 이중 등록 제거
- `inventory_api.py` alloc_router 6개 엔드포인트 → `allocation_api.py` 완전 이관
- 응답 형식 `{success: True}` → `{ok: True}` 통일

### B-8: sidebar-counts SHIPPED/CONFIRMED 미포함
- `dashboard.py` 쿼리에 SHIPPED/CONFIRMED 상태 추가

### B-9+B-10: 응답 형식 혼재 통일
- `dashboard.py` 에러 응답 `{error: str(e)}` → `{ok: False, error: str(e)}`
- `allocation_api.py patch_allocation` `{success: True}` → `{ok: True}`

### D-2: 마이그레이션 역순 호출
- `db_migration_mixin.py` v675>v700, v740>v800, v868>v872 역순 재정렬

### D-3: RAISE(FAIL) 트리거 전파
- `outbound_mixin.py` current_weight UPDATE 시 트리거 에러 명시 catch

### D-4: sold_table UNIQUE COALESCE 타입 혼용
- `COALESCE(sub_lt, '')` INTEGER/TEXT 혼용 → `tonbag_id` 기반 partial index

### D-5: 복구 경로 weight 음수 미검증
- `cancel_outbound_tonbag` weight 음수 파라미터 검증 + abs() 방어

### D-6: total.sample_bags 항상 0
- sidebar-counts `total.sample_bags` 하드코딩 0 → 실제 합산

---

## 🟡 3단계 — 코드 품질 (영향도 하, 8건)

| 이슈 | 수정 내용 |
|---|---|
| F-9 | Ctrl+3 중복 case → C-p(picked) 분리 |
| F-11 | renderPage 포워더 `_navigateAndSync` 별칭 추가 |
| F-12 | showToast sqm-core 미로드 시 안전 폴백 |
| B-11 | /api/action prefix 규칙 명세 주석 |
| D-7 | db_schema_mixin v289~v600 이중 마이그레이션 제거 |
| D-8 | 캐시 fallback 로그 warning→debug |
| D-9 | uvicorn 포트 충돌 시 자동 재시도 (최대 3회) |

---

## 🔒 보안 감사 결과

- SQL Injection: **전체 안전** (화이트리스트 + 파라미터 바인딩)
- 인증: 로컬 전용(PyWebView) 설계로 의도된 미인증 — localhost 바인딩으로 외부 노출 차단
- 민감정보: 하드코딩 없음 (API 키 → ini/환경변수)

---

## ⚡ 성능 감사 결과

| API | 응답시간 |
|---|---|
| /api/inventory | 19ms |
| /api/allocation | 4ms |
| /api/dashboard/kpi | 10ms |
| /api/dashboard/sidebar-counts | 9ms |
| /api/tonbags | 29ms |

모든 주요 API < 30ms (데이터: 1540톤백 / 140 LOT)

---

## 🧪 테스트

```
tests/test_stage1_bugfix.py   22개  ✅
tests/test_stage2_bugfix.py   21개  ✅
tests/test_stage3_bugfix.py   15개  ✅
tests/test_stage5_alloc_migration.py  5개  ✅
기존 테스트 (phase1~4)        85개  ✅
────────────────────────────────────
합계                         148개  ✅  4.26s
```

---

## 📁 변경 파일 목록

**Backend (9개)**
- `backend/api/__init__.py`
- `backend/api/actions.py`
- `backend/api/actions2.py`
- `backend/api/allocation_api.py`
- `backend/api/dashboard.py`
- `backend/api/info.py`
- `backend/api/inventory_api.py`
- `backend/api/outbound_api.py`
- `backend/api/allocation_api.py` (B-7 이관 포함)

**Engine/DB (4개)**
- `engine_modules/database.py`
- `engine_modules/db_migration_mixin.py`
- `engine_modules/db_schema_mixin.py`
- `engine_modules/inventory_modular/outbound_mixin.py`

**Frontend (9개)**
- `frontend/index.html`
- `frontend/js/main.js`
- `frontend/js/router.js`
- `frontend/js/sqm-aux-modals.js`
- `frontend/js/sqm-core.js`
- `frontend/js/sqm-inline.js`
- `frontend/js/sqm-onestop-stream.js`
- `frontend/js/sqm-settings-templates.js`
- `frontend/js/sqm-tonbag.js`
- `frontend/js/sqm-upload-modals.js`

**기타**
- `main_webview.py`
- `version.py`
