Read COMMON_RULES.md and follow it strictly.

BATCH ID: B04
PURPOSE:
Protect inventory integrity through sample policy enforcement and weight conservation checks.

PRIMARY TARGET FILES:
- engine_modules/inventory_modular/outbound_mixin.py
- engine_modules/inventory_modular/integrity_mixin.py
- engine_modules/inventory_validator.py
- parsers/allocation_parser.py
- parsers/picking_list_parser.py
- related integrity helpers

TASKS:
1. Audit sample handling paths.
2. Ensure sample records are not accidentally treated as normal outbound tonbags unless the documented policy already requires it.
3. Audit weight-conservation logic:
   initial_weight == current_weight + picked_weight (within tolerance if already defined by project rules)
4. Strengthen integrity checks only if safe and within existing rules.
5. Create or update tests:
   - tests/stage_gates/test_b04_sample_exclusion.py
   - tests/stage_gates/test_b04_weight_conservation.py
   - tests/stage_gates/test_b04_integrity_smoke.py
6. If needed, add:
   - scripts/smoke/b04_integrity_smoke.py
7. Add at least one regression test for a previously risky integrity path.
8. Do not proceed to P1 if any integrity gate fails.

TEST GATES:
- python -m py_compile <all changed files>
- pytest -q tests/stage_gates/test_b04_sample_exclusion.py
- pytest -q tests/stage_gates/test_b04_weight_conservation.py
- pytest -q tests/stage_gates/test_b04_integrity_smoke.py

DEBUG LOOP RULE:
Do not go to P1 unless B04 passes.
Maximum 3 fix attempts before FAIL + DEFERRED.

SUCCESS CRITERIA:
- sample-handling regressions blocked
- weight conservation tests pass
- integrity smoke passes
- B04 status written as PASS

WRITE OR UPDATE:
- reports/claude_runs/B04/summary.md
- reports/claude_runs/B04/test_results.txt
- reports/claude_runs/B04/deferred.md
- reports/claude_runs/B04/status.txt
