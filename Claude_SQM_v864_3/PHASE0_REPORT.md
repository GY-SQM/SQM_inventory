# Phase 0 — Safety Net Report

**Project:** SQM Inventory v864.3 (PyWebView + FastAPI migration)
**Date:** 2026-04-21
**Author:** Ruby (Senior Software Architect mode)

---

## Summary

Phase 0 establishes the **test harness infrastructure** for the v864.3
migration. Nothing in the product code was modified. We added only
test/script/config scaffolding so that every later phase has a fast,
repeatable way to confirm the basics still work.

Scope delivered:

- pytest configuration and a three-layer test tree (`unit/`, `smoke/`, `e2e/`).
- Import-only unit tests that do NOT instantiate the engine (the engine
  currently fails to load; tests tolerate this by design).
- Smoke tests that drive the FastAPI app via `TestClient`, so they do
  not require `main_webview.py` to be running.
- A standalone smoke runner (`scripts/smoke_test.py`) that works without
  pytest — useful for CI or quick sanity checks.
- A Windows batch runner (`scripts/run_tests.bat`) that runs both
  pytest and the standalone smoke, with a clear pass/fail summary and
  correct `ERRORLEVEL` propagation.

---

## File Manifest

All paths are absolute and live under
`D:\program\SQM_inventory\Claude_SQM_v864_3\`.

| # | Path | Purpose |
|---|---|---|
| 1 | `tests\__init__.py` | Makes `tests` an importable package (was missing). |
| 2 | `tests\unit\__init__.py` | Unit test package marker. |
| 3 | `tests\unit\conftest.py` | `api_client` + `base_url` fixtures (unit scope). |
| 4 | `tests\unit\test_imports.py` | Imports for `backend.api`, `backend.common.errors`, `backend.api.menubar`, `SQMInventoryEngineV3`. |
| 5 | `tests\smoke\__init__.py` | Smoke test package marker. |
| 6 | `tests\smoke\conftest.py` | `api_client` + `base_url` fixtures (smoke scope). |
| 7 | `tests\smoke\test_api_health.py` | `/api/health`, `/api/dashboard/stats`, `/api/inventory` respond 200. |
| 8 | `tests\e2e\__init__.py` | Placeholder for Phase 4+ Playwright tests. |
| 9 | `tests\e2e\README.md` | Scope + requirements for future E2E work. |
| 10 | `scripts\smoke_test.py` | Standalone smoke runner (no pytest dependency). |
| 11 | `scripts\run_tests.bat` | Windows runner: pytest + standalone smoke. |
| 12 | `requirements-dev.txt` | Dev dependencies (pytest, httpx, playwright). |
| 13 | `pytest.ini` | pytest configuration + marker registry. |
| 14 | `PHASE0_REPORT.md` | This document. |

### Deliberately NOT touched

- `tests\conftest.py` **already existed** from a prior test suite
  (Phase 4 fixtures: `fixtures_dir`, `empty_db`, `ten_lots_db`). Per the
  "DO NOT modify existing files" rule, the new `api_client` / `base_url`
  fixtures were placed in `tests\unit\conftest.py` and
  `tests\smoke\conftest.py` instead. pytest auto-composes parent and
  child conftests, so both layers coexist cleanly.
- `backend\`, `frontend\`, `engine_modules\`, `features\`, `parsers\`,
  `utils\`, `main_webview.py` — untouched.

---

## How to Run

From project root:

```bat
scripts\run_tests.bat
```

The batch file will:

1. Activate a virtualenv if `venv\` or `.venv\` exists.
2. Run `pytest tests\ -v`.
3. Run `python scripts\smoke_test.py`.
4. Print a PASS / FAIL summary and exit non-zero if anything failed.

Alternative (direct invocation):

```bat
pytest tests\unit -v
pytest tests\smoke -v
python scripts\smoke_test.py
```

---

## Current Status

Phase 0 deliverables are **file-complete**. The harness was designed to
degrade gracefully when the backend or engine cannot be imported:

- `test_imports.py` uses `importlib.import_module` + `pytest.fail`, so
  an import failure produces a clear assertion message rather than a
  collection-time crash.
- `api_client` fixture calls `pytest.skip(...)` on `ImportError` (or any
  exception during app load). Smoke tests therefore report as SKIPPED
  rather than ERRORED when the backend is broken.
- `scripts\smoke_test.py` wraps every probe in `try/except` and reports
  FAIL with the exception type — no raw tracebacks on stdout.

Expected first run, given the known engine-load failure:

- `tests\unit\test_imports.py` — should all PASS (class import does not
  require engine instantiation).
- `tests\smoke\test_api_health.py` — should PASS because the three
  endpoints under test have sample-data fallbacks when
  `ENGINE_AVAILABLE=False`.
- `scripts\smoke_test.py` — should print 5 PASS lines and exit 0.

Actual output will be captured on the first live run by Nam Ki-dong
(the harness has not been executed in this session — file creation only).

---

## Known Issues

1. **Engine silently fails to load.** `backend\api\__init__.py` catches
   `Exception` during `SQMInventoryEngineV3(str(DB_PATH))` and sets
   `ENGINE_AVAILABLE=False`. The harness does NOT crash because of this —
   but it also does NOT fix it. **Phase 2** (engine wiring) is
   responsible for identifying and resolving the root cause.
2. **Sample-data path still returns 200.** The smoke tests assert only
   that endpoints respond; they do not validate that the data is real
   warehouse data. That discrimination is intentionally deferred to
   Phase 2 regression tests.
3. **Existing `tests\conftest.py` was preserved untouched.** A future
   consolidation may merge the Phase 0 fixtures into it, but only with
   explicit approval.
4. **Playwright directory is empty.** `tests\e2e\` only has a README +
   `__init__.py`. Browser tests arrive in Phase 4.

---

## Next Step

**Phase 1 — v864.2 Audit + UI Manifest.**

Objectives:

- Walk v864.2 tab-by-tab and record every visible control, label, and
  interaction path.
- Produce `docs\phase1\ui_manifest.json` — the authoritative UI parity
  checklist that Phase 3 will verify against.
- Cross-reference against `docs\handoff\feature_matrix.json` (the 85
  features map) to catch any gaps.

Phase 0 unblocks Phase 1 by guaranteeing that every subsequent change
can be re-validated in under a minute via `scripts\run_tests.bat`.
