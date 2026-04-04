Read COMMON_RULES.md and follow it strictly.

BATCH ID: B02
PURPOSE:
Strengthen transaction safety, rollback behavior, and critical exception coverage.

PRIMARY TARGET FILES:
- engine_modules/database.py
- engine_modules/inventory_modular/outbound_mixin.py

TASKS:
1. Audit transaction context manager behavior in engine_modules/database.py.
2. If rollback coverage is too narrow and partial commit is possible, strengthen rollback behavior safely.
3. Audit outbound-related multi-step operations for BEGIN/COMMIT/ROLLBACK consistency.
4. Expand exception handling only where missing critical DB/IO/integrity failures can cause crash or partial commit.
5. Do not change business rules, status rules, or DB schema.
6. Create or update stage tests under:
   - tests/stage_gates/test_b02_transaction_guard.py
   - tests/stage_gates/test_b02_outbound_rollback.py
7. If needed, create a smoke helper:
   - scripts/smoke/b02_transaction_smoke.py

TEST GATES:
- python -m py_compile <all changed files>
- pytest -q tests/stage_gates/test_b02_transaction_guard.py
- pytest -q tests/stage_gates/test_b02_outbound_rollback.py
- run smoke script if created

DEBUG LOOP RULE:
If tests fail, inspect failure, fix only within this batch scope, re-run.
Maximum 3 fix attempts before FAIL + DEFERRED.

SUCCESS CRITERIA:
- rollback guard improved where needed
- no partial-commit regression introduced
- changed files compile
- stage tests pass

WRITE OR UPDATE:
- reports/claude_runs/B02/summary.md
- reports/claude_runs/B02/test_results.txt
- reports/claude_runs/B02/deferred.md
- reports/claude_runs/B02/status.txt
