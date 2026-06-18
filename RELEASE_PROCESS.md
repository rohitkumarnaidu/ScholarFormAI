# ScholarForm AI Release Process

## Versioning

ScholarForm AI follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (1.x.x) — Incompatible API or breaking database migrations
- **MINOR** (x.1.x) — Backward-compatible feature additions
- **PATCH** (x.x.1) — Backward-compatible bug fixes

Pre-release suffixes: `-alpha.N`, `-beta.N`, `-rc.N`.

## Release Cadence

| Release Type | Cadence | Examples |
|-------------|---------|----------|
| Major | ~6 months | 1.0.0, 2.0.0 |
| Minor | ~6-8 weeks | 1.1.0, 1.2.0 |
| Patch | As needed (hotfix) | 1.0.1, 1.0.2 |
| Pre-release | Before each major/minor | 1.1.0-beta.1 |

## Release Manager

Rotating role among Core Team. Responsible for shepherding the release from branch to production.

> **Quick reference:** See [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) for the one-page release checklist.

## Release Workflow

### 1. Branch & Changelog

```bash
git checkout -b release/v1.1.0
```

- Update `CHANGELOG.md` with all changes since last release
- Ensure `CITATION.cff` `version` and `date-released` are current
- Bump version in `backend/pyproject.toml` (if exists) and `frontend/package.json`

### 2. Testing Gate

All CI must pass on the release branch:

- Backend: `ruff check app && mypy app && pytest tests -m "not integration and not llm" -x -q`
- Frontend: `npm run lint && npm test && npm run build`
- E2E: `npm run test:e2e` (full suite, not just critical path)
- Docs freshness: `docs-freshness` workflow (manual trigger)

### 3. Release Candidate

```bash
git tag v1.1.0-rc.1
git push origin v1.1.0-rc.1
```

- Deploy RC to staging environment
- Run full E2E suite against staging
- 48-hour testing window for community feedback
- Fix any regressions and cut new RC if needed

### 4. Final Tag & Release

Tags MUST be cryptographically signed using GPG or SSH signing:

```bash
# Configure GPG signing (one-time)
git config --global user.signingkey <KEY_ID>
git config --global tag.gpgsign true

# Create and push a signed tag
git tag -s v1.1.0 -m "ScholarForm AI v1.1.0"
git push origin v1.1.0
```

All release tags MUST be signed (`git tag -s`). Unsigned tags will be rejected by CI (`create-release.yml` verifies tag signature).

- This triggers `create-release.yml` workflow **automatically**
- The workflow does **everything** — no manual steps needed:

| Step | What Happens | Status |
|------|-------------|--------|
| 1 | Tag pushed → workflow triggered | ✅ |
| 2 | Version verified against `pyproject.toml` + `package.json` | ✅ |
| 3 | Release notes generated via GitHub API (categorized by conventional commits) | ✅ |
| 4 | Full release body built: notes + Docker images + packages + assets + verification | ✅ |
| 5 | GitHub Release created with auto-generated body | ✅ |
| 6 | Checksums generated and attached | ✅ |
| 7 | SBOMs generated and attached (backend + frontend) | ✅ |
| 8 | Docker images built, signed (cosign), and pushed to ghcr.io | ✅ (separate workflow) |
| 9 | npm/PyPI packages published to GitHub Packages | ✅ (separate workflows) |
| 10 | SLSA provenance attestation generated | ✅ |

> **You do not need to edit the release page manually.** The body is auto-generated with:
> - Release notes from merged PRs (via GitHub API + conventional commit categorization)
> - Docker pull commands with cosign verify instructions
> - Package install commands (npm + pip)
> - Release assets table with SHA256 verification
> - Provenance verification commands

### 4.1 GitHub Release Page Contents

When a release is created (auto or manually), include the **following sections and artifacts** on the release page:

#### Release Title Format
```
ScholarForm AI v1.1.0
```

#### Body Template

```markdown
## 📦 ScholarForm AI v1.1.0

### What's Changed
[Auto-generated from Release Drafter — edit for clarity]

### 🚨 Breaking Changes
- [List any breaking changes or say "None in this release"]

### 🚀 Features
- [Key features]

### 🐛 Bug Fixes
- [Key fixes]

### 🔒 Security
- [Security fixes]

### 📖 Full Changelog
[Link to compare view: https://github.com/scholarform/scholarform/compare/v1.0.0...v1.1.0]

---

### 🐳 Docker Images

Pull from GitHub Container Registry:

```bash
# Backend API server
docker pull ghcr.io/scholarform/backend:v1.1.0
docker pull ghcr.io/scholarform/backend:latest

