## SQM v9.0.1 — Central Allowlist (Phase 2 완료)

릴리즈일: 2026-07-22
대상: v9.0.0.1 → v9.0.1
대분류: minor (Phase 2 완료, 모니터링 추가)

### Phase 2 Step 4: 모니터링
- core/db_allowed.py
  - _VALIDATE_COUNTS: in-memory dict (key=(area, kind, result))
  - _record_validate(area, kind, result): 호출 시 카운트
  - validate() 모든 분기에 _record_validate() 호출 통합
  - stats_detailed() 함수 추가:
    - total_calls / allowed / blocked
    - by_kind: {kind: {allowed, blocked}}
  - reset_counts() 함수 (테스트용)
- tests/test_db_allowed.py
  - TestPhase2Step4 (T32~T36, 5 tests)
  - setup_method로 카운터 격리
  - empty / allowed / blocked / mixed / invalid input 케이스

### Phase 2 전체 회고
| Step | 통합 | 회귀 |
|---|---|---|
| Phase 2 Step 1 | ALLOWED_FILE_EXTS | 590 |
| Phase 2 Step 2 | REPORT_FIELDS_BY_TYPE (5×68) | 593 |
| Phase 2 Step 3 | lint 가드 (tools/lint_db_hardcoding.py) | 603 |
| **Phase 2 Step 4** | **모니터링 (in-memory)** | **608** |
| **총 (Phase 1+2)** | **10 allowlist + REVERT_MAP + lint + 모니터링** | **+41 from v8.8.5** |

### 누적 allowlist (v9.0.0 + v9.0.1)
- 10 frozenset: TABLES(25) / STATUS(12) / AREAS(10) / SCOPES(14) / LOT_EDIT(8) / CARRIER_RULE(7) / TABLE_DELETE(10) / FILE_EXTS(6) / REPORT_FIELDS_BY_TYPE(5×68) / (총 165 식별자)
- 1 dict: REVERT_MAP (5 state transitions)
- validate() dispatch 5종 + record_validate 통합
- stats_detailed() 모니터링 + lint 가드 (defense in depth)

### Cross-check 보너스
- import 추가 시 MappingProxyType NameError 즉시 발견 → from types import 추가
- report_fields L331 frozenset lookup — v9.0.0의 "동적 set skip" 결정을 부분 뒤집기 (정적 부분은 central로)

### 회귀
- 608 passed (v8.8.5 베이스라인 552 + 신규 56)

### 다음 (v9.0.2+)
- audit_log 영속화 (in-memory → DB)
- GET endpoint `/api/admin/db-allowed/stats` (frontend dashboard용)
- dynamic set → 명시적 allowlist 변환 (queries3.py L644/653/891)
- SQL context lint (broad → narrow)
- Phase 3 (또 다른 작업) — 새 시즌
