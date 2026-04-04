You are a senior Python architect improving exception handling.

Working directory: F:\프로그램\Sqm 재고관리\Claude_SQM_v865
Target file ONLY: gui_app_modular/dialogs/onestop_inbound.py

RULES — NEVER VIOLATE:
- NO DB schema change
- NO business policy change
- NO public method signature change
- Backup file first: cp file.py file.py.bak_auto
- Run python -m py_compile after EVERY edit
- If py_compile fails → fix immediately
- Do NOT ask questions. Auto-decide everything. Do NOT stop.

ALREADY DONE: 7 data-path exceptions were standardized in previous session.

TASK — Fix remaining ~53 except Exception:

Category 1 — File I/O:
  except Exception → except (OSError, IOError, PermissionError)

Category 2 — JSON:
  except Exception → except (json.JSONDecodeError, KeyError, ValueError)

Category 3 — Template load/save:
  except Exception → except (OSError, json.JSONDecodeError, KeyError)

Category 4 — tkinter widget ops (winfo_exists, config, pack, grid, geometry, destroy):
  KEEP except Exception — tkinter raises unpredictable errors. DO NOT CHANGE THESE.

Category 5 — Import errors:
  except Exception → except (ImportError, AttributeError)

For categories 1-3 and 5:
  - Change except Exception to specific types
  - Where logger.debug exists on recoverable errors, upgrade to logger.warning
  - Do NOT change behavior, only narrow the exception type

After completion, output:
TASK 3 COMPLETE:
- exceptions narrowed: [count]
- kept as Exception (tkinter): [count]
- py_compile: PASS/FAIL
- deferred: [list or none]
