Read COMMON_RULES.md and follow it strictly.

BATCH ID: B12
PURPOSE:
Prepare safer architecture boundaries for future refactoring without destabilizing the system.

TASKS:
1. Review duplicated domain rules across GUI, handlers, and engine.
2. Identify candidate service boundaries:
   - AllocationService
   - OutboundService
   - PickingService
   - ParseReviewService
3. Review status/sample/weight constants for duplicate definitions.
4. Introduce custom exceptions only if safe and low-risk.
5. Produce a design report, and only perform small safe extractions in this batch.
6. Create or update tests:
   - tests/stage_gates/test_b12_constants_single_source.py
   - tests/stage_gates/test_b12_custom_exceptions_import.py
   - tests/stage_gates/test_b12_service_boundary_smoke.py

TEST GATES:
- python -m py_compile <all changed files>
- pytest -q tests/stage_gates/test_b12_constants_single_source.py
- pytest -q tests/stage_gates/test_b12_custom_exceptions_import.py
- pytest -q tests/stage_gates/test_b12_service_boundary_smoke.py

SUCCESS CRITERIA:
- architecture boundary report created
- only safe, minimal structural extraction performed
- no interface breakage
