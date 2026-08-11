# SQM Release and Audit Checklist

> Use before GitHub release, employee deployment, shared ZIP, or external review.

## 1. Version Gate

- [ ] `version.py` version matches release name.
- [ ] Run `python scripts\check_release_version.py --release vX.Y.Z` before creating a GitHub release.
- [ ] Release notes mention user-visible changes and migration risks.
- [ ] Artifact name matches the release version.

## 2. Secret Scan

```powershell
rg -n "api[_-]?key|secret|password|token|Bearer " .
git ls-files | rg "config_local|settings.ini|logs/|data/db/|backup/"
```

- [ ] No hardcoded API keys, passwords, tokens, or bearer strings.
- [ ] Local-only config, DB files, logs, backups, and generated outputs are not committed.

## 3. Dangerous API Scan

```powershell
rg -n "os\.system|shell=True|pickle\.load|yaml\.load|eval\(|exec\(" .
rg -n 'f".*SELECT|% .*SELECT|\.format\(.*SELECT' .
```

- [ ] No unsafe shell execution from user input.
- [ ] No unsafe deserialization.
- [ ] SQL uses parameters or repository helpers.
- [ ] User file paths cannot escape intended directories.

## 4. Data Integrity Gate

- [ ] No test writes to production DB.
- [ ] Allocation/outbound/cancel/confirm operations use transactions.
- [ ] Invariant checked where relevant: `initial_weight = current_weight + picked_weight` within +/- 1kg.
- [ ] Backup exists before destructive or bulk update workflow.

## 5. UI and Workflow Gate

- [ ] No new direct blocking `window.confirm()` calls.
- [ ] Main user flow tested start to finish for changed workflows.
- [ ] Loading, normal, empty, and error states checked for changed screens.

## 6. GitHub Protection Gate

- [ ] Normal changes were made through branch -> PR -> merge, not direct `main` push.
- [ ] `SQM CI / CI / test` passed before merge or release.
- [ ] If branch protection is unavailable, the GitHub plan limitation is recorded in `docs/verify-report.md`.
- [ ] After GitHub Pro upgrade or public conversion, `main` branch protection requires `CI / test`.

## 7. Final Decision

- [ ] PASS: release/share allowed.
- [ ] HOLD: blocking issue found.

Blocking issue:

-
