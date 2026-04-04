Read COMMON_RULES.md and follow it strictly.

BATCH ID: B09
PURPOSE:
Reduce duplicate GUI refreshes and startup/dashboard blocking behavior.

PRIMARY TARGET FILES:
- gui_app_modular/main_app.py
- gui_app_modular/mixins/refresh_mixin.py
- gui_app_modular/tabs/dashboard_tab.py
- gui_app_modular/tabs/dashboard_data_mixin.py
- related tab refresh logic

TASKS:
1. Audit .after() usage in target files.
2. Identify duplicate or unnecessary deferred refresh calls.
3. Preserve critical UI update paths.
4. Introduce safer refresh coordination only if it does not alter business logic.
5. Add busy cursor / status feedback where appropriate and safe.
6. Create or update tests/scripts:
   - tests/stage_gates/test_b09_dashboard_refresh_smoke.py
   - tests/stage_gates/test_b09_after_storm_guard.py
   - scripts/smoke/b09_startup_smoke.py

TEST GATES:
- python -m py_compile <all changed files>
- pytest -q tests/stage_gates/test_b09_dashboard_refresh_smoke.py
- pytest -q tests/stage_gates/test_b09_after_storm_guard.py
- python scripts/smoke/b09_startup_smoke.py

SUCCESS CRITERIA:
- refresh duplication reduced
- startup/dashboard smoke passes
- no obvious GUI regression introduced
