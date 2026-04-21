# Log Audit — config_logging.py
**Date:** 2026-04-20  
**Team:** Phase 5-A  

## Handlers

| Handler | Type | Level | Target |
|---------|------|-------|--------|
| `console_handler` | `logging.StreamHandler` | `CRITICAL` (pytest) / `INFO` (normal) | `_ORIG_STDOUT` (original stdout, bypasses tee) |
| `file_handler` | `RotatingFileHandler` | `DEBUG` | `logs/sqm_inventory.log` |

## Formatter

Single formatter used by both handlers:
```
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
```
Human-readable text only — no structured/JSON formatter.

## JSONFormatter Present?

**No.** Grep for `JSON|json|jsonl|JsonFormatter` in `config_logging.py` returns zero matches.

## Where is setup_logging() called?

- **`config.py` line 516**: `_logger = setup_logging()` — called at module import time (top-level)
- **`core/config_logging.py`**: re-exports `setup_logging` from root `config_logging`
- **`core/__init__.py` line 9**: imports `setup_logging` for downstream use

## SQM_CAPTURE_STDIO

`_install_stdio_bridge()` reads `os.environ.get("SQM_CAPTURE_STDIO", "1")`.  
- Default: `"1"` (enabled)  
- When enabled: `sys.stdout` → `_StreamTeeToLogger(..., INFO)`, `sys.stderr` → `_StreamTeeToLogger(..., ERROR)`  
- The tee writes to the **original** stream AND logs to the file handler  
- Reentrancy guard via `threading.local()` prevents infinite recursion  
- Disable with `SQM_CAPTURE_STDIO=0`

## Log File Path & Rotation Policy

| Setting | Value |
|---------|-------|
| Path | `<project_root>/logs/sqm_inventory.log` |
| Max file size | 10 MB (`LOG_MAX_SIZE_MB = 10`) |
| Backup count | 5 (`LOG_BACKUP_COUNT = 5`) |
| Encoding | UTF-8 |
| Keep days | 30 (constant defined, not enforced in setup) |

Total log storage: up to ~60 MB (10 MB × 6 files).

## Key Observations for Phase 5-A

1. No JSON handler or formatter exists — clean addition possible
2. `_ORIG_STDOUT` pattern already used to avoid tee recursion — JSONL file handler will follow same safety pattern
3. `_LOG_DIR` is already a `Path` object — easy to derive JSONL filename
4. `os.environ` is already imported — `SQM_JSON_LOG` env var check is trivial
