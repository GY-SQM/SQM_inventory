You are a senior Python architect consolidating duplicate SQL queries.

Working directory: F:\프로그램\Sqm 재고관리\Claude_SQM_v865

RULES — NEVER VIOLATE:
- NO DB schema change
- NO business policy change
- NO public method signature change
- Backup files before modifying: cp file.py file.py.bak_auto
- Run python -m py_compile on EVERY changed file
- If py_compile fails → fix immediately
- If change feels risky → skip and log as DEFERRED
- Do NOT ask questions. Auto-decide everything. Do NOT stop.

TASK:
1. Search for repeated SQL patterns:
   grep -rn "SELECT.*FROM inventory_tonbag.*WHERE.*status" --include="*.py"
   grep -rn "SELECT.*FROM allocation_plan.*WHERE.*status" --include="*.py"
   grep -rn "SELECT.*FROM inventory WHERE lot_no" --include="*.py"

2. Find queries repeated >= 3 times across DIFFERENT files

3. For each duplicate pattern, create a named method in:
   engine_modules/inventory_modular/query_mixin.py
   Use clear method names like:
   - get_tonbags_by_status(lot_no, statuses)
   - get_active_plans_by_lot(lot_no)
   - get_inventory_by_lot(lot_no)

4. Replace duplicate queries with method calls in caller files

5. py_compile verify ALL changed files

IMPORTANT: Only consolidate queries that are truly identical in semantics.
If a query has unique WHERE clauses or JOINs, leave it alone.

After completion, output:
TASK 4 COMPLETE:
- duplicate patterns found: [count]
- methods created in query_mixin: [list]
- files updated: [list]
- py_compile: PASS/FAIL
- deferred: [list or none]
