Read COMMON_RULES.md and follow it strictly.

BATCH ID: B11
PURPOSE:
Improve performance in the safest high-impact areas.

TASKS:
1. Detect and fix N+1 query patterns in the current batch scope.
2. Replace per-item Treeview delete with batch delete where safe.
3. Reduce expensive repeated refresh patterns.
4. Add simple performance measurement scripts:
   - scripts/perf/measure_tree_refresh.py
   - scripts/perf/measure_dashboard_load.py
5. Create or update:
   - tests/stage_gates/test_b11_query_count_guard.py

TEST GATES:
- python -m py_compile <all changed files>
- python scripts/perf/measure_tree_refresh.py
- python scripts/perf/measure_dashboard_load.py
- pytest -q tests/stage_gates/test_b11_query_count_guard.py

SUCCESS CRITERIA:
- at least one measurable performance bottleneck improved
- no functional regression in batch scope
