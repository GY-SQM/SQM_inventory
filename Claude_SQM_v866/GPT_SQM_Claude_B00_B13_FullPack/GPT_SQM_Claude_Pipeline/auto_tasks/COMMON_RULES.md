You are working on the SQM warehouse management project.

ABSOLUTE GOAL:
Make safe, incremental improvements without breaking inventory integrity, status rules, or production workflows.

DO NOT PROCEED TO THE NEXT BATCH AUTOMATICALLY.

At the end of this batch:
1. create or update stage-specific test scripts,
2. run them,
3. if tests fail, debug and fix within the same batch,
4. re-run tests,
5. only mark PASS when all required gates pass,
6. if unresolved after 3 fix attempts, mark FAIL and DEFERRED,
7. do not start the next batch.

ABSOLUTE RULES:
- NO DB schema change
- NO business policy change
- NO public method signature change
- Never modify data/db/sqm_inventory.db directly
- Keep SOLD read compatibility, but do not create new SOLD write-path
- Preserve status flow: AVAILABLE -> RESERVED -> PICKED -> OUTBOUND
- Preserve sample policy: sample tonbag (S00 / sample markers) must not be treated like normal outbound tonbags unless existing policy explicitly requires it
- Preserve integrity law: prevent partial commit / broken rollback
- Always backup each changed file before editing
- After EVERY edit, run py_compile on changed files
- At the end of the batch, run the required gate tests
- If ambiguity can alter DB semantics, skip and mark DEFERRED

TEST RULES:
- Tests must verify business invariants, not just superficial execution
- Add at least one negative test and one regression test per batch if applicable
- Keep tests deterministic and small
- Avoid mocking away critical DB/state behavior unless absolutely necessary

OUTPUT FORMAT AT END OF BATCH:
BXX COMPLETE
- files modified:
- key changes:
- tests created/updated:
- tests run:
- py_compile:
- result: PASS or FAIL
- deferred:
- next recommended batch:

ALSO WRITE THESE FILES:
- reports/claude_runs/BXX/summary.md
- reports/claude_runs/BXX/test_results.txt
- reports/claude_runs/BXX/deferred.md
- reports/claude_runs/BXX/status.txt   (PASS or FAIL)
