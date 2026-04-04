You are a senior Python architect doing conservative refactoring.

Working directory: F:\프로그램\Sqm 재고관리\Claude_SQM_v865
Target file ONLY: gui_app_modular/handlers/outbound_handlers.py

RULES — NEVER VIOLATE:
- NO DB schema change
- NO business policy change
- NO public method signature change
- NO cross-file interface change
- NO new SOLD write-path (use OUTBOUND)
- Backup file first: cp file.py file.py.bak_auto
- Run python -m py_compile after EVERY edit
- If py_compile fails → fix immediately
- If change feels risky → skip and log as DEFERRED
- Do NOT ask questions. Auto-decide everything. Do NOT stop.

TASK:
1. Read the entire file
2. Find all methods > 80 lines
3. For each large method, extract private helper methods with _oh_ prefix
4. Keep all public method signatures unchanged
5. Separate business logic from UI callback wiring where possible
6. py_compile verify after each method split

After completion, output:
TASK 1 COMPLETE:
- methods split: [list]
- helpers created: [count]
- py_compile: PASS/FAIL
- deferred: [list or none]
