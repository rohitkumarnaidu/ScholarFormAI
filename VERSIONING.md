# Versioning Policy

**ScholarForm AI** strictly adheres to [Semantic Versioning 2.0.0](https://semver.org/). This document clarifies how SemVer applies to our platform, specifically addressing our REST APIs, CLI, and Agentic AI workflows.

## Version Format
Given a version number `MAJOR.MINOR.PATCH` (e.g., `1.2.3`):
- **MAJOR** version increments when we make incompatible API or architectural changes.
- **MINOR** version increments when we add functionality in a backward-compatible manner.
- **PATCH** version increments when we make backward-compatible bug fixes or security updates.

## API Versioning
Our REST APIs and Agent interfaces are versioned in the URL path (e.g., `/api/v1/format`).
- API path versions correspond to the **MAJOR** version of ScholarForm AI.
- Minor additions (new query parameters, new response fields) will not change the path version. Clients must be robust to receiving extra fields.
- Breaking changes (removing endpoints, changing response structures, changing required payload fields) will trigger a MAJOR version bump and a new API path (e.g., `/api/v2/`).

## Agentic AI Workflows
Because AI outputs can be non-deterministic, defining a "breaking change" for AI behavior is nuanced:
- **Patch/Minor:** Enhancements to prompt templates, upgrading to newer underlying LLM models, or tweaking RAG retrieval logic that improves quality without breaking the API contract are considered minor or patch changes.
- **Major:** Changing the fundamental structure of how agents communicate (e.g., switching from a synchronous Forensic Auditor to an asynchronous event-driven model) or requiring entirely new configuration variables for basic operation.

## Deprecation
Before any feature, CLI command, or API endpoint is removed, it will be marked as `DEPRECATED` in the documentation, [CHANGELOG.md](CHANGELOG.md), and via API warning headers. Deprecated features will be supported for at least one full MINOR release cycle (minimum 6 months) before being removed in the next MAJOR release.

Please consult our [Release Strategy](RELEASE.md) to understand how versions map to our support lifecycle.
