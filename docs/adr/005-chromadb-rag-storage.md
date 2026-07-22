<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 005: ChromaDB for RAG Vector Storage"
description: Decision to use ChromaDB for session-scoped document embeddings
sidebar_position: 44
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# ADR 005: ChromaDB for RAG Vector Storage

## Context

The synthesis and agent features require semantic search over uploaded documents. A vector database is needed to store and query document embeddings.

## Decision

Use ChromaDB as the embedded vector store. Collections are created per-session (`session_{id}`) with a 24-hour TTL for auto-cleanup.

## Consequences

- No external vector DB service to manage
- Embeddings stored on local filesystem at `backend/db/semantic_store/`
- TTL cleanup via Celery beat scheduled task
- Limited to single-node deployment (not distributed)
- Embedding model: `multi-qa-MiniLM-L6-v2` for a balance of speed and quality
