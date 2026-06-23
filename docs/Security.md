<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Security
description: Security controls, gaps, and hardening measures
sidebar_position: 35
version: "1.0"
status: ✅ Complete
owner: Security Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Security

> **Codex Finding:** Security is **"better scaffolded than plans claim"** — most security primitives are in place and properly sized. However, live validation across production endpoints has not been performed. Critical gaps in RBAC and audit logging remain.

> **See also:** [Risk Register](Risk_Register.md), [Secret Rotation](SECRET_ROTATION.md), [API Key Quick Start](API_KEY_QUICK_START.md)

---

## Implemented Controls

| Control | File | Size | Status |
|---------|------|------|--------|
| JWKS JWT Verification | `security/jwks_verifier.py` | 5.4KB | ✅ Implemented |
| Security Headers (CSP, HSTS) | `middleware/security_headers.py` | 4.6KB | ✅ Implemented |
| Rate Limiting (base) | `middleware/rate_limit.py` | 6.9KB | ✅ Implemented |
| Tier-Aware Rate Limiting | `middleware/tier_rate_limit.py` | 4.1KB | ✅ Implemented |
| Abuse Detection | `middleware/abuse_detector.py` | 2.7KB | ✅ Implemented |
| Virus Scanning (ClamAV) | `utils/virus_scanner.py` | 4.4KB | ✅ Implemented |
| Request ID Tracking | `middleware/request_id.py` | 2.2KB | ✅ Implemented |
| MIME + Magic Byte Validation | Inline in document router | — | ✅ Implemented |
| RBAC Middleware | `middleware/rbac.py` | 708B | ⚠️ **Stub** |
| Audit Logging | `services/audit_log_service.py` | 1.1KB | ⚠️ **Minimal** |
| Signed Download URLs | In `document_service.py` | — | ⚠️ Needs live verification |

---

## Codex Assessment

> **"Better scaffolded than plans claim"** — Codex 5.4 Audit

**Strengths identified:**
- Rate limiting is two-layer (base + tier-aware) — more sophisticated than most projects at this stage
- JWKS verifier properly fetches public keys from Supabase JWKS endpoint
- ClamAV integration is a proper daemon client (not a subprocess call)
- Abuse detector is a real middleware, not a stub
- Security headers include CSP — proactively reduces XSS attack surface

**Gaps to address before live validation:**
- RBAC middleware is 708B — too small to enforce real role-based access
- Audit logging service is 1.1KB — likely only logs some events, not all write operations
- Signed download URL verification not confirmed at runtime

---

## Security Gaps

| Gap | Severity | Fix |
|-----|----------|-----|
| RBAC is a stub (708B) | 🔴 HIGH | Implement role-based checks for: `admin`, `pro`, `free`, `guest` |
| Audit logging minimal (1.1KB) | 🔴 HIGH | Log all write ops with: user_id, action, resource_id, IP, timestamp |
| No secrets scanning in CI | 🟡 MEDIUM | Add Gitleaks or TruffleHog to `security.yml` |
| No CORS strict origin list | 🟡 MEDIUM | Whitelist production domains only (Vercel + custom domain) |
| ClamAV required in Docker | 🟡 MEDIUM | Add graceful degradation when ClamAV is unavailable (log warning, don't hard-fail) |
| Stripe webhook secret not verified to be set | 🟡 MEDIUM | Add startup check for `STRIPE_WEBHOOK_SECRET` |
| Pandoc/LibreOffice subprocess risks | 🟡 MEDIUM | Subprocess invocations carry command injection risk — strict input sanitization required |

---

## Security Checklist

- [x] ClamAV virus scanning before processing
- [x] HTTPS/HSTS enforcement via `security_headers.py`
- [x] JWKS JWT verification (Supabase)
- [x] Tier-aware rate limiting
- [x] CSP hardening
- [x] Request ID correlation
- [x] File MIME + magic byte + extension tri-validation
- [x] Abuse detection middleware
- [ ] **Audit logging for ALL write operations** (currently minimal)
- [ ] **Admin RBAC** (currently stub — 708B)
- [ ] Signed download URLs — runtime verification needed
- [ ] CVE scanning in CI (Trivy exists in `security.yml` — verify it runs)
- [ ] Secrets scanning in CI (Gitleaks/TruffleHog)
- [ ] CORS strict origin list

---

## Authentication Flow

```
Browser → Supabase Auth (JWT issued)
       → All API requests: Authorization: Bearer <jwt>
       → FastAPI JWKS middleware → jwks_verifier.py
       → Verifies signature against Supabase JWKS endpoint
       → Extracts user_id, role, plan_tier
       → Passes to route handlers
```

---

## Known Risk: Subprocess Attack Surface

`latex_exporter.py` (stub) and `document_service.py` invoke Pandoc and LibreOffice as subprocesses. These must have:
1. Strict input whitelist (only allow DOCX/PDF/TeX extensions)
2. No user-controlled string concatenation in subprocess args
3. Timeout enforcement to prevent resource exhaustion

See [`docs/Risk_Register.md`](Risk_Register.md) for the full risk inventory.
