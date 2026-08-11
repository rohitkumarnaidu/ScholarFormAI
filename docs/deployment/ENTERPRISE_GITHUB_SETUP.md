<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Enterprise GitHub Setup Guide

**ScholarForm AI** — Complete GitHub configuration for enterprise open-source readiness.

---

## Table of Contents

1. [Repository Setup](#1-repository-setup)
2. [GitHub Packages & Container Registry](#2-github-packages--container-registry)
3. [Release Automation](#3-release-automation)
4. [Security & Compliance](#4-security--compliance)
5. [Repository Governance](#5-repository-governance)
6. [Branch Protection & Merge Queues](#6-branch-protection--merge-queues)
7. [Community Standards](#7-community-standards)
8. [Monitoring & Observability](#8-monitoring--observability)
9. [Environment Variables & Secrets](#9-environment-variables--secrets)
10. [Checklists](#10-checklists)

---

## 1. Repository Setup

### 1.1 Repository Metadata

Configure in **Settings > General**:

| Setting | Value |
| --------- | ------- |
| Visibility | Public |
| Description | AI-powered academic manuscript formatter and research document generator |
| Website | `https://scholarform.ai` |
| Topics | `academic-writing`, `manuscript-formatting`, `ai-agent`, `document-processing`, `fastapi`, `nextjs`, `python`, `typescript` |

### 1.2 Repository Features

| Feature | Setting |
| --------- | --------- |
| Issues | ✅ Enabled |
| Discussions | ✅ Enabled (Q&A, General, Ideas, Show and tell) |
| Projects | ✅ Enabled (Beta) |
| Wiki | ❌ Disabled (use `docs/` directory instead) |
| Sponsorships | ✅ Enabled (see FUNDING.yml) |
| Preserve this repository | ❌ Disabled |
| Allow auto-merge | ✅ Enabled |
| Always suggest updating PR branches | ✅ Enabled |
| Allow merge commits | ❌ Disabled |
| Allow squash merging | ✅ Enabled (Default: "Squash and merge") |
| Allow rebase merging | ❌ Disabled |

### 1.3 Repository Topics

Add to repository **About** section for discoverability:

```
scholarform academic-writing manuscript-formatting ai-agent
document-processing fastapi nextjs python typescript
research-tools latex docx pdf-generation nlp
```

---

## 2. GitHub Packages & Container Registry

### 2.1 Package Types

ScholarForm AI publishes three package types:

| Package | Registry | Source | Frequency |
| --------- | ---------- | -------- | ----------- |
| `ghcr.io/scholarform/backend` | GitHub Container Registry | `backend/docker/Dockerfile` | On release + main |
| `ghcr.io/scholarform/celery-worker` | GitHub Container Registry | `backend/docker/Dockerfile` | On release + main |
| `@scholarform/frontend` | GitHub npm Registry | `frontend/` | On release |
| `scholarform-backend` | GitHub PyPI Registry | `backend/` | On release |

### 2.2 Container Registry Configuration

**Required secrets** (Settings > Secrets and variables > Actions):

| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | Auto-available; used for `ghcr.io` authentication |

No additional secrets required — `GITHUB_TOKEN` has `packages: write` permission in the workflow.

### 2.3 Consuming Packages

**Docker:**

```bash
docker pull ghcr.io/scholarform/backend:latest
docker pull ghcr.io/scholarform/backend:1.0.0
docker pull ghcr.io/scholarform/celery-worker:latest
```

**npm (GitHub Packages):**

```bash
echo "@scholarform:registry=https://npm.pkg.github.com" >> .npmrc
npm install @scholarform/frontend
```

**Python (GitHub Packages):**

```bash
pip install scholarform-backend --index-url https://github.com/rohitkumarnaidu/ScholarFormAI
```

### 2.4 Multi-Architecture Support

Images are built for:

| Architecture | Status |
| ------------- | -------- |
| `linux/amd64` | ✅ Supported |
| `linux/arm64` | ✅ Supported |

### 2.5 Image Signing & Attestation

All container images are:

- **Signed** with cosign (keyless, OIDC-based): `cosign verify ghcr.io/scholarform/backend:1.0.0`
- **SBOM attested**: CycloneDX SBOM attached as OCI attestation
- **Provenance attested**: Build provenance via GitHub attestations

```bash
# Verify attestation
gh attestation verify ghcr.io/scholarform/backend:1.0.0 \
  --repo rohitkumarnaidu/ScholarFormAI

# Verify signature
cosign verify ghcr.io/scholarform/backend:1.0.0 \
  --certificate-identity-regexp "https://github.com/rohitkumarnaidu/ScholarFormAI.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

---

## 3. Release Automation

### 3.1 Release Workflow

```
Developer → Conventional Commit → PR → Merge to main → Release Drafter updates draft
                                                                   ↓
                                                        Tag v1.0.0 → Create Release
                                                                       ↓
                                                     Build Docker → Push to ghcr.io
                                                     Publish npm  → GitHub Packages
                                                     Publish PyPI → GitHub Packages
                                                     Generate SBOM → Attach to Release
                                                     SLSA Provenance → Attach to Release
```

### 3.2 Commit Message Format

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, `security`

Valid scopes: `backend`, `frontend`, `pipeline`, `auth`, `api`, `templates`, `docs`, `ci`, `deps`, `release`, `docker`

Examples:

```
feat(backend): add IEEE citation export
fix(frontend): correct dark mode toggle state
docs(api): update endpoint examples for v1.1
security(pipeline): fix SSRF vulnerability in PDF parser
```

### 3.3 Version Resolution

| Commit Type | Version Bump | Example |
| ------------- | ------------- | --------- |
| `feat` + `breaking` label | MAJOR | 1.0.0 → 2.0.0 |
| `feat` | MINOR | 1.0.0 → 1.1.0 |
| `fix` | PATCH | 1.0.0 → 1.0.1 |
| `security` | PATCH | 1.0.0 → 1.0.1 |
| `deps` | PATCH | 1.0.0 → 1.0.1 |
| `docs`, `ci`, `chore` | No release | — |

### 3.4 Release Types

| Release Type | Pre-release Suffix | Example |
| ------------- | ------------------- | --------- |
| Release Candidate | `-rc.N` | `v1.1.0-rc.1` |
| Beta | `-beta.N` | `v1.1.0-beta.1` |
| Alpha | `-alpha.N` | `v1.1.0-alpha.1` |
| Stable | None | `v1.1.0` |

### 3.5 Release Artifacts

Every GitHub Release includes:

- Release notes (auto-generated via Release Drafter)
- Checksums (SHA256) of all artifacts
- SBOM (CycloneDX JSON) for backend dependencies
- SBOM (CycloneDX JSON) for frontend dependencies
- SLSA provenance attestation (intoto JSON)
- Docker image digests
- Full changelog link

---

## 4. Security & Compliance

### 4.1 GitHub Security Features

| Feature | Status | Description |
| --------- | -------- | ------------- |
| Dependabot alerts | ✅ Enabled | Automated vulnerability alerts |
| Dependabot security updates | ✅ Enabled | Auto-PR for vulnerable dependencies |
| Secret scanning | ✅ Enabled | Push protection for secrets |
| Code scanning (CodeQL) | ✅ Enabled | Python + JavaScript analysis |
| OpenSSF Scorecard | ✅ Enabled | Supply chain security score |
| Dependency review | ✅ Enabled | License + vulnerability check on PRs |
| SLSA provenance | ✅ Enabled | Build integrity attestation |
| CVE advisory workflow | ✅ Enabled | Auto-create issues from Dependabot alerts |

### 4.2 Required Secrets

| Secret | Where | Used By |
| -------- | ------- | --------- |
| `GITHUB_TOKEN` | Auto (repo) | All workflows |
| `SCORECARD_GIST_ID` | Actions secrets | Scorecard badge (optional) |
| `GIST_SECRET` | Actions secrets | Badge update (optional) |
| `PYPI_TOKEN` | Actions secrets | PyPI publish (optional) |
| `RENDER_API_KEY` | Actions secrets | Render deployment |
| `RENDER_PROD_SERVICE_ID` | Actions secrets | Render deployment |
| `RENDER_PROD_DEPLOY_HOOK_URL` | Actions secrets | Render deployment |
| `PROD_BACKEND_URL` | Actions secrets | Health checks |
| `DATABASE_URL` | Actions secrets | DB migrations |
| `VERCEL_TOKEN` | Actions secrets | Vercel deployment |
| `VERCEL_ORG_ID` | Actions secrets | Vercel deployment |
| `VERCEL_PROD_PROJECT_ID` | Actions secrets | Vercel deployment |

### 4.3 OpenSSF Scorecard Badge

After the Scorecard workflow runs, a badge can be displayed in the README:

```markdown
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/rohitkumarnaidu/ScholarFormAI/badge)](https://securityscorecards.dev/viewer/?uri=github.com/rohitkumarnaidu/ScholarFormAI)
```

Scorecard evaluates:

- Binary artifacts, branch protection, CI tests, CII Best Practices
- Code review, contributors, dangerous workflow, dependency update tools
- Dependency review, fuzzing, license, maintained, packaging
- Pinned dependencies, SAST, security policy, signed releases, token permissions
- Vulnerabilities, webhooks

### 4.4 SLSA Level Targets

| Level | Current | Target | Requirements |
| ------- | --------- | -------- | ------------- |
| SLSA 1 | ✅ | — | Provenance exists |
| SLSA 2 | ✅ | — | Signed provenance |
| SLSA 3 | ✅ | Q3 2026 | Hermetic, isolated builds |

### 4.5 Security Response SLA

| Severity | Response | Fix | Public Disclosure |
| ---------- | ---------- | ----- | ------------------- |
| Critical | 24h | 7 days | 60 days |
| High | 48h | 14 days | 60 days |
| Medium | 72h | 30 days | 90 days |
| Low | 1 week | 90 days | 120 days |

---

## 5. Repository Governance

### 5.1 Label Taxonomy

| Category | Labels | Description |
| ---------- | -------- | ------------- |
| **Type** | `bug`, `feature`, `enhancement`, `documentation`, `security` | Issue type |
| **Status** | `stale`, `pinned`, `blocked`, `needs-triage`, `in-progress` | Workflow state |
| **Priority** | `priority-critical`, `priority-high`, `priority-medium`, `priority-low` | Severity |
| **Scope** | `backend`, `frontend`, `pipeline`, `api`, `ci-cd`, `docker`, `dependencies` | Affected area |
| **Size** | `size-small`, `size-medium`, `size-large` | PR size (auto-labeled) |
| **Release** | `breaking`, `skip-changelog` | Release drafter categories |

### 5.2 Issue Templates

Configured in `.github/ISSUE_TEMPLATE/`:

- `bug_report.md` — Structured bug report with environment + reproduction
- `feature_request.md` — Feature proposal with motivation + acceptance criteria

### 5.3 Pull Request Template

Configured in `.github/PULL_REQUEST_TEMPLATE.md`:

- Checklist for testing, documentation, changelog
- Conventional commit enforcement
- Auto-assigned reviewers via CODEOWNERS

### 5.4 CODEOWNERS

File `.github/CODEOWNERS` defines ownership:

| Pattern | Owner |
| --------- | ------- |
| `*` | `@rohitkumarnaidu` |
| `/backend/` | `@rohitkumarnaidu` |
| `/frontend/` | `@rohitkumarnaidu` |
| `/.github/` | `@rohitkumarnaidu` |
| `/docs/` | `@rohitkumarnaidu` |
| `/SECURITY.md` | `@rohitkumarnaidu` |

### 5.5 Stale Management

Configured in `.github/workflows/stale.yml`:

| Item | Stale After | Close After | Exemptions |
| ------ | ------------ | ------------- | ------------ |
| Issues | 60 days | 14 days | `security`, `bug`, `enhancement`, `roadmap`, `pinned`, `priority-critical`, `priority-high` |
| PRs | 30 days | 14 days | `security`, `dependencies`, `pinned`, `priority-critical` |

---

## 6. Branch Protection & Merge Queues

### 6.1 Branch Protection Rules

See [BRANCH_PROTECTION.md](../BRANCH_PROTECTION.md) for full configuration.

### 6.2 Required Status Checks

| Status Check | Backend CI | Frontend CI | Security | Commitlint | Dependabot | CodeQL | Scorecard | Dep Review |
| ------------- | :-----------: | :------------: | :--------: | :-----------: | :----------: | :------: | :---------: | :----------: |
| `main` | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| `develop` | ✅ | ✅ | — | ✅ | — | — | — | — |
| `release/*` | ✅ | ✅ | ✅ | — | — | — | — | ✅ |
| `hotfix/*` | — | — | ✅ | — | — | — | — | ✅ |

### 6.3 Merge Queue

The merge queue validates all required checks before allowing a PR to merge:

```yaml
# .github/workflows/merge-queue.yml
on:
  merge_group:
    types: [checks_requested]
```

Required for `main` branch merges.

### 6.4 Auto-Merge Policy

| PR Type | Auto-Merge | Method | Conditions |
| --------- | :----------: | -------- | ------------ |
| Dependabot patch | ✅ | Squash | All checks pass |
| Dependabot minor | ✅ | Squash | All checks pass |
| Renovate patch | ✅ | Squash | All checks pass |
| Security patches | ✅ | Squash | All checks pass |
| Regular PRs | ❌ Manual | Squash | 1 review + all checks |

---

## 7. Community Standards

### 7.1 Community Profile Checklist

GitHub displays a community profile checklist. Ensure these files exist:

| File | Status | Location |
| ------ | -------- | ---------- |
| README.md | ✅ | Root |
| LICENSE | ✅ | Root (MIT) |
| CONTRIBUTING.md | ✅ | Root |
| CODE_OF_CONDUCT.md | ✅ | Root (Contributor Covenant v2) |
| SECURITY.md | ✅ | Root |
| SUPPORT.md | ✅ | Root |
| FUNDING.yml | ✅ | `.github/FUNDING.yml` |
| Issue templates | ✅ | `.github/ISSUE_TEMPLATE/` |
| Pull request template | ✅ | `PULL_REQUEST_TEMPLATE.md` |

### 7.2 Discussion Categories

| Category | Description |
| ---------- | ------------- |
| Q&A | Questions about using ScholarForm AI |
| General | General discussion, announcements |
| Ideas | Feature proposals and ideas |
| Show and tell | Showcase work created with ScholarForm |

### 7.3 Governance

- **Model**: BDFL + Core Team
- **RFC Process**: Required for breaking changes, new features
- **Roles**: BDFL, Core Team, Committers, Contributors
- See [GOVERNANCE.md](../../GOVERNANCE.md) for details.

---

## 8. Monitoring & Observability

### 8.1 GitHub Health Metrics

| Metric | Tool | Frequency |
| -------- | ------ | ----------- |
| OpenSSF Scorecard | Scorecard workflow | Weekly |
| Dependabot alerts | GitHub UI | Real-time |
| Code scanning alerts | CodeQL | On push |
| Secret scanning alerts | GitHub UI | Real-time |
| Repository traffic | GitHub Insights | Daily |
| Community activity | GitHub Pulse | Weekly |

### 8.2 CI/CD Dashboard

Monitor at: `https://github.com/rohitkumarnaidu/ScholarFormAI/actions`

Key workflows to watch:

1. `backend-ci` — Failing tests signal regression
2. `security` — New vulnerabilities
3. `scorecard` — Supply chain health
4. `stale` — Issue queue health
5. `dependency-review` — License compliance

### 8.3 Release Dashboard

Track releases at: `https://github.com/rohitkumarnaidu/ScholarFormAI/releases`

---

## 9. Environment Variables & Secrets

### 9.1 Environments

| Environment | Branch | Protection Rules | Deploy Workflow |
| ------------- | -------- | ----------------- | ----------------- |
| Production | main | CI gates required | `deploy-production.yml` |
| Staging | develop | CI gates required | `deploy-staging.yml` |

### 9.2 GitHub Environments

Configure in **Settings > Environments**:

#### Production Environment

| Setting | Value |
| --------- | ------- |
| Required reviewers | @rohitkumarnaidu |
| Wait timer | 0 minutes |
| Deployment branches | `main` |
| Secret: `RENDER_API_KEY` | ✅ |
| Secret: `RENDER_PROD_SERVICE_ID` | ✅ |
| Secret: `RENDER_PROD_DEPLOY_HOOK_URL` | ✅ |
| Secret: `PROD_BACKEND_URL` | ✅ |
| Secret: `VERCEL_TOKEN` | ✅ |
| Secret: `VERCEL_ORG_ID` | ✅ |
| Secret: `VERCEL_PROD_PROJECT_ID` | ✅ |

#### Staging Environment

| Setting | Value |
| --------- | ------- |
| Deployment branches | `develop` |
| Secret: `RENDER_API_KEY` | ✅ |
| Secret: `RENDER_STAGING_SERVICE_ID` | ✅ |
| Secret: `STAGING_BACKEND_URL` | ✅ |

---

## 10. Checklists

### 10.1 Pre-Launch Checklist

| Task | Status | Verified By |
| ------ | -------- | ------------- |
| Branch protection rules configured | ☐ | |
| Required status checks enabled | ☐ | |
| Merge queue enabled | ☐ | |
| Dependabot alerts enabled | ☐ | |
| Secret scanning enabled | ☐ | |
| Code scanning (CodeQL) configured | ☐ | |
| Scorecard workflow passing | ☐ | |
| All CI/CD workflows passing | ☐ | |
| GitHub Packages publishable | ☐ | |
| Release Drafter working | ☐ | |
| Community profile 100% | ☐ | |
| Repository metadata complete | ☐ | |
| CODEOWNERS file correct | ☐ | |
| Environment secrets configured | ☐ | |

### 10.2 Release Checklist

| Task | Responsibility |
| ------ | --------------- |
| Verify all CI passes on release branch | Release Manager |
| Update CHANGELOG.md | Release Manager |
| Update CITATION.cff version | Release Manager |
| Tag release candidate (`vX.Y.Z-rc.1`) | Release Manager |
| Deploy RC to staging | CI/CD |
| Run full E2E suite against staging | QA |
| 48-hour testing window | Community |
| Tag stable release (`vX.Y.Z`) | Release Manager |
| Verify Docker images published | CI/CD |
| Verify npm/PyPI packages published | CI/CD |
| Verify release assets attached | Release Manager |
| Post-deploy monitoring (1 hour) | On-call |

### 10.3 Post-Incident Checklist

| Task | Owner |
| ------ | ------- |
| Create GitHub Advisory (if vulnerability) | Security Team |
| Backport fix to supported versions | Release Manager |
| Update CHANGELOG with security entry | Release Manager |
| Write postmortem | Incident Lead |
| Update runbooks if needed | Incident Lead |
| Close advisory after fix is deployed | Security Team |

---

## Appendix: Workflow Summary

| Workflow | Trigger | Purpose | New/Existing |
| ---------- | --------- | --------- | :------------: |
| `backend-ci.yml` | Push/PR to main | Backend lint, type, test | Existing |
| `frontend-ci.yml` | Push/PR to main | Frontend lint, test, build | Existing |
| `security.yml` | PR/schedule | SAST, dependency scanning | Existing |
| `deploy-production.yml` | Manual dispatch | Production deployment | Existing |
| `deploy-staging.yml` | Push to develop | Staging deployment | Existing |
| `e2e-production.yml` | Manual dispatch | E2E against production | Existing |
| `e2e-staging.yml` | Scheduled | E2E against staging | Existing |
| `docs-freshness.yml` | Schedule | Documentation staleness check | Existing |
| `sbom.yml` | Push/schedule | SBOM generation | Existing |
| `dependency-review.yml` | PR to main | License + vulnerability review | Existing |
| `keepalive-free-tier.yml` | Schedule | Render free-tier keepalive | Existing |
| **`docker-publish.yml`** | Push/tag/release | Multi-arch Docker to ghcr.io | **New** |
| **`npm-publish.yml`** | Release | npm to GitHub Packages | **New** |
| **`python-publish.yml`** | Release | PyPI to GitHub Packages | **New** |
| **`release-drafter.yml`** | Push/PR to main | Auto-draft release notes | **New** |
| **`create-release.yml`** | Tag push (`v*`) | Full release with artifacts | **New** |
| **`commitlint.yml`** | PR | Conventional commit validation | **New** |
| **`scorecard.yml`** | Schedule/push | OpenSSF Scorecard | **New** |
| **`codeql.yml`** | Push/PR/schedule | CodeQL analysis | **New** |
| **`slsa-provenance.yml`** | Release | SLSA provenance attestation | **New** |
| **`cve-advisory.yml`** | Dependabot/schedule | Auto-create CVE issues | **New** |
| **`stale.yml`** | Schedule | Stale issue/PR management | **New** |
| **`labeler.yml`** | PR | Auto-label by changed files | **New** |
| **`merge-queue.yml`** | Merge group | Merge queue CI validation | **New** |

**Total: 24 workflows** (13 existing + 11 new)

---

*Last updated: July 2026*
