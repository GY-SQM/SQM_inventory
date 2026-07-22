## SQM v9.0.0 — Central Allowlist (Phase 1 CLOSED)

릴리즈일: 2026-07-22
대상: v9.0.0-beta → v9.0.0
대분류: major (DB 접근 인터페이스 변경 가능)

### v9.0.0 정식 (Phase 1 closed)
- core/db_allowed.py (NEW, ~10 KB)
  - ALLOWED_TABLES (25개, frozenset)
  - ALLOWED_STATUS (12개, frozenset, +1 RESERVED)
  - ALLOWED_AREAS (10개, frozenset)
  - ALLOWED_SCOPES (14개, frozenset)
  - REVERT_MAP (5개, dict — state transition)
  - LOT_EDIT_FIELDS (8개, frozenset)
  - CARRIER_RULE_EDIT_FIELDS (7개, frozenset)
  - ALLOWED_TABLE_DELETE (10개, frozenset, ⊆ ALLOWED_TABLES)
  - validate(area, kind, value) 단일 진입점
  - helpers: all_tables / all_statuses / all_areas / stats

### 마이그레이션 (Phase 1 Step 1~4)
- backend/api/status_revert_api.py
  - ALLOWED_SCOPES + REVERT_MAP → central allowlist
- backend/api/actions3.py
  - LOT_EDIT_FIELDS → central allowlist
- backend/api/settings.py
  - CARRIER_RULE_EDIT_FIELDS + ALLOWED_TABLE_DELETE → central allowlist

### queries3.py SKIP
- queries3.py는 정적 ALLOWED_* 없음 (모두 동적 set comprehension)
  - L331: `{f["field"] for f in _REPORT_FIELDS.get(report_type, [])}` (런타임 동적)
  - L644, L653, L891: `{v.lower() for v in vals}` (filter_values에서 동적)
- v8.8.5 audit 인벤토리 #1.4: "queries3.py:1925 — 테이블명 동적 (DB 메타)"
- 동적 검증 패턴은 central allowlist 대상 아님
- Phase 2 후보: 동적 set comprehension → 명시적 allowlist 변환 검토

### 회전 패턴 4개
1. frozenset 단순 (set membership) — 6개 allowlist
2. dict 매핑 (state transition) — REVERT_MAP
3. validate(kind=...) dispatch — table/status/area/scope_type/lot_field
4. invariant cross-check — ALLOWED_TABLE_DELETE ⊆ ALLOWED_TABLES

### Cross-check 보너스 (자동 발견)
- ALLOWED_STATUS에 RESERVED 누락 → 추가
- ALLOWED_TABLES에 5개 누락 테이블 → 추가
  (outbound, outbound_item, picking_table, outbound_event_log, allocation_plan, return_history)
- 키/값 invariant (T15, T16, T24, T25) — 회귀 보호

### 테스트
- tests/test_db_allowed.py (29 tests, 누적)
  - Smoke S01~S05 + Pytest T01~T25
- tests/test_audit_yellow_2_f_string_sql_inventory.py
  - regex 확장 (v9.0.0 새 패턴 인식)
  - audit 인벤토리 ↔ 마이그레이션 정합성 유지

### 회귀
- 587 passed (v8.8.6 베이스라인 557 + 신규 30)

### 다음 (Phase 2 후보)
- report_templates.py _ALLOWED_EXT (파일 확장자)
- queries3.py 동적 set → 명시적 allowlist 변환
- lint 가드 (db_allowed 외부에서 테이블/컬럼명 하드코딩 감지)
- 모니터링 (validate() 호출 횟수 / 차단 카운트)
