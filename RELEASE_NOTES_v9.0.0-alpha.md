## SQM v9.0.0-alpha — Central Allowlist (Phase 1 partial)

릴리즈일: 2026-07-22
대상: v8.8.6 → v9.0.0-alpha
대분류: major (DB 접근 인터페이스 변경 가능)

### 신규 모듈
- core/db_allowed.py (NEW, 6.8 KB)
  - ALLOWED_TABLES (19개, frozenset)
  - ALLOWED_STATUS (12개, frozenset, +1 RESERVED)
  - ALLOWED_AREAS (10개, frozenset)
  - ALLOWED_SCOPES (14개, frozenset)
  - REVERT_MAP (5개, dict — state transition)
  - LOT_EDIT_FIELDS (8개, frozenset)
  - validate(area, kind, value): 단일 검증 진입점
  - helpers: all_tables / all_statuses / all_areas / stats

### 마이그레이션 (Phase 1 Step 1~3)
- backend/api/status_revert_api.py
  - ALLOWED_SCOPES, REVERT_MAP → core.db_allowed로 이전
- backend/api/actions3.py
  - LOT_EDIT_FIELDS → core.db_allowed로 이전
- 사용처 변경 없음 (import 참조)

### 회전 패턴 3개 확립
1. frozenset 단순 (set membership) — ALLOWED_TABLES / STATUS / AREAS / SCOPES / LOT_EDIT_FIELDS
2. dict 매핑 (state transition) — REVERT_MAP (cross-check: 키/값 모두 ALLOWED_STATUS)
3. validate(kind=...) dispatch 확장 — kind=table/status/area/scope_type/lot_field

### Cross-check 보너스
- ALLOWED_STATUS에 RESERVED 누락 발견 → 추가
- 키/값 invariant 테스트 (T15, T16) — 회귀 보호

### 테스트
- tests/test_db_allowed.py (NEW, 25 tests)
  - Smoke S01~S05: 모듈 import + 기본 동작
  - Pytest T01~T21: validate + frozenset + helpers + REVERT_MAP + LOT_EDIT_FIELDS
- tests/test_audit_yellow_2_f_string_sql_inventory.py
  - ALLOWED_FIELDS → LOT_EDIT_FIELDS (audit 인벤토리 일관성)

### 회귀
- 583 passed (v8.8.6 베이스라인 557 + 신규 26)

### 다음 (v9.0.0 정식)
- queries3.py / settings.py / report_templates.py 등 마이그레이션 (Phase 1 Step 4+)
- v9.0.0 정식 release
