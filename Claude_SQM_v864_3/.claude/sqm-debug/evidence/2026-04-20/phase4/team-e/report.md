# Team E — Phase 4 Diagnostic Report
Date: 2026-04-20 | Mode: READ-ONLY | Phase: 4 — Regression & Hardening

## E1. Schema Inventory

Core tables confirmed: inventory, inventory_tonbag, shipment, outbound, outbound_item,
outbound_scan, allocation_plan, audit_log, stock_movement, parsing_log,
document_invoice/bl/pl/do (Phase 3 additions), container_info, freetime_info.

**Invariants (source: crud_mixin.py:7)**
1. current_weight = AVAILABLE + RESERVED tonbags (is_sample=0 only)
2. picked_weight = PICKED tonbags (is_sample=0 only)
3. Sample tonbag: sub_lt=0, is_sample=1, weight=1kg per LOT

**Schema delta baseline→current:** Append-only; no destructive ALTER TABLE.  
All migrations idempotent (duplicate-column errors suppressed, continue).

**CRITICAL:** v871 migration attempted weight-floor TRIGGER but SQLite TRIGGER not
actually enforced — negative weights remain possible if validators bypassed.

## E2. Cache & Query-Path Audit (Phase 2.5 deferred)

File: engine_modules/query_cache.py + engine_modules/database.py:661-759

- QueryCache: RLock per line 33, MD5 key, TTL=60s, hit/miss stats
- Hit/miss logic: database.py:669-687 (fetchone), 701-719 (fetchall)
- **Silent double-execution:** cache.get() exception → logger.warning (Phase 2 fix) → fallback to non-cached execute → query runs twice silently
- Visibility: warning level only; no circuit breaker, no startup metric summary

**P08:** severity=3, freq=2, blast=3, ease=2 → score=9×(1/2)≈45 → **P2**

## E3. Parser Partial-Write Audit

**sales_order_engine.py**
- Transaction: db.transaction("IMMEDIATE") line 691 ✓
- _recalc_current_weight() called per LOT (lines 414-418) ✓ (Phase 3-B fix present)
- Issue: sold_table has NO unique constraint on (sales_order_no, lot_no, sub_lt) → retry → duplicate rows possible
- **P08 Score: 28 → P3**

**return_inbound_engine.py**
- Transaction: db.transaction("IMMEDIATE") line 110 ✓
- Early validation before transaction (prefetch pattern, lines 64-69) ✓
- No explicit retry; RuntimeError on failure ✓

**inbound_mixin.py**
- Transaction: db.transaction() line 267 ✓
- Duplicate LOT check pre-transaction (line 201) ✓
- to_dict() at lines 63, 155-156: no try-except; exception propagates (traceback visible, not silent)

## E4. Migration Readiness

- Forward: _run_all_migrations() idempotent, 32+ functions ✓
- Reverse: None — relies on .db file backups (manual restore only) ⚠️
- **P0-5 TRIGGER (v871): weight floor NOT ENFORCED** — CREATE TRIGGER syntax not applied
  - inventory.current_weight can go negative if app-level validator bypassed
  - **P08:** severity=4, freq=2, blast=4, ease=3 → score=32×(1/3)≈110 → **P1 BAND**

## E5. Export/Report Durability

- ExcelWriter: context manager (pd.ExcelWriter __exit__) ✓
- openpyxl.Workbook: explicit save() ✓
- _unique_excel_path() prevents filename collision ✓
- **Risk:** No temp-file→rename pattern; crash mid-save → corrupted .xlsx
- **P08 Score: 32 → P3**

## E6. Test Fixture DB Plan (Phase 4-D BLOCKER)

**Current state:** No tests/ directory. No fixtures. pytest count = 0.

**Required fixture DBs:**
1. `tests/fixtures/inventory_empty.db` — schema only
2. `tests/fixtures/inventory_ten_lots.db` — 10 LOTs + 10 samples
3. `tests/fixtures/inventory_edge_5001.db` — pre-fix state (5001kg drift replay)
4. `tests/fixtures/inventory_post_outbound.db` — outbound state for restore tests

**Loader helpers:** tests/fixtures/__init__.py with create_empty_db(), create_ten_lots_db(), create_edge_5001_db(), create_post_outbound_db()

**Test modules needed:**
- tests/test_schema.py, test_cache.py, test_parsers.py, test_crud.py, test_exports.py, conftest.py

## P08 Priority Summary

| Finding | Score | Band | Action |
|---|---|---|---|
| E4-A: Weight floor trigger not enforced | ~110 | **P1** | Phase 4-A patch (add SQLite trigger) |
| E2-A: Cache double-execution risk | ~45 | P2 | Phase 4 cache visibility fix |
| E5-A: Export no temp-file pattern | ~32 | P3 | Phase 4 write-then-rename |
| E3-A: SO duplicate insert on retry | ~28 | P3 | Add UNIQUE constraint |
| E3-B: to_dict() exception propagation | ~15 | P4 | Add try-except + logger |

## Gate Prerequisites Before Patching
1. Create tests/ + tests/fixtures/ directories
2. Build 4 fixture DBs
3. Run py_compile on changed files
4. Regression test must exist per P13 before any merge