# Celery worker
docker pull ghcr.io/scholarform/celery-worker:v1.1.0
docker pull ghcr.io/scholarform/celery-worker:latest
```

**Verify image signature:**
```bash
cosign verify ghcr.io/scholarform/backend:v1.1.0 \
  --certificate-identity-regexp "https://github.com/scholarform/scholarform.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

**Verify build provenance:**
```bash
gh attestation verify ghcr.io/scholarform/backend:v1.1.0 \
  --repo scholarform/scholarform
```

---

### 📦 Packages

```bash
# npm
npm install @scholarform/frontend@1.1.0

# PyPI
pip install scholarform-backend==1.1.0
```

---

### ✅ Release Assets (attached to this release)

| Asset | Description |
|-------|-------------|
| `release-checksums.txt` | SHA256 checksums of all artifacts |
| `scholarform-sbom-v1.1.0.json` | CycloneDX SBOM (1137+ dependencies) |
| `scholarform.intoto.jsonl` | SLSA Level 3 provenance attestation |

**Verify integrity:**
```bash
# Download the release
gh release download v1.1.0

# Verify checksums
sha256sum -c release-checksums.txt
```

---

### ⬆️ Upgrading

See [MIGRATION_GUIDES.md](MIGRATION_GUIDES.md) for upgrade instructions.

**Quick upgrade:**
1. Pull new Docker images
2. Run database migrations: `alembic upgrade head`
3. Deploy backend + worker
4. Deploy frontend
5. Verify health: `curl https://api.scholarform.ai/api/v1/health/live`
```

#### Release Artifacts Checklist

Before publishing the release, verify these artifacts are **attached** to the release:

| # | Artifact | Source | Auto-attached? |
|---|----------|--------|---------------|
| 1 | `release-checksums.txt` | CI generate | ✅ (create-release.yml) |
| 2 | `scholarform-sbom-v1.1.0.json` | CI generate | ✅ (create-release.yml) |
| 3 | `scholarform.intoto.jsonl` | SLSA workflow | ✅ (slsa-provenance.yml) |
| 4 | Docker image `ghcr.io/scholarform/backend:v1.1.0` | docker-publish.yml | ✅ |
| 5 | Docker image `ghcr.io/scholarform/celery-worker:v1.1.0` | docker-publish.yml | ✅ |
| 6 | npm package `@scholarform/frontend@1.1.0` | npm-publish.yml | ✅ |
| 7 | PyPI package `scholarform-backend==1.1.0` | python-publish.yml | ✅ |
| 8 | SBOM attestation on Docker image | docker-publish.yml | ✅ |
| 9 | Cosign signature on Docker image | docker-publish.yml | ✅ |
| 10 | GitHub attestation on Docker image | docker-publish.yml | ✅ |

#### Pre-release Label

If the release is a **pre-release** (alpha, beta, RC), check **"Set as a pre-release"** on the GitHub Release page:

```
v1.1.0-rc.1  →  Pre-release ✅
v1.1.0       →  Latest release ✅
```

#### Release Notes Auto-generation

Release Drafter automatically drafts release notes on every push to `main`. The draft is available at:

```
https://github.com/scholarform/scholarform/releases
```

When the tag is pushed, `create-release.yml` uses the draft to populate the release body. **Review and edit the draft before publishing** if creating the release manually.

### 5. Deploy

- Production deployment via `deploy-production.yml` workflow (manual trigger)
- Monitor SLO dashboards for 1 hour post-deploy
- If regression detected: trigger rollback (see [Rollback Runbook](docs/runbooks/rollback.md))

### 6. Post-Release

- Create a new `v1.2.0` milestone in GitHub Issues
- Move any unfinished issues from the released milestone
- Update `docs/API.md` if API changes were made
- Update `docs/MIGRATION_GUIDES.md` if migration steps are needed

## Hotfix Process

For critical bugs in production:

1. Branch from the release tag: `git checkout -b hotfix/v1.0.1 v1.0.0`
2. Apply the fix with a single commit
3. Run minimal CI (backend fast tests + frontend lint)
4. Tag and release following step 4-5 above
5. Merge hotfix back to `main`

## Backport Policy

- Security fixes: backported to last 2 minor versions
- Critical bugs: backported to latest minor only
- Features: never backported

## Deprecation Policy

- API endpoints: deprecated for 2 minor versions before removal
- Configuration flags: deprecated for 1 minor version
- Template contracts: deprecated with migration guide

---

*Last updated: June 2026*
