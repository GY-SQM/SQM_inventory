# JSON Log Schema — Phase 5-A Design
**Date:** 2026-04-20  
**Team:** Phase 5-A  

## Activation

Controlled by environment variable:
```
SQM_JSON_LOG=1   # enable JSON-lines handler
SQM_JSON_LOG=0   # (default) — identical to pre-patch behavior
```

## Output File

```
logs/sqm_jsonl_YYYY-MM-DD.log
```
Example: `logs/sqm_jsonl_2026-04-20.log`

Date is computed once at `setup_logging()` call time using `datetime.date.today()`.

## JSON-Lines Record Schema

Each line is a single valid JSON object (no trailing comma, no wrapping array):

```json
{
  "ts":     "2026-04-20T14:32:01.123456",
  "level":  "INFO",
  "logger": "engine_modules.inventory",
  "msg":    "재고 조회 완료 (42건)",
  "exc":    "Traceback (most recent call last):\n  ..."
}
```

### Fields

| Field | Type | Always Present | Description |
|-------|------|---------------|-------------|
| `ts` | ISO 8601 string | Yes | `datetime.fromtimestamp(record.created).isoformat()` |
| `level` | string | Yes | `record.levelname` e.g. `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"` |
| `logger` | string | Yes | `record.name` — the logger hierarchy name |
| `msg` | string | Yes | `record.getMessage()` — formatted message with `%`-args applied |
| `exc` | string | Only if exception | `self.formatException(record.exc_info)` — full traceback text |

### Design Decisions

1. **No `thread` or `pid` fields by default** — keeps records small; can be added later via `record.thread`
2. **`ensure_ascii=False`** — Korean characters preserved as-is (not `\uXXXX` escaped)
3. **`exc` key only present when exception** — avoids `"exc": null` noise
4. **ISO 8601 from `record.created`** — microsecond precision, local time (consistent with existing log format)

## Handler Spec

```python
RotatingFileHandler(
    filename = _LOG_DIR / f"sqm_jsonl_{date.today()}.log",
    maxBytes = 10 * 1024 * 1024,   # 10 MB — same as human log
    backupCount = 5,
    encoding = "utf-8",
)
level = logging.DEBUG
formatter = _SQMJsonFormatter()
```

## Plan B: Lines Added to config_logging.py

```
_SQMJsonFormatter class   : ~12 lines
_add_json_handler()       : ~12 lines
env-var guard in setup_logging(): 3 lines
─────────────────────────────────
Total                     : ~27 lines  (well under 40-line budget)
```

## Invariants

- `SQM_JSON_LOG` unset or `""` → zero change in behavior
- `SQM_JSON_LOG=0` → zero change in behavior  
- Existing `file_handler` and `console_handler` untouched regardless of flag
- No new third-party dependencies (stdlib: `json`, `datetime`, `logging`, `os`)
