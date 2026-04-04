Read COMMON_RULES.md and follow it strictly.

BATCH ID: B08
PURPOSE:
Reduce duplicate SQL logic by centralizing repeated queries into canonical methods.

PRIMARY TARGET FILES:
- engine_modules/inventory_modular/query_mixin.py
- repeated query call sites

TASKS:
1. Search repeated SQL patterns involving inventory_tonbag and allocation_plan.
2. Identify queries repeated 3 or more times.
3. Create canonical query helper methods in query_mixin.py.
4. Replace duplicate call sites only where semantics clearly match.
5. Do not change result meaning or DB behavior.
6. Create or update tests:
   - tests/stage_gates/test_b08_query_result_equivalence.py
   - tests/stage_gates/test_b08_query_mixin_smoke.py

TEST GATES:
- python -m py_compile <all changed files>
- pytest -q tests/stage_gates/test_b08_query_result_equivalence.py
- pytest -q tests/stage_gates/test_b08_query_mixin_smoke.py

SUCCESS CRITERIA:
- repeated SQL reduced
- result equivalence preserved
- tests pass
