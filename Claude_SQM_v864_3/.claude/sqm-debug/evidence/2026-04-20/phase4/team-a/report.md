# Team A — Phase 4 Diagnostic Report
Date: 2026-04-20 | Mode: READ-ONLY | Phase: 4 — Regression & Hardening

## A1. Entrypoint Chain

| File | Guard | Status |
|---|---|---|
| run.py | `if __name__ == "__main__"` line 107 | ✓ |
| run_bootstrap.py | utility module, no guard (correct) | ✓ |
| gui_app_modular/__main__.py | `if __name__ == "__main__"` line 16 | ✓ |
| run_claude.bat | hardcoded `F:\프로그램\Sqm 재고관리\Claude_SQM_v862_FULL` line 10 | ⚠️ STALE |

**Finding A-1-1:** run_claude.bat:10 — Korean path + wrong version (v862 not v864). P4 band.

## A2. Startup Sequence — All Required Markers Present

| Marker | Source | Status |
|---|---|---|
| `[ENGINE] primary loaded: SQMInventoryEngineV3 (db=...)` | main_app.py:344-346 | ✓ |
| `[AUTO-RECOVERY] DB 정상` or `자동 복구 실행됨` | main_app.py:146,153 | ✓ |
| `[STARTUP] SQM v... 시작` | main_app.py:607 | ✓ |
| `[STARTUP] 톤백 상태 정합성 OK` | main_app.py:639 | ✓ |

Boot sequence order: run.py:main → run_bootstrap.run_gui → SQMInventoryApp.__init__ → config.setup_logging → engine init → auto-recovery → UI setup → health check (root.after 500ms).

## A3. Runtime Failure Scan

### Finding A-3-1: bare except pass in dashboard_tab.py (×2)
- **File:** gui_app_modular/tabs/dashboard_tab.py:675-676
- **Pattern:** `except Exception: pass` in `_sync_card_colors()`
- **P08:** severity=2, freq=1, blast=1, ease=1 → score=2 → **P5**
- **Risk:** cosmetic only, widget config suppressed silently

### Finding A-3-2: Phase 2 residual check → PASS
- No new `except Exception: pass` or bare `except:` introduced after Phase 2

### Finding A-3-3: Config / env vars → PASS
- All env vars have fallbacks in config.py
- config_logging.py: setup_logging() idempotent (handlers.clear() on re-entry)

## A4. Observability Plan

### Dashboard Thread Race (Phase 4-B target)
Missing in gui_app_modular/tabs/dashboard_tab.py:612-613:
- Thread ID logging (main vs worker thread)
- Lock contention timing
- Worker elapsed time
- Exception stack trace in background thread

**Proposed additions (12 lines, Plan B):**
- Before thread start: `logger.debug(f"[Dashboard] refresh start (main={threading.current_thread().ident})")`
- In `_bg_dispatcher`: thread ID + start time + elapsed on finally

### Phase 3 Fix Regression Markers (Phase 4-A)
| Fix | Regression Guard Status |
|---|---|
| BUG 5001kg drift (crud_mixin.py:194) | ❌ NO guard file |
| Batch recalc (sales_order_engine.py) | ❌ NO guard file |
| SQL injection → safe (database.py) | ✓ spot-check parameterized queries |
| Dashboard thread race | OPEN — Phase 4-B |

### Test Infrastructure Gap
- No `tests/` directory
- No `tests/regression_runtime_*.py`
- GPT_verify_outbound_refactor_v3.py: NOT FOUND (need to verify)

## P08 Priority Summary

| Finding | Band | Score | Action |
|---|---|---|---|
| Dashboard thread observability missing | P2 | ~54 | Phase 4-B instrumentation |
| Regression guards absent (3 Phase-3 fixes) | P3 | ~36 | Phase 4-A backfill |
| run_claude.bat stale path | P4 | 6 | 1-line fix |
| dashboard_tab.py bare except ×2 | P5 | 2 | 2-line fix |

## Recommended Phase 4 Patches (Plan B, <40 lines/file)

1. **Patch A-1** `run_claude.bat:10` — replace hardcoded path with `%~dp0` (1 line)
2. **Patch A-2** `dashboard_tab.py:675-676` — replace `except Exception: pass` with `logger.debug(...)` (2 lines)
3. **Patch A-3** `dashboard_tab.py:612-613` — add thread ID + timing observability (12 lines, Phase 4-B prerequisite)

Gate prerequisite before any patch: P05 checklist + py_compile pass.
