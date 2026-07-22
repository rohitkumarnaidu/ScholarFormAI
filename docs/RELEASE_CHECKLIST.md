<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Release Checklist — Quick Reference

## How to Create a Release

**Just push a tag — everything is automated:**

```bash
# 1. Ensure CHANGELOG.md and version files are updated
# 2. Tag and push
git tag v1.1.0
git push origin v1.1.0
```

The `create-release.yml` workflow handles the rest.

---

## What the Automation Creates

When you push a `v*` tag, the **release page is automatically populated** with:

### 1. Release Notes
Auto-generated from the GitHub Releases API using conventional commit types.

### 2. Docker Images Section
```bash
docker pull ghcr.io/scholarform/backend:v1.1.0
docker pull ghcr.io/scholarform/celery-worker:v1.1.0
```
Plus `cosign verify` and `gh attestation verify` commands.

### 3. Packages Section
```bash
npm install @scholarform/frontend@1.1.0
pip install scholarform-backend==1.1.0
```

### 4. Release Assets
| Asset | Auto-attached? |
|-------|---------------|
| `release-checksums.txt` | ✅ |
| `backend-sbom.json` | ✅ |
| `frontend-sbom.json` | ✅ |

---

## Post-Release Verification

```bash
# 1. Check release exists
gh release view v1.1.0

# 2. Download and verify assets
gh release download v1.1.0
sha256sum -c release-checksums.txt

# 3. Pull and verify Docker image
docker pull ghcr.io/scholarform/backend:v1.1.0
cosign verify ghcr.io/scholarform/backend:v1.1.0 \
  --certificate-identity-regexp "https://github.com/rohitkumarnaidu/ScholarFormAI.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

# 4. Verify npm package exists
npm view @scholarform/frontend@1.1.0 version

# 5. Check production health
curl -s https://api.scholarform.ai/api/v1/health/live | jq .

# 6. Verify SLSA attestation
gh attestation verify ghcr.io/scholarform/backend:v1.1.0 \
  --repo rohitkumarnaidu/ScholarFormAI
```

---

## Manual Release (Fallback)

If automation fails, create the release manually at:
`https://github.com/rohitkumarnaidu/ScholarFormAI/releases/new`

Use the body template from `RELEASE_PROCESS.md` section 4.1.

---

## Quick Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Workflow didn't trigger | Tag not pushed or wrong format | `git push origin v1.1.0` |
| Release body is empty | GitHub API rate limit | Re-run workflow manually |
| SBOM not attached | SBOM file not found | Ensure `sbom/` directory exists |
| Docker images not in ghcr.io | docker-publish.yml failed | Check workflow logs |
