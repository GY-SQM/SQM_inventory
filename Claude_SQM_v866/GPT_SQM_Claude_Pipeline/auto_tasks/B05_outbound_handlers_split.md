Read COMMON_RULES.md and follow it strictly.

BATCH ID: B05
PURPOSE:
Refactor outbound_handlers.py into smaller, safer orchestration functions without changing public behavior.

PRIMARY TARGET FILE:
- gui_app_modular/handlers/outbound_handlers.py

TASKS:
1. Identify all methods longer than 80 lines.
2. Extract helper methods using _oh_ prefix.
3. Separate UI callback wiring from business branching where possible.
4. Preserve public signatures.
5. Avoid cross-file interface changes.
6. Create or update tests:
   - tests/stage_gates/test_b05_outbound_handlers_smoke.py
   - tests/stage_gates/test_b05_public_signature_stable.py

TEST GATES:
- python -m py_compile gui_app_modular/handlers/outbound_handlers.py
- pytest -q tests/stage_gates/test_b05_outbound_handlers_smoke.py
- pytest -q tests/stage_gates/test_b05_public_signature_stable.py

SUCCESS CRITERIA:
- large methods reduced
- public signature preserved
- smoke tests pass
