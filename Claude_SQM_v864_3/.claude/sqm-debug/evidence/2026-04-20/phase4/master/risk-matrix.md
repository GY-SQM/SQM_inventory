# Master Risk Matrix — Phase 4
Date: 2026-04-20 | Step 1 Diagnostic Complete

## Consolidated Priority Queue

| ID | Issue | Team | P08 Score | Band | Phase 4 Sub | Action |
|---|---|---|---|---|---|---|
| E4-A/D-002 | Weight floor TRIGGER 미적용 — negative weight 가능 | D+E | ~110 | **P1** | 4-A | CHECK constraint migration + validator boot 강제 |
| A-4a | Dashboard thread observability 부재 | A | ~54 | P2 | 4-B | thread ID + timing 로깅 12줄 |
| A-4b | Regression guard 전무 (Phase 3 fix 3건) | A+D | ~36 | P3 | 4-A | tests/ 디렉터리 + regression_*.py 작성 |
| E5-A | Export no temp-file pattern | E | ~32 | P3 | defer | write-then-rename 패턴 |
| E3-A/D-001 | sold_table UNIQUE constraint 없음 | D+E | ~24 | P4 | 4-A | migration + INSERT OR IGNORE |
| E2-A | Cache 이중 실행 visibility | E | ~45 | P2 | 4-A | 로그 레벨 개선 |
| A-3-1 | run_claude.bat 경로 오류 | A | 6 | P5 | 4-A | 1줄 fix |
| A-3-2 | dashboard_tab.py bare except ×2 | A | 2 | P5 | 4-A | 2줄 fix |

## Phase 4 Sub-phase Assignment

### 4-A: Regression runbook + critical fixes (Teams A+D+E)
Priority order:
1. Create tests/ + tests/fixtures/ structure (E6, unblocks everything)
2. Weight floor CHECK constraint migration (E4-A+D-002)
3. Regression guards for Phase 3 fixes (P13 backfill):
   - tests/regression_engine_current_weight.py (BUG-2026-04-20-001)
   - tests/regression_engine_batch_recalc.py
   - tools/assert_validator_no_update.py
4. sold_table UNIQUE index migration (D-001)
5. Cache log improvement (E2-A)
6. run_claude.bat 1줄 fix (A)
7. dashboard bare except 2줄 fix (A)

### 4-B: Dashboard thread race (Team B lead, Team A observability)
- Instrument dashboard_tab.py thread ID + timing (12줄 Plan B)
- After observability: assess whether root.after() migration needed

### 4-C: reserve_from_allocation 465줄 분해 (Team D)
- REQUIRES Master approval (>40 lines change)
- Plan: _ra_validate_lot_availability + _ra_select_and_reserve_tonbags + _ra_record_allocation_plan
- Must pass GPT_verify_outbound_refactor invariant proof before merge

### 4-D: pytest infrastructure (Team E)
- 4개 fixture DB 생성
- conftest.py + 5개 test module
- Target: ≥10 tests covering Phase 3 fixes

### 4-E: Integration review + version bump
- Run 02_INTEGRATION_REVIEW_V3.md 7-step review
- Bump version to v8.7.2

## Gate Status (post-diagnostic, pre-patch)

| Gate | Status | Note |
|---|---|---|
| Pre-gate (bug-chain docs) | PENDING | 4-A 패치 전 작성 필요 |
| Compile gate | NOT RUN | 현재 코드베이스 기준 확인 필요 |
| Test gate | FAIL | pytest 0건 |
| Scenario gate | PARTIAL | Phase 3 smoke 대기 중 |
| Rollback gate | PASS | _phase1_backup_20260420/ 존재 |

## Cross-Team Conflict Map
- E4-A + D-002: 동일 파일 db_migration_mixin.py — Team D+E 공동 패치, Master 조율
- D-001 (sold_table): Team D 논리 + Team E 마이그레이션 — 순서: E가 migration 작성, D가 INSERT OR IGNORE 추가
