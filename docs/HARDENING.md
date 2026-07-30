<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Hardening Mechanisms

## Overview

ScholarForm AI applies multiple hardening mechanisms to make software defects less likely to result in security vulnerabilities. This document describes the hardening measures in place across the application, infrastructure, and CI/CD pipeline.

## Application-Level Hardening

### Web Security Headers

All production responses include the following security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | Restrictive CSP (script-src, style-src, img-src, connect-src, frame-src, report-uri) | Prevents XSS and data injection attacks |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforces HTTPS |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer information |
| `Permissions-Policy` | Restricted feature permissions | Limits API access |

### Input Validation

- **Triple validation**: MIME type + magic bytes + file extension verification on all uploads.
- **Schema validation**: Pydantic models validate all API inputs with type, range, and format constraints.
- **Allowlist approach**: Inputs validated against allowlists where possible, not denylists.

### Output Encoding

- All user-generated content is encoded before rendering (prevents XSS).
- JSON responses use safe serialization.
- Template rendering uses auto-escaping.

### Authentication & Authorization

- JWT verification against Supabase JWKS endpoint on every authenticated request.
- Row-level security (RLS) in Supabase scopes data per user.
- Role-based access control for admin functions.
- API keys encrypted with Fernet at rest.

### Rate Limiting

- Per-IP token bucket (120 requests/minute base rate).
- Per-key tier-aware rate limiting.
- Rate limit headers in responses (`X-RateLimit-*`).

### Error Handling

- No stack traces exposed in production.
- Consistent error response format.
- Sanitized error messages to prevent information disclosure.

## Infrastructure Hardening

### Network

| Measure | Implementation |
|---------|---------------|
| TLS version | TLS 1.3 only (production) |
| CORS | Strict origin allowlist, no wildcard in production |
| HTTPS redirect | All HTTP requests redirected to HTTPS |

### Data

- **Encryption at rest**: AES-256 for database (Supabase), AES-256 for file storage.
- **Encryption in transit**: TLS 1.3 for all external communication.
- **Secrets management**: Environment variables never committed, `detect-secrets` pre-commit hook.
- **API keys**: Fernet-encrypted at rest in database.

### Runtime

- **Memory limits**: Process-level memory limits on Celery workers.
- **Request size limits**: 60MB max body size on API.
- **Timeouts**: Configurable timeouts for all external service calls.
- **Circuit breakers**: `pybreaker` for external service resilience.

## CI/CD Hardening

| Measure | Tool |
|---------|------|
| SAST | CodeQL, Bandit |
| Secret scanning | detect-secrets (pre-commit), GitHub secret scanning (push protection) |
| Dependency scanning | pip-audit, npm audit, OWASP Dependency Check |
| Container scanning | Trivy |
| Supply chain | SLSA Level 3, OpenSSF Scorecard, cosign signing |
| Dependencies | Dependabot, Renovate |

## Compiler/Interpreter Hardening

- Python: Running with optimized assertions where appropriate.
- Docker: Images use `python:3.12-slim` with reduced attack surface.
- Node.js: Running with `--enable-source-maps` for error tracing.

## Dependency Hardening

- Pinned dependency versions (`requirements.txt`, `package-lock.json`).
- Integrity verification (`package-lock.json` hash checking, pip hash checking).
- Regular vulnerability scanning via Dependabot and CI.

---

*Last updated: July 2026*
