# E2E Tests (Playwright)

This directory will hold end-to-end browser tests driven by Playwright.

## Scope

- Drives the rendered frontend (`frontend/index.html`) in a real browser.
- Exercises user flows: clicking menus, filling forms, reading tables.
- Asserts UI parity with v864.2 where applicable.

## Requirements

- `main_webview.py` (or equivalent) must be running and serving the app
  on `http://127.0.0.1:8765`.
- `playwright` and `pytest-playwright` installed (see `requirements-dev.txt`).
- First-time setup: `playwright install chromium`.

## Status

**Empty on purpose.** Populated starting **Phase 4** of the migration
plan. For Phase 0 the only artifact here is this README plus
`__init__.py`.

## How to run (future)

```bat
pytest tests\e2e\ -v --browser chromium
```
