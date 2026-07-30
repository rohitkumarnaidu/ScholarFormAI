# Database Documentation & Schema Specification

> **NOTICE**: ScholarForm AI database documentation has been consolidated into [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

---

## Persistent Database Architecture

ScholarForm AI uses a multi-store persistence architecture:

1. **Supabase PostgreSQL (v15+)**: Primary relational database containing 16 operational tables (`profiles`, `documents`, `document_results`, `document_versions`, `processing_status`, `suggestions`, `user_api_keys`, `api_key_usage_log`, `custom_providers`, `generator_sessions`, `generator_messages`, `generator_documents`, `audit_log`, `webhook_subscriptions`, `webhook_delivery_logs`, `document_shares`).
2. **Redis 7.x**: High-performance cache layer for GROBID extractions (1h TTL), LLM completions (24h TTL), rate limiting, and Celery task queuing.
3. **ChromaDB**: Persistent local vector store for publisher style guidelines (`bge-m3` model) and per-session RAG context.

For the complete Entity-Relationship Diagram (ERD), full 16-table schema references, index specifications, and Row Level Security (RLS) policies, please refer directly to:

👉 **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)**

---

*Last updated: July 2026*
