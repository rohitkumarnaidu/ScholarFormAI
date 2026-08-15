# Release Strategy

This document outlines the release process, cadence, and support lifecycle for **ScholarForm AI**.

## Release Cadence

We aim to provide a predictable release schedule for our community and enterprise users.

- **Patch Releases (1.x.y):** Released as needed, typically every 1-2 weeks. These include urgent bug fixes, security patches, and minor non-breaking enhancements.
- **Minor Releases (1.x.0):** Released every 4-6 weeks. These include new features, templates, and agent capabilities that are fully backward compatible.
- **Major Releases (X.0.0):** Released annually. These may contain breaking changes, architectural overhauls, and major new paradigms (e.g., introducing CRDTs).

## Release Process

Our release pipeline is fully automated and adheres to Enterprise Open Source standards:

1. **Feature Freeze:** 1 week prior to a minor/major release, the main branch enters a feature freeze. Only bug fixes are merged.
2. **Release Candidate (RC):** A release candidate (e.g., `v1.1.0-rc.1`) is tagged and deployed to our staging environments.
3. **Automated Testing:** Extensive E2E, integration, and security scans (including SLSA Level 3 compliance checks) are executed.
4. **Final Release:** Upon successful validation, the final version is tagged, and artifacts (Docker images, NPM packages, PyPI packages) are published. The [CHANGELOG.md](CHANGELOG.md) is updated.

## Long-Term Support (LTS)

To support our enterprise integrators and academic institutions, ScholarForm AI designates specific minor versions as LTS releases.

- LTS releases receive backported security updates and critical bug fixes for **18 months**.
- Regular releases receive support for **6 months**.

Users running mission-critical formatting pipelines are encouraged to deploy LTS versions.

## Deprecation Policy

Features or APIs slated for removal will be marked as deprecated in a minor release and will remain functional until the next major release, providing at least a 6-month migration window. Please see [VERSIONING.md](VERSIONING.md) for more details.
