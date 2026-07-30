<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Bus Factor & Access Continuity

## Bus Factor

The **bus factor** (also known as "truck factor") is the minimum number of project members that would have to suddenly disappear before the project stalls due to lack of knowledgeable personnel.

### Current Status

| Role | Current Incumbent | Bus Factor Risk |
|------|------------------|-----------------|
| BDFL / Project Lead | Rohit Kumar Naidu | 1 (single point of failure) |
| Backend Core | Vacant | N/A |
| Frontend Core | Vacant | N/A |
| DevOps Core | Vacant | N/A |

**Current bus factor: 1**

### Target

**Target bus factor: 2+** (OpenSSF Gold badge requirement)

### Mitigation Plan

1. **Recruit core team members** for backend, frontend, and DevOps roles (see [MAINTAINERS.md](../MAINTAINERS.md) for open positions).
2. **Cross-training** — document all critical processes so they can be performed by multiple people.
3. **Bus factor initiatives** — identify candidates from active contributors and mentor them into core team roles.

## Access Continuity

The project MUST be able to continue with minimal interruption if any one person is unable to continue support. This includes the ability to:

- Create and close issues
- Accept proposed changes
- Release versions of software

### Current Safeguards

| Resource | Backup Plan |
|----------|-------------|
| GitHub repository | Multiple admin accounts available |
| npm package publishing | GitHub Actions CI automates publishing |
| PyPI package publishing | GitHub Actions CI automates publishing |
| Docker image publishing | GitHub Actions CI automates publishing |
| Domain names | Registrant credentials documented |
| CI/CD configuration | Stored in repository, not single-person dependent |
| Secrets and keys | Rotated regularly, documented in SECRET_ROTATION.md |

### Resilience by Automation

The project's heavy reliance on CI/CD automation reduces bus factor risk:

| Function | Automation | Dependency on Single Person |
|----------|-----------|---------------------------|
| Testing | 25 CI workflows | Low (fully automated) |
| Security scanning | Dependabot, CodeQL, Trivy, Scorecard | Low (fully automated) |
| Release | create-release.yml, docker-publish.yml | Low (tag-triggered) |
| Dependency updates | Renovate, Dependabot | Low (auto-PR with review) |

---

*Last updated: July 2026*
