# SQM Verify Report

> Purpose: record executable evidence before saying a change is complete.
> Rule: no PASS without a command and observed output.

## Summary

- Date(KST): 2026-08-11
- Change: v9.0.7.2 release gate, direct confirm removal, GitHub Actions gates, branch protection attempt, PR policy docs, and pytest cache warning removal
- Scope: release gate script, release checklist, release audit, frontend confirm guard, GitHub Actions workflows, GitHub branch protection readiness, pytest cache configuration
- Verdict: PASS with branch protection BLOCKED by GitHub plan limitation

## 1. Commands Run

| Step | Command | Result | Evidence |
|---|---|---|---|
| Current version | `Get-Content -Path version.py -TotalCount 30` | PASS | `VERSION = "9.0.7.2"`, `__version__ = "9.0.7.2"` |
| GitHub release check | `gh release list -R GY-SQM/SQM_inventory --limit 5` | PASS | Latest is `SQM v9.0.7.2` |
| Release tag check | `git -c safe.directory=H:/program/sqm/SQM_inventory ls-remote --tags origin refs/tags/v9.0.7.2` | PASS | Tag points to `74f74b264c474e37e6276eac10c063fae76fd9f4` |
| Release version gate before release | `python scripts\check_release_version.py --release v9.0.7.2` | PASS | `version.py 9.0.7.2 matches release tag v9.0.7.2; remote tag is free` before tag creation |
| Branch protection check | `gh api repos/GY-SQM/SQM_inventory/branches/main/protection` | BLOCKED | GitHub returned `403`: upgrade to GitHub Pro or make repository public to enable this feature |
| Workflow list | `gh workflow list -R GY-SQM/SQM_inventory` | PASS | `SQM Release Gate` active after previous push |
| Python compile | `python -m py_compile scripts\check_release_version.py` | PASS | Exit code 0 |
| JS syntax check | `node --check frontend\js\sqm-core.js` | PASS | Exit code 0 |
| Direct confirm sweep | `rg -n "window\.confirm\(" frontend` | PASS | No matches |
| Confirm usage sweep | `rg -n "window\.confirm\(|sqmConfirm\(" frontend docs AGENTS.md CLAUDE.md` | PASS | Only policy text remains in docs; no frontend direct confirm/fallback remains |
| GitHub Actions workflow scan | `rg -n "release-gate|check_release_version|workflow_dispatch|actions/checkout|setup-python" .github docs scripts` | PASS | `.github/workflows/release-gate.yml` contains manual release gate workflow |
| PR CI workflow inspect | `Get-Content -Path .github\workflows\ci.yml` | PASS | `SQM CI` runs on `pull_request` and `push` to `main`, job name `CI / test`; direct confirm sweep uses `git grep` so GitHub runner does not need `rg` |
| Secret scan | `rg -n "api[_-]?key|secret|password|token|Bearer " .` | PASS | Findings are key-handling code, docs, tests, and templates; no literal production secret observed |
| Local-only tracked scan | `git -c safe.directory=H:/program/sqm/SQM_inventory ls-files \| rg "config_local|settings.ini|logs/|data/db/|backup/"` | WARN | `settings.ini.template` is tracked intentionally; no local config/db/log/backup path reported |
| Dangerous API scan | `rg -n "os\.system|shell=True|pickle\.load|yaml\.load|eval\(|exec\(" .` | WARN | Existing references include docs, regex `.exec`, wrapper names, and `sqm-popout.js` indirect eval comment; no new dangerous API added by this change |
| SQL f-string sweep | `rg -n 'f".*SELECT|% .*SELECT|\.format\(.*SELECT' .` | WARN | Existing SQL construction findings; prior audit exists in `docs/audit-f-string-sql-inventory.md`; no SQL changed here |
| Regression tests | `python -m pytest tests/ -q` | PASS | `688 passed in 24.19s` with pytest cache disabled |

## 2. Functional Checks

