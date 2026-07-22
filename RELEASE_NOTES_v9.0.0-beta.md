## SQM v9.0.0-beta — Central Allowlist (Phase 1 Step 1~4)

릴리즈일: 2026-07-22
대상: v9.0.0-alpha → v9.0.0-beta
대분류: major (DB 접근 인터페이스 변경 가능)

### 누적 변경 (Phase 1 Step 1~4)
- core/db_allowed.py (NEW, 누적 8.4 KB)
  - ALLOWED_TABLES (25개, frozenset, +6 outbound/picking/etc.)
  - ALLOWED_STATUS (12개, frozenset, +1 RESERVED)
  - ALLOWED_AREAS (10개, frozenset)
  - ALLOWED_SCOPES (14개, frozenset)
  - REVERT_MAP (5개, dict — state transition)
  - LOT_EDIT_FIELDS (8개, frozenset)
  - CARRIER_RULE_EDIT_FIELDS (7개, frozenset)
  - ALLOWED_TABLE_DELETE (10개, frozenset, ⊆ ALLOWED_TABLES)
  - validate(area, kind, value) 단일 진입점
  - helpers: all_tables / all_statuses / all_areas / stats

### 마이그레이션
- backend/api/status_revert_api.py — ALLOWED_SCOPES + REVERT_MAP
- backend/api/actions3.py — LOT_EDIT_FIELDS
- backend/api/settings.py — CARRIER_RULE_EDIT_FIELDS + ALLOWED_TABLE_DELETE
- 사용처 변경 없음 (import 참조)

### 회전 패턴 4개 확립
1. frozenset 단순 (set membership)
2. dict 매핑 (state transition) — REVERT_MAP (cross-check: 키/값 모두 ALLOWED_STATUS)
3. validate(kind=...) dispatch 확장 — table/status/area/scope_type/lot_field
4. invariant cross-check — ALLOWED_TABLE_DELETE ⊆ ALLOWED_TABLES

### Cross-check 보너스 (자동 발견)
- ALLOWED_STATUS에 RESERVED 누락 발견 → 추가
- ALLOWED_TABLES에 5개 누락 테이블 발견 → 추가
  (outbound, outbound_item, picking_table, outbound_event_log, allocation_plan, return_history)
- 키/값 invariant 테스트 (T15, T16, T24, T25) — 회귀 보호

### 테스트
- tests/test_db_allowed.py (29 tests, 누적)
  - Smoke S01~S05 + Pytest T01~T25
  - 4개 카테고리 (테이블, 상태, scope, field)
  - 4개 invariant (frozenset 불변성, dict cross-check, subset)
- tests/test_audit_yellow_2_f_string_sql_inventory.py
  - regex 확장 (v9.0.0 새 패턴 인식: import 할당, ALLOWED_TABLE_DELETE)
  - 인벤토리 ↔ 마이그레이션 정합성 유지

### 회귀
- 587 passed (v8.8.6 베이스라인 557 + 신규 30)

### 다음 (v9.0.0 정식)
- queries3.py (큰 회전, 7+ 위치) — 새 패턴 (table list) 가능성
- report_templates.py _ALLOWED_EXT (단순, 파일 확장자)
- v9.0.0 정식 release
