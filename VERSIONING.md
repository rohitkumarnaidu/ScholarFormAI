# Versioning

## Semantic Versioning

AMF follows [Semantic Versioning 2.0.0](https://semver.org/):

Given a version number `MAJOR.MINOR.PATCH`:

- **MAJOR** (1.x.x): Incompatible API or CLI changes
- **MINOR** (x.1.x): New functionality in a backward-compatible manner
- **PATCH** (x.x.1): Backward-compatible bug fixes

## Version Manifest

Version numbers are maintained in:

| Component | File |
|-----------|------|
| Backend API | `backend/app/__init__.py` |
| CLI | `cli/amf/__init__.py` |
| SDK | `sdk/amf_sdk/__init__.py` |
| Frontend | `frontend/package.json` |

All components are released together under the same version.

## Stability Guarantees

### API Stability
- All `/api/v1/*` endpoints are stable within a major version
- New endpoints may be added in minor versions
- Breaking changes only in major versions

### CLI Stability
- All commands and flags are stable within a major version
- New commands and flags added in minor versions
- Deprecated flags removed in the next major version

### SDK Stability
- Public API (`amf_sdk` module) is stable within a major version
- Private modules (`_*`) may change in minor versions

### Configuration Stability
- Configuration file format is stable within a major version
- New options may be added in minor versions

## Deprecation Policy

1. Deprecated features are announced in the CHANGELOG
2. Deprecated features emit warnings for at least one minor version
3. Features are removed only in major versions

## Pre-release Versions

Pre-release versions follow the format `X.Y.Z-alpha.N`, `X.Y.Z-beta.N`, or `X.Y.Z-rc.N`.

These are used for testing and are not guaranteed to be stable.
