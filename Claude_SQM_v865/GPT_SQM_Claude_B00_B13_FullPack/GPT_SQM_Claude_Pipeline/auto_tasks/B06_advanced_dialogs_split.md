Read COMMON_RULES.md and follow it strictly.

BATCH ID: B06
PURPOSE:
Separate dialog orchestration from report-generation logic in advanced_dialogs_mixin.py.

PRIMARY TARGET FILE:
- gui_app_modular/mixins/advanced_dialogs_mixin.py

TASKS:
1. Identify methods longer than 80 lines.
2. Extract helper methods using _adm_ prefix.
3. Keep report policies unchanged.
4. Preserve existing DN/outbound blocking logic for incomplete cases.
5. Create or update tests:
   - tests/stage_gates/test_b06_report_dialog_smoke.py
   - tests/stage_gates/test_b06_dn_guard.py

TEST GATES:
- python -m py_compile gui_app_modular/mixins/advanced_dialogs_mixin.py
- pytest -q tests/stage_gates/test_b06_report_dialog_smoke.py
- pytest -q tests/stage_gates/test_b06_dn_guard.py

SUCCESS CRITERIA:
- large methods reduced
- report flow remains intact
- tests pass
