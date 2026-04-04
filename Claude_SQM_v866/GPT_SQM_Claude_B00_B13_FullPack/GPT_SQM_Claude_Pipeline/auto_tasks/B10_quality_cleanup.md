Read COMMON_RULES.md and follow it strictly.

BATCH ID: B10
PURPOSE:
Improve maintainability by cleaning dead-code candidates, bare except blocks, and import hygiene.

TASKS:
1. Search all bare except / silent pass patterns.
2. Remove or logify them where safe.
3. Detect unused imports and remove safe cases.
4. Detect obviously stale commented-out code blocks.
5. If deletion risk is high, mark DEFERRED instead of deleting.
6. Create or update quality scripts:
   - scripts/quality/check_bare_except.py
   - scripts/quality/check_unused_imports.py
   - scripts/quality/check_large_functions.py

TEST GATES:
- python -m py_compile <all changed files>
- python scripts/quality/check_bare_except.py
- python scripts/quality/check_unused_imports.py
- python scripts/quality/check_large_functions.py

SUCCESS CRITERIA:
- silent-exception count reduced
- import hygiene improved
- quality scripts run successfully
