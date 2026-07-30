# Versioning Policy

ScholarForm AI follows [Semantic Versioning 2.0.0](https://semver.org/).

## Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE[.+BUILD]]
```

- **MAJOR** — Incompatible API changes, major feature drops, breaking database migrations
- **MINOR** — Backward-compatible feature additions, deprecation warnings
- **PATCH** — Backward-compatible bug fixes, security patches, performance improvements
- **PRERELEASE** — `alpha`, `beta`, `rc` (release candidate) suffixes

## Version Alignment

All components share a single unified version number:

| Component | Source |
|-----------|--------|
| Backend (`__version__`) | `backend/app/__init__.py` |
| Backend (package) | `backend/pyproject.toml` |
| Frontend | `frontend/package.json` |
| Citation | `CITATION.cff` |
| Git tag | `v<version>` |

## Release Cadence

| Release | Frequency | Support Window |
|---------|-----------|---------------|
| Major | ~6-12 months | 18 months |
| Minor | ~4-8 weeks | 12 months |
| Patch | As needed | 6 months |
| Security | <24h from disclosure | Full LTS window |

## Backward Compatibility

- **API v1** — No breaking changes within MAJOR version. Deprecations announced one MINOR version before removal.
- **Database** — Migrations are backward-compatible for one MINOR version. Rollbacks supported within that window.
- **Configuration** — Environment variables and config files maintain backward compatibility. Deprecated keys logged as warnings for one MINOR version.

## Pre-release Versions

Pre-release versions (alpha, beta, rc) indicate that the version is unstable and may not satisfy compatibility requirements:

```
1.0.0-alpha    — Internal testing, unstable API
1.0.0-beta     — Feature-complete, testing phase
1.0.0-rc.1     — Release candidate, final validation
```

## Deprecation Policy

1. Mark as deprecated in CHANGELOG and docstrings
2. Emit deprecation warning at runtime for one full MINOR version
3. Remove in the next MAJOR version
4. Document migration path in MIGRATION.md

## Version Bump Process

When preparing a release:

```bash
# Update version in source files
backend/app/__init__.py
backend/pyproject.toml
frontend/package.json
CITATION.cff

# Run the sync script to verify alignment
python scripts/sync_version.py

# Commit and tag
git commit -m "release: v<version>"
git tag -a v<version> -m "v<version>"
```
