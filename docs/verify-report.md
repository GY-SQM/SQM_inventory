# SQM Verify Report

> Purpose: record executable evidence before saying a change is complete.
> Rule: no PASS without a command and observed output.

## Summary

- Date(KST): 2026-08-11
- Change: v9.0.7.2 release gate and GitHub release readiness
- Scope: version gate script, release checklist, release audit
- Verdict: PASS with existing warnings recorded

## 1. Commands Run

| Step | Command | Result | Evidence |
|---|---|---|---|
| Current version | `Get-Content -Path version.py -TotalCount 30` | PASS | `VERSION = "9.0.7.2"`, `__version__ = "9.0.7.2"` |
| GitHub latest release before update | `gh release list -R GY-SQM/SQM_inventory --limit 10` | PASS | Latest was `v9.0.7` |
| Remote tag check | `git -c safe.directory=H:/program/sqm/SQM_inventory ls-remote --tags origin` | PASS | `v9.0.7.2` was not present before release |
| Release version gate | `python scripts\check_release_version.py --release v9.0.7.2` | PASS | `version.py 9.0.7.2 matches release tag v9.0.7.2; remote tag is free` |
| Python compile | `python -m py_compile scripts\check_release_version.py` | PASS | Exit code 0 |
| Secret scan | `rg -n "api[_-]?key|secret|password|token|Bearer " .` | PASS | Findings are key-handling code, docs, tests, and templates; no literal production secret observed |
| Local-only tracked scan | `git -c safe.directory=H:/program/sqm/SQM_inventory ls-files \| rg "config_local|settings.ini|logs/|data/db/|backup/"` | WARN | `settings.ini.template` is tracked intentionally; no local config/db/log/backup path reported |
| Dangerous API scan | `rg -n "os\.system|shell=True|pickle\.load|yaml\.load|eval\(|exec\(" .` | WARN | Existing references include docs, regex `.exec`, wrapper names, and `sqm-popout.js` indirect eval comment; no new dangerous API added by this change |
| SQL f-string sweep | `rg -n 'f".*SELECT|% .*SELECT|\.format\(.*SELECT' .` | WARN | Existing SQL construction findings; prior audit exists in `docs/audit-f-string-sql-inventory.md`; no SQL changed here |
| UI confirm sweep | `rg -n "window\.confirm\(" .` | WARN | Existing wrapper fallback in `frontend/js/sqm-core.js`; no workflow confirm added here |
| Regression tests | `python -m pytest tests/ -q` | PASS | `688 passed, 1 warning in 42.92s` |

## 2. Functional Checks

| Case | Input/Action | Expected | Actual | PASS/FAIL |
|---|---|---|---|---|
| Version/release match | Release `v9.0.7.2` | `version.py` equals `9.0.7.2` | Match | PASS |
| Duplicate release guard | Remote tag lookup | Release tag is free before creation | Free | PASS |
| Checklist usability | Add version gate command | Release checklist includes direct command | Present | PASS |
| Test suite | Run pytest | No regression failures | 688 passed | PASS |

## 3. UI State Checks

| Screen | Loading | Normal | Empty | Error | Notes |
|---|---|---|---|---|---|
| Changed screens | N/A | N/A | N/A | N/A | Release gate/documentation-only change |

## 4. SWEEP Search

| Pattern | Command | Findings | Action |
|---|---|---|---|
| Version mismatch | `python scripts\check_release_version.py --release v9.0.7.2` | No mismatch | Gate added |
| Direct confirm | `rg -n "window\.confirm\(" .` | Existing wrapper fallback only | Recorded warning |
| Secrets | `rg -n "api[_-]?key|secret|password|token|Bearer " .` | Key-handling code/templates/tests | Recorded, no production secret observed |
| Dangerous APIs | `rg -n "os\.system|shell=True|pickle\.load|yaml\.load|eval\(|exec\(" .` | Existing audited patterns | Recorded warning |

## 5. Encoding Evidence

| File/Data | UTF-8 | UTF-8 BOM | CP949/EUC-KR sample | Result |
|---|---|---|---|---|
| `scripts/check_release_version.py` | UTF-8 | no BOM intended | ASCII-only content | PASS |
| `docs/release-checklist.md` | UTF-8 | no BOM intended | ASCII-only touched line | PASS |
| `docs/verify-report.md` | UTF-8 | no BOM intended | ASCII-only content | PASS |

## 6. Open Risks

- Existing SQL f-string findings remain outside this release-gate change and are documented in `docs/audit-f-string-sql-inventory.md`.
- Existing `window.confirm` fallback remains in `frontend/js/sqm-core.js`; workflows should continue using `sqmConfirmAsync`.
- Pytest emitted one cache permission warning for `.pytest_cache`; tests still passed.

## Final Verdict

- PASS/FAIL: PASS
- Reason: `v9.0.7.2` version gate passed, release tag was free before release, and regression tests passed.
