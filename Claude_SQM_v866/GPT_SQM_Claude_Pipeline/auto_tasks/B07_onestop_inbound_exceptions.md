Read COMMON_RULES.md and follow it strictly.

BATCH ID: B07
PURPOSE:
Reduce silent failure risk in onestop_inbound.py by narrowing exception handling where safe and standardizing logs.

PRIMARY TARGET FILE:
- gui_app_modular/dialogs/onestop_inbound.py

TASKS:
1. Audit all broad exception blocks.
2. Narrow exceptions for file/JSON/template operations where safe.
3. For tkinter widget operations, broad exceptions may remain only if needed, but add clear logging.
4. Replace silent or low-visibility exception handling with warning/error logs as appropriate.
5. Create or update tests:
   - tests/stage_gates/test_b07_inbound_dialog_smoke.py
   - tests/stage_gates/test_b07_exception_logging.py

TEST GATES:
- python -m py_compile gui_app_modular/dialogs/onestop_inbound.py
- pytest -q tests/stage_gates/test_b07_inbound_dialog_smoke.py
- pytest -q tests/stage_gates/test_b07_exception_logging.py

SUCCESS CRITERIA:
- no important silent exception remains in target file
- dialog smoke passes
- logging behavior is improved
