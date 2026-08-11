# AGENTS.md ? SQM Inventory Agent Rules

> Follow `CLAUDE.md` for project memory and product rules. This file adds Codex/harness operating gates.

## Core Rules

- Do not overwrite user or runtime data.
- Do not commit API keys, database files, logs, backups, generated outputs, or local-only configuration.
- SQM v9 uses `main_webview.py`; do not reintroduce removed legacy entrypoints.
- For UI confirms, avoid direct blocking `window.confirm`; use `sqmConfirmAsync` where workflow confirmation is needed.


## Main Branch Protection

- Do not push directly to `main` for normal code changes.
- Use branch -> PR -> `SQM CI / CI / test` success -> merge.
- After GitHub Pro upgrade or repository public conversion, enable `main` branch protection and require the `CI / test` status check.
- Emergency direct pushes must be documented in `docs/verify-report.md` with reason, commands, and follow-up audit.
## Harness Engineering Gates

1. **VERIFY**: Builder notes are not evidence. Record direct commands, output snippets, and PASS/FAIL in `docs/verify-report.md`.
2. **AUDIT**: Before release or sharing, check secrets, dangerous APIs, input validation, logs, and backups with `docs/release-checklist.md`.
3. **SWEEP**: Search for the same defect pattern with `rg`; record either no additional findings or the fixes made.

Required command examples:

```powershell
rg -n "api[_-]?key|secret|password|token|Bearer " .
rg -n "os\.system|shell=True|pickle\.load|yaml\.load|eval\(|exec\(" .
python -m pytest tests/ -q
```

## Completion Standard

- State exactly what changed.
- State the commands run and their results.
- State known warnings instead of hiding them.
