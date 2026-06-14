---
title: ScholarForm AI — Security & Compliance
description: Security model, compliance posture, threat model, and security operations
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: Security
review_cadence: monthly
last_updated: June 2026
---

# Security & Compliance

## Security Model

ScholarForm AI implements defense-in-depth across all layers:

| Layer | Controls |
|-------|----------|
| **Network** | HTTPS enforcement, CORS, security headers (CSP, HSTS) |
| **Auth** | JWT-based auth via Supabase, RLS policies, tier-based rate limiting |
| **API** | Rate limiting (sliding window), request ID tracing, audit logging |
| **Input** | File type validation, magic bytes check, ClamAV antivirus scanning |
| **Pipeline** | Timeout enforcement, cancellation, partial result persistence |
| **Secrets** | Environment variables, `.secrets.baseline`, detect-secrets pre-commit hook |

## Available Documents

| Document | Description |
|----------|-------------|
| [Security Model](../docs/explanation/security-model.md) | Detailed security architecture |
| [Compliance](compliance.md) | Compliance posture and data handling controls |
| [Secret Rotation](../docs/SECRET_ROTATION.md) | Secret rotation procedures |
| [Threat Model](threat-model.md) | STRIDE threat model and mitigations |

## Defense in Depth

```mermaid
graph TB
    subgraph "Layer 1: Network"
        L1A["HTTPS enforcement"]
        L1B["CORS policies"]
        L1C["Security headers (CSP, HSTS)"]
    end
    subgraph "Layer 2: Auth"
        L2A["JWT authentication"]
        L2B["Supabase RLS"]
        L2C["Tier-based rate limiting"]
    end
    subgraph "Layer 3: API"
        L3A["Sliding window rate limit"]
        L3B["Request ID tracing"]
        L3C["Audit logging"]
    end
    subgraph "Layer 4: Input"
        L4A["File type validation"]
        L4B["Magic bytes check"]
        L4C["ClamAV antivirus"]
    end
    subgraph "Layer 5: Secrets"
        L5A["Environment variables"]
        L5B["detect-secrets pre-commit"]
        L5C["Quarterly rotation"]
    end
    Request["Incoming Request"] --> L1A
    L1A --> L1B
    L1B --> L1C
    L1C --> L2A
    L2A --> L2B
    L2B --> L2C
    L2C --> L3A
    L3A --> L3B
    L3B --> L3C
    L3C --> L4A
    L4A --> L4B
    L4B --> L4C
    L4C --> L5A
```

## Key Practices

- All secrets in environment variables via `settings.py` (Pydantic Settings)
- No secrets committed — enforced by `detect-secrets` pre-commit hook
- API keys rotated quarterly
- JWT tokens expire after 1 hour, refresh tokens after 7 days
- File uploads scanned by ClamAV before processing
- Rate limits: 100 req/min (authenticated), 10 req/min (guest uploads)

## See Also

- [Operations Runbooks](../runbooks/) — Incident response and secret rotation
- [Middleware & Security System](content/Backend Development/Middleware & Security System.md)
