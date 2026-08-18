# GitHub Branch Protection Setup

Use this after either upgrading GitHub Pro for the private repository or making the repository public.

## Target

- Repository: `GY-SQM/SQM_inventory`
- Protected branch: `main`
- Required status check: `CI / test`
- Workflow source: `.github/workflows/ci.yml` (`SQM CI`)

## Recommended Settings

1. Go to GitHub repository Settings -> Branches.
2. Add a branch protection rule for `main`.
3. Enable `Require a pull request before merging`.
4. Enable `Require status checks to pass before merging`.
5. Select required check: `CI / test`.
6. Enable `Require branches to be up to date before merging`.
7. Enable `Require conversation resolution before merging`.
8. Enable `Do not allow bypassing the above settings` if available for the current plan.
9. Leave force pushes disabled.
10. Leave deletions disabled.

## CLI Verification

```powershell
gh workflow list -R GY-SQM/SQM_inventory
gh pr list -R GY-SQM/SQM_inventory --state open --limit 10
gh api repos/GY-SQM/SQM_inventory/branches/main/protection
```

Expected protection API result after the plan supports the feature: HTTP 200 with required status check contexts including `CI / test`.

## Current State

As of 2026-08-18, `main` branch protection is enabled for this public repository.

Required settings confirmed by API:

- Required status check: `CI / test`
- Require branches to be up to date before merging
- Require pull request reviews: 1 approval
- Dismiss stale reviews
- Require conversation resolution
- Enforce admins
- Force pushes disabled
- Deletions disabled

Emergency direct pushes must be recorded in `docs/verify-report.md` with reason, command evidence, and follow-up audit.