| Case | Input/Action | Expected | Actual | PASS/FAIL |
|---|---|---|---|---|
| Version/release match | Release `v9.0.7.2` | GitHub latest equals local version | Latest release is `v9.0.7.2` | PASS |
| Duplicate release guard | Remote tag lookup before release | Release tag is free before creation | Free before creation | PASS |
| Checklist usability | Add version gate command | Release checklist includes direct command | Present | PASS |
| Direct confirm removal | Remove sync fallback | No `window.confirm(` in frontend | No matches | PASS |
| Manual release gate | Add manual workflow | `workflow_dispatch` runs version gate, compile, pytest | Workflow active | PASS |
| PR CI gate | Add push/PR workflow | CI runs compile, JS check, confirm sweep, pytest | Workflow file present | PASS |
| Branch protection | Enable/inspect `main` protection | Protection available | GitHub plan blocks feature | BLOCKED |
| Test suite | Run pytest | No regression failures | 688 passed locally with no cache warning; CI real DB check skips under `GITHUB_ACTIONS=true` | PASS |

## 3. UI State Checks

| Screen | Loading | Normal | Empty | Error | Notes |
|---|---|---|---|---|---|
| Changed screens | N/A | N/A | N/A | N/A | Removed unused sync confirm fallback only; existing async modal remains |

## 4. SWEEP Search

| Pattern | Command | Findings | Action |
|---|---|---|---|
| Version mismatch | `python scripts\check_release_version.py --release v9.0.7.2` | No mismatch before release | Gate added |
| Direct confirm | `rg -n "window\.confirm\(" frontend` | No frontend matches | Fallback removed |
| Release workflow | `rg -n "workflow_dispatch|check_release_version" .github docs scripts` | Found workflow and checklist entries | GitHub Actions connected |
| PR CI workflow | `Get-Content -Path .github\workflows\ci.yml` | Found pull_request/push CI | Ready for branch protection required check `CI / test` |
| Secrets | `rg -n "api[_-]?key|secret|password|token|Bearer " .` | Key-handling code/templates/tests | Recorded, no production secret observed |
| Dangerous APIs | `rg -n "os\.system|shell=True|pickle\.load|yaml\.load|eval\(|exec\(" .` | Existing audited patterns | Recorded warning |

## 5. Encoding Evidence

| File/Data | UTF-8 | UTF-8 BOM | CP949/EUC-KR sample | Result |
|---|---|---|---|---|
| `scripts/check_release_version.py` | UTF-8 | no BOM intended | ASCII-only content | PASS |
| `.github/workflows/release-gate.yml` | UTF-8 | no BOM intended | ASCII-only content | PASS |
| `.github/workflows/ci.yml` | UTF-8 | no BOM intended | ASCII-only content | PASS |
| `pytest.ini` | UTF-8 | no BOM intended | ASCII-only content | PASS |
| `frontend/js/sqm-core.js` | UTF-8 | no BOM intended | Existing Korean text readable | PASS |
| `docs/release-checklist.md` | UTF-8 | no BOM intended | ASCII-only touched line | PASS |
| `AGENTS.md` | UTF-8 | no BOM intended | ASCII-only touched block | PASS |
| `docs/verify-report.md` | UTF-8 | no BOM intended | ASCII-only content | PASS |

## 6. Open Risks

- Branch protection for `main` is blocked by GitHub account/repository plan: private repository requires GitHub Pro or public repository for this feature.
- Existing SQL f-string findings remain outside this release-gate/UI-confirm/CI change and are documented in `docs/audit-f-string-sql-inventory.md`.
- `.pytest_cache` is inaccessible on this PC; pytest cache writes are disabled via `pytest.ini`, removing the warning without changing test assertions.
- The first `SQM CI` push run failed because GitHub Windows runner did not have `rg`; workflow was corrected to use `git grep` instead. The second run confirmed no matches but needed explicit `exit 0` because PowerShell preserved `git grep` no-match exit code 1. The next run reached pytest and exposed a CI-only real DB index check; `test_real_db_has_indexes` now skips on `GITHUB_ACTIONS=true` while local real DB validation remains active.
- The manual release gate should be run before creating the next release tag; `SQM CI` is the PR/push status check candidate for future branch protection.

## Final Verdict

- PASS/FAIL: PASS with branch protection BLOCKED
- Reason: `v9.0.7.2` is the GitHub latest release, direct frontend `window.confirm` is removed, GitHub Actions release and PR CI gates are present, and regression tests passed. `main` branch protection could not be enabled because GitHub returned a plan limitation error.