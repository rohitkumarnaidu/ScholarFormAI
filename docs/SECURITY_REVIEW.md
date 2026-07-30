<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Security Review

## Overview

ScholarForm AI performs regular security reviews to identify vulnerabilities, assess risk, and ensure the platform meets its security requirements. This document outlines the review process, scope, and findings.

## Review Cadence

| Review Type | Frequency | Performer |
| ------------- | ----------- | ----------- |
| Internal security review | Quarterly | Project maintainers |
| SAST scan (CodeQL + Bandit) | Every push | Automated (CI) |
| Dependency vulnerability scan | Weekly (Dependabot) + Every push (pip-audit, npm audit) | Automated |
| Container scan (Trivy) | Every PR to main | Automated (CI) |
| OpenSSF Scorecard evaluation | Weekly | Automated |
| Fuzz testing | On relevant code changes | Automated (CI) |
| Dependency review | Every PR to main | Automated |

## Scope

The security review covers:

- **Authentication and authorization**: JWT verification, Supabase RLS, API key validation, RBAC
- **Input validation**: File upload validation (MIME, magic bytes, extension tri-check), API input sanitization
- **Data protection**: Encryption at rest (AES-256), encryption in transit (TLS 1.3), secrets management
- **Infrastructure**: Supabase database, Redis cache, Celery workers, file storage
- **Dependencies**: All pip/npm packages, Docker base images
- **API endpoints**: All 34 routes for injection, authorization bypass, information disclosure
- **Web security**: CSP headers, HSTS, X-Content-Type-Options, X-Frame-Options, CSRF protection

## Security Requirements

The software is designed to meet the following security requirements:

1. **Authentication**: Only authenticated users may access protected resources. JWTs are verified against Supabase JWKS endpoint.
2. **Authorization**: Users may only access their own data (row-level security). Role-based access for admin functions.
3. **Input validation**: All file uploads undergo MIME type, magic byte, and extension validation. ClamAV scans all uploads.
4. **Output encoding**: All user-generated content is properly encoded to prevent XSS.
5. **Rate limiting**: Per-IP and per-key rate limiting with token bucket algorithm (120 req/min base).
6. **Secure defaults**: HTTPS enforced in production, CORS restricted to known origins, CSP headers restrictive.
7. **Audit logging**: All write operations (POST, PUT, DELETE) are logged with user ID, timestamp, and action.

## Secure Design Implementation

ScholarForm AI implements the following secure design principles (per Saltzer & Schroeder):

| Principle | Implementation |
| ----------- | --------------- |
| Economy of mechanism | Simple architecture: FastAPI → Supabase + Redis. Minimal attack surface. |
| Fail-safe defaults | Access denied by default; explicit grants required. |
| Complete mediation | All API requests pass through auth middleware. File access checked per-request. |
| Open design | Security mechanisms documented and open source. |
| Separation of privilege | API keys separate from user auth. Admin vs user roles separate. |
| Least privilege | Workers run with minimal DB permissions. API tokens scoped per user. |
| Least common mechanism | Separate Redis DBs for cache vs queue. Separate Celery queues. |
| Psychological acceptability | Clear error messages, documentation, intuitive permission model. |
| Limited attack surface | CORS restricted, only necessary endpoints exposed, rate limited. |
| Input validation with allowlists | Upload validation uses allowlists for MIME types, not denylists. |

## Vulnerability Management

See [SECURITY.md](../SECURITY.md) for the full vulnerability management process, including:

- Responsible disclosure policy
- Response SLA (24h acknowledgment, 7d critical fix)
- CVE process via GitHub Security Advisories
- Supported versions and backport policy

## Recent Review Findings

| Date | Type | Findings | Status |
| ------ | ------ | ---------- | -------- |
| July 2026 | SAST (CodeQL + Bandit) | 0 critical, 0 high | Clean |
| July 2026 | Dependency scan | 0 critical CVEs | Clean |
| July 2026 | Container scan (Trivy) | 0 critical, 0 high | Clean |
| July 2026 | OpenSSF Scorecard | 14/16 checks at 10/10 | Active |

## SLSA Provenance

All releases include SLSA Level 3 provenance attestations, ensuring build integrity and supply chain security.

## Security.txt

A `security.txt` file is available at `https://scholarform.ai/.well-known/security.txt` following RFC 9116.

---

*Last updated: July 2026*
