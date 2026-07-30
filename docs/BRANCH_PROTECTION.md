<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI — Branch Protection Rules

This document defines the required branch protection settings for the `main` and `develop` branches. These rules must be configured in the GitHub repository settings under **Settings > Branches > Add branch protection rule**.

---

## `main` Branch — Production

| Setting | Value |
| --------- | ------- |
| **Require pull request reviews** | ✅ Enabled |
| Required approving reviews | 1 (increases to 2 for backend/security paths) |
| Dismiss stale reviews | ✅ Enabled |
| Require review from Code Owners | ✅ Enabled |
| **Require status checks** | ✅ Enabled |
| Required checks | `backend-ci`, `frontend-ci`, `security`, `commitlint`, `dependency-review`, `codeql/python`, `codeql/javascript-typescript`, `scorecard` |
| **Require branches to be up to date** | ✅ Enabled |
| **Require conversation resolution** | ✅ Enabled |
| **Require signed commits** | ✅ Enabled |
| **Require linear history** | ✅ Enabled |
| **Allow force pushes** | ❌ Disabled |
| **Allow deletions** | ❌ Disabled |
| **Lock branch** | ❌ Disabled |
| **Do not allow bypassing** | ✅ Enabled (even for admins) |

## `develop` Branch — Integration

| Setting | Value |
| --------- | ------- |
| **Require pull request reviews** | ✅ Enabled |
| Required approving reviews | 1 |
| Dismiss stale reviews | ✅ Enabled |
| **Require status checks** | ✅ Enabled |
| Required checks | `backend-ci`, `frontend-ci`, `commitlint` |
| **Require branches to be up to date** | ✅ Enabled |
| **Require conversation resolution** | ✅ Enabled |
| **Allow force pushes** | ❌ Disabled |
| **Allow deletions** | ❌ Disabled |

## `release/*` Branches — Release Candidates

| Setting | Value |
| --------- | ------- |
| **Require pull request reviews** | ✅ Enabled |
| Required approving reviews | 2 |
| **Require status checks** | ✅ Enabled |
| Required checks | `backend-ci`, `frontend-ci`, `security`, `dependency-review` |
| **Require linear history** | ✅ Enabled |

## `hotfix/*` Branches — Emergency Fixes

| Setting | Value |
| --------- | ------- |
| **Require pull request reviews** | ✅ Enabled |
| Required approving reviews | 1 (Core Team lead only) |
| **Require status checks** | ✅ Enabled |
| Required checks | `security`, `dependency-review` |
| **Allow force pushes** | ✅ Enabled (for squashing fix commits) |

---

## Status Check Configuration

The following GitHub Actions workflows must be configured as required status checks:

### For `main` branch:

1. `backend-ci` — Backend lint, type-check, and test suite
2. `frontend-ci` — Frontend ESLint, vitest, and build
3. `security` — Bandit, Trivy, and OWASP Dependency Check
4. `commitlint / pr-title` — Conventional commit validation
5. `commitlint / commits` — Commit message validation
6. `dependency-review / Dependency Review` — License + vulnerability check
7. `CodeQL / Analyze (python)` — Python security analysis
8. `CodeQL / Analyze (javascript-typescript)` — JS/TS security analysis
9. `OpenSSF Scorecard / analysis` — Supply chain security score

### For `develop` branch:

1. `backend-ci`
2. `frontend-ci`
3. `commitlint / pr-title`
4. `commitlint / commits`

---

## Auto-Merge Configuration

Merge settings for Dependabot and Renovate PRs:

| Type | Merge Method | Conditions |
| ------ | ------------- | ------------ |
| Patch dependencies | Squash merge | All checks pass + auto-approved |
| Minor dependencies | Squash merge | All checks pass + 1 approval |
| Major dependencies | Triage merge | Manual review required |
| Security patches | Squash merge | All checks pass + auto-approved |
| Development dependencies | Squash merge | All checks pass + auto-approved |

---

## Enforcement Notes

- Branch protection rules are enforced via GitHub UI (not CODEOWNERS or CI)
- Repository admins cannot bypass `main` protection (`Enforce for admins` must be checked)
- Linear history ensures clean `git log` and easy cherry-pick for hotfixes
- Signed commits provide verifiable authorship (use `git commit -S` with GPG)

---

## Verification

To verify branch protection is active:

```bash
# Check if protected
gh api repos/$OWNER/$REPO/branches/main/protection | jq '.required_status_checks'

# List required checks
gh api repos/$OWNER/$REPO/branches/main/protection/required_status_checks/contexts
```

---

*Last updated: July 2026*
