---
title: ScholarForm AI — Threat Model
description: STRIDE threat model analysis and mitigations for ScholarForm AI
sidebar_position: 3
version: "1.0"
status: ✅ Complete
owner: Security
review_cadence: monthly
last_updated: June 2026
---

# Threat Model

## Spoofing

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Fake user identity | JWT token theft | Short expiry (1h), refresh tokens, HTTPS-only |
| API key theft | Exposed in logs or client | Key rotation, env vars, no logging of secrets |

## Tampering

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Document content modification | Man-in-the-middle | HTTPS or TLS enforced |
| Uploaded file tampering | Malicious file upload | Magic bytes check, ClamAV scan, size limits |
| Database tampering | SQL injection | SQLAlchemy parameterized queries, RLS |

## Repudiation

| Threat | Vector | Mitigation |
|--------|--------|------------|
| User denies action | No audit trail | Request ID and audit logging on all write operations |
| Pipeline failure denial | No logs | Structured logging with job_id correlation |

## Information Disclosure

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Document leakage | Storage breach | AES-256 encryption, RLS policies |
| API key leakage | Error responses | Sanitized error messages, no secrets in responses |
| User data exposure | Insecure endpoints | Authentication required on all document endpoints |

## Denial of Service

| Threat | Vector | Mitigation |
|--------|--------|------------|
| API flooding | Excessive requests | Rate limiting (sliding window), tier-based limits |
| Pipeline exhaustion | Large or batch uploads | Concurrency semaphore, queue thresholds |

## Attack Surface Overview

```mermaid
graph TB
    subgraph "External"
        EXT_A["Browser Client"]
        EXT_B["API Consumer"]
        EXT_C["Malicious Actor"]
    end
    subgraph "Attack Vectors"
        VEC1["XSS / CSRF"]
        VEC2["JWT theft / replay"]
        VEC3["File upload abuse"]
        VEC4["API flooding"]
        VEC5["IDOR"]
    end
    subgraph "Mitigations"
        MIT1["CSP + HSTS + CORS"]
        MIT2["Short JWT expiry + refresh"]
        MIT3["Magic bytes + ClamAV + size limit"]
        MIT4["Rate limit + concurrency semaphore"]
        MIT5["RLS + user_id verification"]
    end
    EXT_A --> VEC1
    EXT_A --> VEC2
    EXT_B --> VEC4
    EXT_C --> VEC3
    EXT_C --> VEC5
    VEC1 --> MIT1
    VEC2 --> MIT2
    VEC3 --> MIT3
    VEC4 --> MIT4
    VEC5 --> MIT5
```

## Elevation of Privilege

| Threat | Vector | Mitigation |
|--------|--------|------------|
| User accesses another user's documents | IDOR | RLS policies, user_id verification |
| Guest uses paid features | Tier bypass | TierRateLimitMiddleware, server-side enforcement |

## See Also

- [Security Model](../docs/explanation/security-model.md)
- [Middleware & Security System](content/Backend Development/Middleware & Security System.md)
- [Compliance Posture](compliance.md)
