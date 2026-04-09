# P2-C-01 DB Access Map
작성일: 2026-04-07

## DB 접근 빈도 TOP 파일 (execute/cursor/commit/rollback)

| 파일 | DB 접근 횟수 | SQL문 횟수 | 전환 우선순위 |
|---|---|---|---|
| engine_modules/inventory_modular/outbound_mixin.py | 77 | 140 | **최고** — Batch B 대상 |
| engine_modules/db_migration_mixin.py | 149 | 44 | 낮음 — 마이그레이션 전용 |
| engine_modules/database.py | 42 | 14 | 낮음 — DB 인프라 |
| core/barcode_scan_engine.py | 38 | - | 중간 |
| engine_modules/db_schema_mixin.py | 37 | - | 낮음 — 스키마 전용 |
| features/parsers/sales_order_engine.py | 28 | 32 | 중간 |
| engine_modules/inventory_modular/return_mixin.py | 14 | 31 | 중간 |
| engine_modules/inventory_modular/query_mixin.py | - | 50 | 중간 |
| gui_app_modular/tabs/allocation_tab.py | 15 | 29 | 중간 |
| engine_modules/inventory_modular/tonbag_mixin.py | 11 | 23 | 중간 |
| engine_modules/inventory_modular/crud_mixin.py | 9 | 22 | 중간 |
| engine_modules/inventory_modular/inbound_mixin.py | 8 | 18 | 높음 — Batch A 연계 |
| gui_app_modular/tabs/dashboard_data_mixin.py | 4 | 48 | 중간 — 조회 전용 |
| gui_app_modular/dialogs/onestop_outbound.py | 9 | 14 | 높음 — Batch B 연계 |

## 결론
- outbound_mixin.py가 SQL 140건으로 최다 — Batch B 최우선 대상
- inbound_mixin.py는 Batch A에서 일부 분리 완료
- db_migration/db_schema는 인프라 코드이므로 전환 대상 아님
