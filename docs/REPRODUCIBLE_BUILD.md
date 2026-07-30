<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Reproducible Builds

## Overview

ScholarForm AI strives for reproducible builds — the ability for multiple independent parties to rebuild identical bit-for-bit artifacts from source code. This is a requirement for the OpenSSF Best Practices Gold badge and is essential for supply chain security.

## Current Status

### Docker Images

Docker images are built with pinned base images and locked dependency versions:

- **Base images**: Tagged with specific digests for reproducibility.
- **Python dependencies**: Pinned to exact versions in `requirements.txt` and `requirements-render.txt`.
- **npm dependencies**: Locked via `package-lock.json` with integrity hashes.
- **Build context**: CI runs on ephemeral GitHub Actions runners with controlled environments.
- **Multi-arch builds**: Linux/amd64 and Linux/arm64 using Docker Buildx with consistent build flags.

### Hermetic Builds

Builds are hermetic — they do not depend on external network resources beyond declared dependencies:

1. All dependencies are declared in `requirements.txt`, `package.json`, or `Dockerfile`.
2. `pip install` resolves from PyPI with pinned versions.
3. `npm ci` installs from `package-lock.json` with integrity verification.
4. Docker builds use `--no-cache` and pinned base images.

### SLSA Provenance

All Docker images include SLSA Level 3 provenance attestations:

```bash
gh attestation verify ghcr.io/scholarform/backend:1.0.0 --repo rohitkumarnaidu/ScholarFormAI
```

## Reproducibility Verification

To verify a reproducible build locally:

### Docker
```bash
cd backend
docker build -t scholarform-backend:local -f docker/Dockerfile .
```

Compare the image digest with the CI-produced image from ghcr.io.

### Python environment
```bash
cd backend
pip install -r requirements.txt
pip freeze > local-requirements.txt
diff local-requirements.txt requirements.txt
```

## Improvement Roadmap

1. Add build timestamp pinning for fully deterministic Docker builds.
2. Implement build hash comparison in CI between PR and main.
3. Document exact CI runner environment specifications.
4. Add reproducible build verification to the release pipeline.

---

*Last updated: July 2026*
