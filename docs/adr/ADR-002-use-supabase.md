# ADR-002: Use Supabase as Primary Database and Auth Provider

- **Status:** Accepted
- **Date:** 2026-01-20
- **Author:** ScholarForm AI Engineering Team

## Context

ScholarForm AI needs a managed database and authentication system that supports:

- Relational data storage for users, documents, templates, billing, and API keys
- Row-level security for multi-tenant document access
- File storage for uploaded manuscripts and exported PDFs/DOCX
- User authentication with social login and API key management
- Real-time subscriptions for formatting progress updates

The alternatives considered were: self-hosted PostgreSQL + separate Auth0/Firebase, Neon, PlanetScale, and Supabase.

## Decision

We chose **Supabase** as the single provider for database, auth, and storage.

| Criterion | Supabase | Self-hosted PG + Auth0 | Neon | PlanetScale |
|-----------|----------|----------------------|------|-------------|
| Managed PostgreSQL | ✅ Built-in |  ️ Requires ops | ✅ Built-in |  ️ MySQL-based |
| Auth provider | ✅ Built-in | ✅ Auth0/Firebase | ❌ Separate | ❌ Separate |
| File storage | ✅ Built-in | ❌ S3 needed | ❌ Separate | ❌ Separate |
| Row-level security | ✅ Native | ❌ App-layer | ❌ Not native | ❌ Not native |
| Real-time subscriptions | ✅ Built-in | ❌ Extra infra | ❌ Extra infra | ❌ Extra infra |
| Ops overhead | Low | High | Low | Low |

Self-hosting PostgreSQL was rejected due to the operational cost of managing replication, backups, and failover for a small team. Auth0 adds per-user pricing that grows with the user base. PlanetScale uses MySQL, which introduces compatibility risk with SQLAlchemy async and Alembic migrations.

## Consequences

**Positive:**
- Single vendor for DB, auth, storage, and real-time — reduces integration surface area
- Row-level security (RLS) policies enforce multi-tenant isolation at the database level, not just the application layer
- Supabase Realtime enables push-based progress updates for long-running formatting jobs
- Managed backups and point-in-time recovery eliminate manual DBA work
- Storage bucket policies mirror RLS, providing consistent access control for manuscript files
- Supabase Auth supports OAuth (Google, GitHub) and email/password with minimal configuration

**Negative:**
- Vendor lock-in — migrating away requires rewriting auth and storage layers
- Connection pooling limitations on the free/Pro tier require careful connection management
- Not all PostgreSQL features are available (e.g., extensions must be on Supabase's allowlist)
- Realtime feature uses PostgreSQL replication slots, which count against the database connection limit
- Self-hosted alternative is impractical without dedicated infrastructure budget
- API rate limits on the free tier require monitoring and proactive upgrades

## Compliance

This decision has been implemented and is verified by:
- `backend/tests/test_supabase_client.py` — Supabase client initialization and operations
- `backend/tests/test_routers_auth.py` — JWT verification via Supabase Auth
- `backend/tests/test_security_enterprise.py` — Row-Level Security verification
- `backend/app/db/supabase.py` — Supabase client factory
- `backend/app/db/models/user.py` — RLS-policy-scoped user data access

## Cross-References

- [ADR 001: Python-First Runtime](001-python-first-runtime.md) — Python 3.12 runtime
- [ADR 004: ChromaDB for RAG](ADR-004-chromadb-for-rag.md) — vector storage (complements Supabase)
- [Security Model](../explanation/security-model.md) — RLS and encryption at rest
- [Database Model](../Database.md) — schema and relationships
