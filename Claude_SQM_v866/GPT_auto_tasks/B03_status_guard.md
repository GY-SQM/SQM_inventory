Read COMMON_RULES.md and follow it strictly.

BATCH ID: B03
PURPOSE:
Enforce status-flow safety and eliminate new SOLD write-path behavior.

PRIMARY TARGET FILES:
- engine_modules/inventory_modular/outbound_mixin.py
- core/barcode_scan_engine.py
- features/parsers/sales_order_engine.py
- gui_app_modular/tabs/scan_tab.py
- gui_app_modular/handlers/outbound_handlers.py

TASKS:
1. Search all write-paths involving SOLD.
2. Remove or replace any new SOLD write-path usage with OUTBOUND where safe.
3. Preserve read compatibility for legacy SOLD rows.
4. Audit for illegal transitions such as:
   - AVAILABLE -> OUTBOUND direct path
   - OUTBOUND -> PICKED reverse path
5. Strengthen double-outbound protection if missing.
6. Verify quick outbound / scan flow does not bypass integrity guard.
7. Create or update tests:
   - tests/stage_gates/test_b03_status_flow.py
   - tests/stage_gates/test_b03_no_new_sold_write_path.py
   - tests/stage_gates/test_b03_double_outbound_guard.py
8. Add at least one negative test for illegal transition.
9. Do not change legacy read compatibility behavior.

TEST GATES:
- python -m py_compile <all changed files>
- pytest -q tests/stage_gates/test_b03_status_flow.py
- pytest -q tests/stage_gates/test_b03_no_new_sold_write_path.py
- pytest -q tests/stage_gates/test_b03_double_outbound_guard.py

DEBUG LOOP RULE:
Stay inside B03 until pass or FAIL after 3 attempts.

SUCCESS CRITERIA:
- no new SOLD write-path
- status transition tests pass
- double-outbound guard covered
- B03 status written as PASS

WRITE OR UPDATE:
- reports/claude_runs/B03/summary.md
- reports/claude_runs/B03/test_results.txt
- reports/claude_runs/B03/deferred.md
- reports/claude_runs/B03/status.txt
