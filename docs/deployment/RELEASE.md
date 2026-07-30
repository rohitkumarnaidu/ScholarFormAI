# ScholarForm AI — Release Process

> **Quick reference.** For the full release process with checklists and automation details, see [RELEASE_PROCESS.md](RELEASE_PROCESS.md).

---

## Versioning

Semantic Versioning 2.0.0: `MAJOR.MINOR.PATCH` (e.g., `1.1.0`)

| Component | Meaning |
|-----------|---------|
| MAJOR | Breaking API changes or database migrations |
| MINOR | Backward-compatible features |
| PATCH | Bug fixes |

Pre-release suffixes: `-alpha.N`, `-beta.N`, `-rc.N`

---

## Release Cadence

| Type | Frequency | Example |
|------|-----------|---------|
| Major | ~6 months | 2.0.0 |
| Minor | ~6-8 weeks | 1.1.0 |
| Patch | As needed (hotfix) | 1.0.1 |
| Pre-release | Before major/minor | 1.1.0-rc.1 |

---

## Release Workflow

### 1. Create Release Branch
```bash
git checkout -b release/v1.1.0
```

### 2. Update Changelog & Versions
- Update `CHANGELOG.md` (Keep a Changelog format)
- Update `CITATION.cff` version + date-released
- Bump version in `frontend/package.json`

### 3. Testing Gate
All CI must pass on the release branch:
- Backend: `ruff check app && mypy app && pytest tests -m "not integration and not llm"`
- Frontend: `npm run lint && npm test && npm run build`
- E2E: `npm run test:e2e`

### 4. Release Candidate
```bash
git tag v1.1.0-rc.1
git push origin v1.1.0-rc.1
```
- Deploy RC to staging
- 48-hour testing window

### 5. Final Release
```bash
git tag -s v1.1.0 -m "ScholarForm AI v1.1.0"   # signed tag
git push origin v1.1.0
```

This triggers `create-release.yml` which **automatically**:
1. Generates release notes from conventional commits
2. Creates GitHub Release with SBOM + checksums
3. Builds and signs Docker images (`ghcr.io/scholarform/*`)
4. Publishes npm package (`@scholarform/frontend`)
5. Publishes PyPI package (`scholarform-backend`)
6. Generates SLSA Level 3 provenance

### 6. Deploy
- Trigger `deploy-production.yml` (manual)
- Monitor SLO dashboards for 1 hour

### 7. Post-Release
- Merge release branch to `main`
- Create next milestone in GitHub Issues

---

## Hotfix Process

```bash
git checkout -b hotfix/v1.0.1 v1.0.0
# Apply fix, commit
git tag -s v1.0.1 -m "ScholarForm AI v1.0.1"
git push origin v1.0.1
# Merge back to main
```

---

## Backport Policy

| Type | Backported To |
|------|---------------|
| Security fixes | Last 2 minor versions |
| Critical bugs | Latest minor only |
| Features | Never backported |

---

## Deprecation Policy

| Artifact | Notice Period |
|----------|---------------|
| API endpoints | 2 minor versions |
| Configuration flags | 1 minor version |
| Template contracts | With migration guide |

---

## Quick Commands

```bash
# Verify tag signature
git tag -v v1.1.0

# Verify Docker image
cosign verify ghcr.io/scholarform/backend:v1.1.0 \
  --certificate-identity-regexp "https://github.com/.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

# Verify provenance
gh attestation verify ghcr.io/scholarform/backend:v1.1.0 --repo rohitkumarnaidu/ScholarFormAI

# Verify release integrity
gh release download v1.1.0
sha256sum -c release-checksums.txt
```

---

*Last updated: July 2026*
