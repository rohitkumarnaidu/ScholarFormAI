<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: Dependency Compliance & SBOM
description: License compliance, SBOM generation, dependency audit procedures
sidebar_position: 55
last_updated: July 2026
---

# Dependency Compliance & SBOM

## Overview

ScholarForm AI maintains a comprehensive compliance program for third-party dependencies:

| Activity | Frequency | Tool | Owner |
| ---------- | ----------- | ------ | ------- |
| License inventory | Every commit | `scripts/generate_sbom.py` | DevEx |
| CVE scanning (Python) | Every PR | pip-audit + safety | CI |
| CVE scanning (npm) | Every PR | npm audit | CI |
| SAST (Python) | Every PR | bandit | CI |
| SBOM regeneration | Weekly (Monday) + on dep change | CycloneDX | CI |
| Dependency PRs | Weekly (Monday) | Renovate | Bot |
| License compliance | Continuous | FOSSA | Security |
| DRY run | On-demand | `scripts/audit_deps.py` | Developer |

## Files

| File | Purpose |
| ------ | --------- |
| `THIRD_PARTY_NOTICES.md` | Human-readable license inventory (auto-generated) |
| `sbom/backend-sbom.json` | CycloneDX SBOM for Python deps |
| `sbom/frontend-sbom.json` | CycloneDX SBOM for npm deps |
| `sbom/summary.json` | Aggregate count report |
| `scripts/generate_sbom.py` | SBOM + notices generator |
| `scripts/audit_deps.py` | Local dependency audit CLI |

## Running Locally

```bash
# Full audit (pip-audit + safety + bandit + npm audit)
python scripts/audit_deps.py

# Quick check
python scripts/audit_deps.py --quick

# Regenerate SBOM + notices
python scripts/audit_deps.py --sbom
```

## CI Integration

- **Backend CI**: `lint` job includes bandit; `audit` job runs pip-audit + safety
- **Frontend CI**: `audit` job runs npm audit
- **SBOM workflow**: Runs weekly + on dependency changes, commits updated SBOMs
- **Dependency Review**: Blocks PRs with high-severity dependencies or denied licenses
- **Renovate**: Automated dependency update PRs every Monday

## License Policy

| Classification | Action |
| --------------- | -------- |
| MIT, BSD, Apache-2.0, ISC | ✅ Allowed |
| MPL-2.0, LGPL-3.0 | ️ Review required |
| AGPL-3.0, GPL-3.0 | ❌ Denied for direct deps; allowed for replaceable components (PyMuPDF, GROBID) |
| Unknown / Proprietary | ❌ Blocked by CI |

## AGPL/GPL Usage

The following AGPL-3.0/GPL-3.0 licensed components are used and must be replaced for proprietary deployments:

- **PyMuPDF (fitz)** — AGPL-3.0 (fallback: `pypdf` / `pypdfium2`)
- **GROBID** — AGPL-3.0 (fallback: Docling)
- **YAKE** — GPL-3.0 (fallback: KeyBERT)

See `docs/explanation/llm-fallback-strategy.md` for the full fallback chain.
