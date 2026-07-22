## SQM v9.0.0.1 — Central Allowlist (Phase 2 Step 1~3)

릴리즈일: 2026-07-22
대상: v9.0.0 → v9.0.0.1
대분류: hotfix (Phase 2 추가분, major 변경 없음)

### Phase 2 Step 1: ALLOWED_FILE_EXTS
- core/db_allowed.py
  - ALLOWED_FILE_EXTS frozenset 추가 (6개: .xlsx/.xls/.pdf/.docx/.csv/.html)
  - validate(kind='file_ext', value) dispatch 추가
- backend/api/report_templates.py
  - 모듈-로컬 _ALLOWED_EXT tuple → ALLOWED_FILE_EXTS frozenset
  - 사용처 2곳 (검증 + 에러 메시지) 자동 변경

### Phase 2 Step 2: REPORT_FIELDS_BY_TYPE
- core/db_allowed.py
  - REPORT_FIELDS_BY_TYPE (MappingProxyType) 추가
  - 5 report_type × 68 fields frozenset
  - import: from types import MappingProxyType (read-only dict)
- backend/api/queries3.py
  - L331: dynamic set comprehension → frozenset lookup (명시화)
  - L644/653/891: dynamic set (user input) 의도된 dynamic으로 skip
  - L337: _REPORT_FIELDS[report_type] (label 검색) — 원본 유지

### Phase 2 Step 3: Lint 가드
- tools/lint_db_hardcoding.py (NEW, 5 KB)
  - 83개 식별자 (10 allowlist 통합) × backend/ 스캔
  - word boundary 매칭 (false positive 최소화)
  - exclude: core/db_allowed.py, tests/, tools/, __pycache__, .git
  - cp949/UTF-8 인코딩 처리
  - top 5 파일만 표시 (노이즈 제한)
  - exit 0 (clean) / 1 (hits) — CI 통합 가능
- tests/test_lint_db_hardcoding.py (NEW, 3.4 KB, 10 tests)
  - L01~L10: import / targets / should_exclude / find_hardcoding / main
  - tmp_path 합성 파일
  - subprocess 테스트 (CI 시뮬레이션)

### Cross-check 보너스
- import 추가 시 MappingProxyType NameError 즉시 발견 → from types import 추가

### 회귀
- 603 passed (v9.0.0 587 + 신규 16)

### 누적 allowlist (v9.0.0 + 0.0.1)
- 10개 frozenset (TABLES/STATUS/AREAS/SCOPES/LOT_EDIT/CARRIER_RULE/TABLE_DELETE/FILE_EXTS/REPORT_FIELDS_BY_TYPE)
- 1개 dict (REVERT_MAP)
- validate() dispatch 5종 (table/status/area/scope_type/lot_field/file_ext)

### 다음 (Phase 2 Step 4 또는 v9.0.1)
- 모니터링 (validate() 호출 카운트 + audit_log 기록)
- v9.0.1 (Phase 2 완료 후 minor)
