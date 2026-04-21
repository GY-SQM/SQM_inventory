# Phase 4-C Invariant Check — Team D

Date: 2026-04-20
File: engine_modules/inventory_modular/outbound_mixin.py

## Line Count

| Function | Before | After |
|---|---|---|
| reserve_from_allocation | lines 1703-2168 = 466 lines | lines 1981-2247 = 267 lines |
| Loop body (for line_no, alloc in ...) | ~155 inline lines | ~154 lines (helpers called) |

## New Helper Methods Added

| Helper | Lines | Purpose |
|---|---|---|
| `_ra_validate_lot_availability` | 1703-1785 (83 lines) | LOT header check + G2 MXBG check + status check |
| `_ra_fetch_tonbag_pool` | 1787-1881 (95 lines) | Tonbag fetch + location warning + no-tonbag diagnosis |
| `_ra_execute_lot_reservation` | 1883-1977 (95 lines) | STAGED path + LOT mode + TONBAG mode reservation |

## Invariant Checks

### _recalc_current_weight
- Status: NOT CALLED in reserve_from_allocation (correct — this function only reserves, does not pick/confirm)
- All existing _recalc_current_weight call sites in outbound_mixin.py are preserved unchanged (lines 764, 765, 791, 792, 932, 933, 1068, 1069, 2477, 2478, 3024, 3025, 3700, 3701, 3782, 3783, 3890, 3891, 3985, 3986)
- None of these are inside the new helpers — PASS

### SAMPLE_WEIGHT_KG
- Status: outbound_mixin.py has ZERO occurrences of SAMPLE_WEIGHT_KG (was never there)
- The is_sample_req / is_sample=1 tonbag filter logic is preserved exactly in _ra_fetch_tonbag_pool
- PASS

### All existing _ra_* helpers untouched
- _ra_build_result_template, _ra_get_alloc_plan_cols, _ra_alloc_val, _ra_insert_plan_row
- _ra_build_plan_payload, _ra_parse_allocation_line, _ra_validate_line_inputs
- _ra_check_alloc_conflict, _ra_check_lot_dup, _ra_resolve_pick_count
- _ra_record_reservation_result, _ra_log_random_selection, _ra_check_duplicate_file
- _ra_g5_batch_validate, _ra_pre_dup_warnings, _ra_finalize_result
- All 15 existing helpers: UNCHANGED

### Behavior preservation notes
- Helper 1 (_ra_validate_lot_availability): result/strict_errors passed by reference; mutations propagate correctly.
- Helper 2 (_ra_fetch_tonbag_pool): returns list or None; None triggers `continue` in caller exactly as original.
- Helper 3 (_ra_execute_lot_reservation): returns 6-tuple (reserved_in_lot, reserved_kg, selected_sub_lts, seed_hash, plan_line_counter, selected). The `selected` variable (list of tonbag dicts) is passed to _ra_log_random_selection — preserved correctly.
- STAGED path: helper sets pending_approval and returns; caller checks `need_approval and has_workflow_status_col` and issues `continue` — same behavior as original inline `continue`.
- ctx dict augmented with `_weight_kg` and `_risk_flags` keys before helper call; these are read by helper via ctx.get() with safe defaults.
- No new imports added.

## py_compile Results

- engine_modules/inventory_modular/outbound_mixin.py: PASS
- engine_modules/inventory_modular/engine.py: PASS
