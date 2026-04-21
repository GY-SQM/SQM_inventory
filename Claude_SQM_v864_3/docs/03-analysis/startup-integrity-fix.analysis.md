---
feature: startup-integrity-fix
phase: check
matchRate: 100
analyzedAt: 2026-03-31
---

# Gap Analysis: startup-integrity-fix

## Match Rate: 100% (7/7 PASS)

### Plan Items

| # | 항목 | 상태 |
|---|------|:----:|
| P1 | stock_movement duplicate_guard 규칙 제외 | PASS |
| P2 | 위치 미지정 880개 — 코드 수정 불필요 | PASS |
| P3 | 중복 감지 반복 로그 억제 (signature 비교 + early return) | PASS |

### Additional Fixes (code-analyzer 발견)

| # | 항목 | 상태 |
|---|------|:----:|
| FIX-1 | apply_global_tree_style() 인자 누락 제거 | PASS |
| FIX-2 | 마이그레이션 중복 실행 가드 (_migrations_applied + _ensure_ 제거) | PASS |
| FIX-3 | LOT 1126010804 샘플 1kg 자동 보정 | PASS |
| FIX-4 | validators.py 주석 SAMPLE 포함→제외 수정 | PASS |

### 수정 파일

| 파일 | 수정 내용 |
|------|-----------|
| `gui_app_modular/utils/duplicate_guard.py` | stock_movement/sold_table/picking_table 빈 규칙 등록 |
| `gui_app_modular/main_app.py` | signature 반복 억제 + tree_style 잘못된 호출 제거 |
| `engine_modules/db_migration_mixin.py` | _migrations_applied 가드 플래그 |
| `engine_modules/db_schema_mixin.py` | _ensure_ 중복 호출 제거 |
| `engine_modules/validators.py` | 샘플 1kg 자동 보정 + 주석 수정 |

## Remaining Gaps: None
