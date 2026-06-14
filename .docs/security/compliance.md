---
title: ScholarForm AI — Compliance Posture
description: Compliance controls, data handling, and regulatory alignment
sidebar_position: 2
version: "1.0"
status: ✅ Complete
owner: Security
review_cadence: monthly
last_updated: June 2026
---

# Compliance Posture

## Data Handling

| Data Type | Storage | Encryption | Retention |
|-----------|---------|------------|-----------|
| Documents (DOCX/PDF) | Supabase Storage | AES-256 at rest, TLS in transit | 30 days after upload |
| User accounts | Supabase Auth | Hashed passwords, JWT tokens | Until account deletion |
| Pipeline logs | PostgreSQL (Supabase) | Encrypted at rest | 90 days |
| AI prompts and responses | In-memory or Redis | TLS in transit | Not persisted |
| Metrics | Prometheus | Not encrypted | 7 days |

## Controls

- **Access Control**: Supabase RLS, JWT authentication, role-based access (user, admin)
- **Audit Trail**: All write operations logged with request_id, user_id, timestamp
- **Input Validation**: File type, magic bytes, size limits (50MB), ClamAV scan
- **Output Sanitization**: HTML sanitization in preview, DOCX validation on export
- **Rate Limiting**: Per-IP and per-user rate limits, tier-based enforcement
- **Session Management**: JWT with 1h expiry, refresh tokens, force-logout capability

## Regulatory Alignment

- **GDPR**: Data deletion on request, 30-day retention, encryption at rest and in transit
- **SOC 2** (target): Audit logging, access controls, monitoring
- **ISO 27001** (target): Information security management system alignment

## See Also

- [Security Model](../docs/explanation/security-model.md)
- [Middleware & Security System](content/Backend Development/Middleware & Security System.md)
- [Operations Runbooks](../runbooks/)
