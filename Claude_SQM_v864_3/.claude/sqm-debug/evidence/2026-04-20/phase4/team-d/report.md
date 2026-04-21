# Team D — Phase 4 Diagnostic Report
Date: 2026-04-20 | Mode: READ-ONLY | Phase: 4 — Regression & Hardening

## D1. State Transition Map

**Tonbag States:**
AVAILABLE → RESERVED (outbound_mixin.py:2111-2116, reserve_from_allocation)
RESERVED → PICKED (execute_reserved, apply_approved_allocations)
PICKED → OUTBOUND (confirm_outbound:2946)
OUTBOUND → SOLD (sales_order_engine sold_table insert)
Reverse: SOLD→PICKED (revert_sold_to_picked:3813), PICKED→RESERVED (revert_picked_to_reserved:3704)
Cancel: Any→AVAILABLE (cancel_outbound_tonbag:846, cancel_outbound_bulk:1068)

**Allocation States:**
RESERVED → STAGED → PENDING_APPROVAL → APPROVED → PICKED → CANCELLED

**Side effects per transition:** Every path calls _recalc_current_weight() — CONFIRMED ✓

## D2. Integrity Risk Audit

### D-001: sold_table — No UNIQUE Constraint on (sales_order_no, lot_no, sub_lt)
- **File:** db_migration_mixin.py:727-754 (CREATE TABLE shows no UNIQUE)
- **Risk:** Retry of same SO upload → duplicate SOLD rows → current_weight double-decremented
- **P08:** severity=4, freq=2, blast=3, ease=1 → score=4×2×3×(1/1)=24 → **P4**
  (Master re-scored from Team D's P0 — actual frequency is low, check_duplicate() in import_log mitigates outer retry)
- **Residual Risk:** Within a single batch run if partial failure + immediate re-run, mitigation relies solely on import_log check

### D-002: Weight Floor TRIGGER Not Enforced
- See Team E E4-A — confirmed by Team D
- validators.py:275-279: detects negative current_weight but only logs, no auto-fix unless DEPLETED condition met
- validators.py:498-520: DEPLETED auto-fix only if current_weight<0 AND no positive tonbags
- **P08:** P1 band (score ~110 per Team E)

### D-003: Rollback completeness → SAFE ✓
All major transactions use `with self.db.transaction()` with try-except. No missing rollback branches found.

### D-004: Stale state after cancellation → SAFE ✓
cancel_outbound_tonbag:846 and revert functions call _recalc_current_weight() + set status correctly.

## D3. High-Risk Function Audit

### reserve_from_allocation (outbound_mixin.py:1703-2168) — 465 lines
**6 distinct concerns:**
1. Input validation & normalization (lines 1740-2000)
2. Allocation conflict detection (lines 1812-1883)
3. Tonbag selection & random allocation (lines 1903-2106)
4. Plan row insertion & tracking (lines 2108-2128)
5. Result recording & audit (lines 2130-2140)
6. Phase 3 finalization (line 2166)

**Decomposition Plan (Phase 4-C, Master approval required):**
- `_ra_validate_lot_availability()` — extract lines 1819-1896 (~120 lines)
- `_ra_select_and_reserve_tonbags()` — extract lines 1898-2106 (~180 lines)
- `_ra_record_allocation_plan()` — extract lines 2108-2140 (~80 lines)

**Other 200+ line functions:**
- outbound_mixin.py: gate1_verify_picking (~300L), gate1_apply_picking_result (~150L)

## D4. Phase 3 Guard Cross-Check (MANDATORY)

| Guard | Status | Evidence |
|---|---|---|
| SAMPLE_WEIGHT_KG excluded at inbound | **PASS** | crud_mixin.py:187, inbound_mixin.py:383 |
| Validators do NOT UPDATE inventory.current_weight | **PASS** | validators.py:510 UPDATE only for DEPLETED + immediate _recalc call at line 517 |
| _recalc_current_weight on ALL outbound paths | **PASS** | sales_order_engine.py:416(batch),478(non-batch),838(retry); outbound_mixin.py:932,1068,2946,3622,3704,3812 |
| No status=SOLD bypass of DOUBLE_OUTBOUND_BLOCKED | **PASS** | outbound_mixin.py:2540-2556(_co_check_double_sold), 2656-2678(_co_guard_against_double_outbound) |
| Weight floor enforced | **PARTIAL** | TRIGGER only blocks UPDATE not INSERT; validator detects but limited auto-fix |

**Phase 3 Guard Result: 4/5 PASS, 1 PARTIAL**

## P08 Priority Table

| Issue | Score | Band | Phase 4 Sub |
|---|---|---|---|
| Weight floor TRIGGER incomplete (E4-A + D-002) | ~110 | P1 | 4-A |
| reserve_from_allocation 465L complexity | ~40 | P3 | 4-C (needs Master approval) |
| sold_table no UNIQUE constraint (D-001) | ~24 | P4 | 4-A migration |
| No tests/ directory (E6) | — | Blocker | 4-D |

## Cross-Team Dependencies
- Team E: weight floor CHECK constraint migration (D-002 ↔ E4-A same fix)
- Team A: regression test suite needed for all Phase 3 guards
- Master approval: Phase 4-C reserve_from_allocation refactor (>40 line change)
