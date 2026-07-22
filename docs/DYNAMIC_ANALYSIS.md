<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Dynamic Analysis

## Overview

ScholarForm AI applies dynamic analysis tools to detect runtime defects and security vulnerabilities before release. This document describes the dynamic analysis techniques in use.

## Fuzz Testing

The project includes [Atheris](https://github.com/google/atheris) (a Python fuzzing engine based on libFuzzer) fuzz tests:

| Target | File | Description |
|--------|------|-------------|
| Document title parser | `fuzz/fuzz_document_title.py` | Fuzzes title extraction from various input formats |
| Metadata parser | `fuzz/fuzz_metadata_parser.py` | Fuzzes metadata parsing from document headers |

Fuzz tests run automatically in CI on PRs that modify `backend/fuzz/` paths (via `.github/workflows/fuzzing.yml`).

## Runtime Assertions

The software includes runtime assertions and validation checks throughout the codebase:

- **Pydantic models**: All API inputs are validated by Pydantic schemas with type, range, and format constraints.
- **SQLAlchemy**: Database operations include integrity checks and constraint validation.
- **File validation**: Uploaded files are validated for MIME type, magic bytes, and extension before processing.
- **Pipeline stage assertions**: Document processing pipeline validates stage inputs and outputs at each step.
- **Celery task validation**: Background tasks validate inputs and handle failures gracefully with retry logic.

## CI Dynamic Analysis

| Tool | Scope | Trigger | Action on Failure |
|------|-------|---------|-------------------|
| Atheris fuzz tests | Title parser, metadata parser | PR to main with fuzz changes | CI failure, must fix |
| Trivy (container scan) | Docker images | PR to main, weekly | CI failure on CRITICAL/HIGH |
| pip-audit | Python dependencies | Every push | CI failure on known CVEs |
| npm audit | JavaScript dependencies | Every push | CI failure on known CVEs |
| OWASP Dependency Check | All dependencies | PR to main | CI failure on HIGH/CRITICAL |

## Security Testing

Dynamic security testing is performed through:

- **Trivy filesystem scanning**: Scans the filesystem for vulnerabilities in dependencies.
- **OWASP Dependency Check**: Identifies publicly known vulnerabilities in project dependencies.
- **Container vulnerability scanning**: All Docker images are scanned for CVEs before publishing.

## Assertion Policy

Runtime assertions are used to:

1. Validate preconditions and postconditions of critical functions.
2. Check invariants in the document processing pipeline.
3. Verify data integrity after transformations.
4. Detect unexpected states early in development.

Assertions are enabled in development and CI testing. Production builds may disable expensive assertions while retaining critical security checks.

---

*Last updated: July 2026*
