Read COMMON_RULES.md and follow it strictly.

BATCH ID: B13
PURPOSE:
Perform final validation, summarize results, and prepare handoff.

TASKS:
1. Run py_compile on all changed files.
2. Run stage gate tests created across batches.
3. Run broader pytest if practical.
4. Run import smoke:
   - python -c "import run"
5. Run startup/check smoke if available:
   - python run.py --check
6. Create final summary documents:
   - reports/claude_runs/B13/final_summary.md
   - reports/claude_runs/B13/changed_files.md
   - reports/claude_runs/B13/deferred_rollup.md
7. Do not bump version unless explicitly allowed by the user or batch scope says so.

TEST GATES:
- python -m py_compile <all changed files>
- pytest -q tests/stage_gates/
- python -c "import run"
- python run.py --check

SUCCESS CRITERIA:
- final validation completed
- deferred items documented
- handoff documents ready
