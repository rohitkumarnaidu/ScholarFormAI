<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---
title: ScholarForm AI — Supported Versions
description: Version support lifecycle and end-of-life timeline
sidebar_position: 35
version: "1.0"
status: ✅ Complete
owner: Security Team
review_cadence: quarterly
---

# Supported Versions

This document describes the support lifecycle for ScholarForm AI releases. It supplements the [Security Policy](../SECURITY.md).

---

## Active Support Matrix

| Version | Status | Security Patches | Bug Fixes | Feature Backports | EOL Date |
|---------|--------|-----------------|-----------|-------------------|----------|
| 1.0.x   | ✅ **Full Support (LTS)** | ✅ Yes | ✅ Yes | ✅ Yes (minor) | TBD |
| 0.9.x   | ❌ End of Life | ❌ No | ❌ No | ❌ No | 2026-07-21 |
| develop | ⚠️ CI-tested (Development) | ❌ No | ❌ No | ❌ No | N/A |

## Support Definitions

| Tier | Description | Included |
|------|-------------|----------|
| **Full Support (LTS)** | Active maintenance for all release lines | Security patches, critical/high bug fixes, medium bug fixes (next patch), low bug fixes (best-effort), minor feature backports |
| **End of Life** | No longer maintained | No patches, no bug fixes, no support |

## Versioning

ScholarForm AI follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (X.0.0) — Breaking changes, new architecture, large feature drops
- **MINOR** (1.X.0) — New features, non-breaking improvements
- **PATCH** (1.0.X) — Bug fixes, security patches, performance improvements

See [VERSIONING.md](../VERSIONING.md) for the complete versioning policy.

## LTS Commitment

Version 1.0.x is designated as a **Long Term Support (LTS) release**. The LTS window is a minimum of **12 months** from the initial 1.0.0 release date (2026-07-21). Critical security patches are backported to the latest stable minor version only.

The EOL date for the 1.0.x line will be announced at least **90 days** in advance via:
- GitHub Release notes
- A notice in [`CHANGELOG.md`](../CHANGELOG.md)
- An issue tagged `eol-announcement`

## Upgrade Path

| From | To | Recommended Timeline |
|------|----|---------------------|
| 0.9.x | 1.0.x | Immediately — 0.9.x is EOL |
| 1.0.x | 1.1.x | Within 90 days of 1.1.0 release |
| 1.x.x | 1.x+1.x | Before EOL of your current version |

## CI/CD Branches

| Branch | Support | Notes |
|--------|---------|-------|
| `main` | ✅ CI-tested | Production branch; all merges run full CI suite (26 workflows) |
| `develop` | ⚠️ Pre-release | Runs CI but not deployed; may contain unreleased features |
| `staging` | ⚠️ Pre-release | Deployed to staging environment for validation |
| `feature/*` | ❌ No support | Temporary; deleted after merge |

## Policy Updates

This policy is reviewed quarterly. Changes are documented in the [CHANGELOG](../CHANGELOG.md) and announced via GitHub Releases.

---

## Related Documents

| Document | Description |
|----------|-------------|
| [SECURITY.md](../SECURITY.md) | Vulnerability disclosure, supported versions, security practices |
| [VERSIONING.md](../VERSIONING.md) | Semantic versioning policy and release numbering |
| [RELEASE_PROCESS.md](../RELEASE_PROCESS.md) | Step-by-step release workflow |
| [CHANGELOG.md](../CHANGELOG.md) | Release history and change log |
| [ROADMAP.md](../ROADMAP.md) | Upcoming features and release timeline |
