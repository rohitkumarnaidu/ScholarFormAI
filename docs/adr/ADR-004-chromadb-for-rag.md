# ADR-004: Use ChromaDB for RAG Vector Store

- **Status:** Accepted
- **Date:** 2026-03-05
- **Author:** ScholarForm AI Engineering Team

## Context

ScholarForm AI's formatting engine needs to apply journal-specific formatting rules, citation styles, and structural guidelines. These rules are stored as unstructured text in guideline documents, style guides, and reference materials. A retrieval-augmented generation (RAG) pipeline is required to:

- Index hundreds of academic style guides (APA, MLA, IEEE, Chicago, journal-specific)
- Retrieve relevant formatting rules for a given manuscript in real-time
- Support embedding-based semantic search (not just keyword match)
- Operate locally in CI/testing without external service dependencies

Alternatives evaluated: Pinecone (managed), Weaviate (self-hosted), pgvector (PostgreSQL extension), and ChromaDB.

## Decision

We chose **ChromaDB** over the alternatives.

| Criterion | ChromaDB | Pinecone | Weaviate | pgvector |
|-----------|----------|----------|----------|----------|
| Local-first | ✅ Yes | ❌ Cloud-only | ⚠️ Hybrid | ✅ Yes |
| No infra deps | ✅ Embedded | ❌ Requires API key | ❌ Requires Docker | ⚠️ Requires PG |
| CI-friendly | ✅ Yes | ❌ Network access | ❌ Docker needed | ✅ Yes |
| Python-native | ✅ First-class | ✅ SDK | ✅ SDK | ⚠️ Via SQLAlchemy |
| HNSW indexing | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ IVFFlat |
| Self-hostable | ✅ Trivial | ❌ No | ⚠️ Heavy | ✅ Trivial |
| Multi-tenancy | ⚠️ Collection-per-tenant | ✅ Namespaces | ✅ Multi-tenancy | ✅ Row-level |

Pinecone was rejected because it requires a cloud API key and network access, making CI tests impossible without external dependencies. Weaviate requires Docker, adding ~1.5GB of overhead for a vector store that is secondary to the main database. pgvector was a close contender but lacks native Python embedding management and requires adding vector operations to the existing PostgreSQL connection pool, which is already under load from document storage.

## Consequences

**Positive:**
- Zero infrastructure dependencies — ChromaDB runs as an embedded library, making the RAG pipeline testable in CI without Docker or network access
- Sub-100ms retrieval for guideline chunks under 10K documents with HNSW indexing
- Persistent client option stores data on disk, surviving restarts in development
- Collection-based organization maps naturally to different guideline sources (APA, MLA, journal-specific)
- Simple Python API reduces onboarding friction — no separate query language or schema management
- Easy to reset or rebuild indexes — simply delete the on-disk storage directory

**Negative:**
- Not designed for production-scale workloads — embedding operations block the event loop without careful async wrapping
- No built-in replication or sharding — a single ChromaDB instance is a single point of failure
- Metadata filtering is limited compared to Weaviate's rich filter DSL
- Collection-level (not document-level) multi-tenancy means tenant isolation requires separate collections
- Embedding model must be loaded separately — ChromaDB does not bundle or manage models
- On-disk format is opaque and not easily inspectable or migratable to other vector stores

## Compliance

This decision has been implemented and is verified by:
- `backend/tests/test_chroma_minimal.py` — ChromaDB CRUD and persistence
- `backend/tests/test_vector_db_security.py` — collection-level isolation
- `backend/tests/pipeline/test_rag_engine.py` — RAG pipeline with ChromaDB
- `backend/db/semantic_store/` — persistent client storage directory
- `backend/app/services/rag_engine.py` — `RagEngine` with `multi-qa-MiniLM-L6-v2`
- `backend/tests/test_embeddings.py` — embedding model loading and query

## Cross-References

- [ADR 005: ChromaDB for RAG Storage](005-chromadb-rag-storage.md) — companion ADR with session-scoped TTL details
- [ADR 002: Use Supabase](ADR-002-use-supabase.md) — primary database (complementary to vector store)
- [AI Architecture](../AI_ARCHITECTURE.md) — RAG pipeline overview
- [Pipeline Architecture](../explanation/pipeline-architecture.md) — end-to-end processing flow
