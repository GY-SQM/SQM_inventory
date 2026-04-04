Read COMMON_RULES.md and follow it strictly.

BATCH ID: B00
PURPOSE:
Prepare the repository for safe staged Claude Code execution.

WORKING DIRECTORY:
Use the current SQM project root.

TASKS:
1. Verify the project root and key files exist:
   - run.py
   - config.py
   - engine_modules/
   - gui_app_modular/
   - data/db/
2. Create report directories if missing:
   - reports/claude_runs/B00
3. Capture environment snapshot:
   - python version
   - git status
   - current branch
4. Create a backup commit before any other batch begins.
5. Create a run manifest file:
   - reports/claude_runs/B00/environment_snapshot.md
6. Do not modify business logic in this batch.
7. Write a concise checklist of what must be true before B01 can start.
8. If required folders are missing, stop and mark FAIL with a clear reason.

TESTS TO RUN:
- python -V
- git status
- basic file existence checks
- python -m py_compile run.py config.py

SUCCESS CRITERIA:
- environment snapshot saved
- backup commit created
- py_compile passed on basic entry files
- B00 status written as PASS

WRITE OR UPDATE:
- reports/claude_runs/B00/environment_snapshot.md
- reports/claude_runs/B00/summary.md
- reports/claude_runs/B00/test_results.txt
- reports/claude_runs/B00/deferred.md
- reports/claude_runs/B00/status.txt
