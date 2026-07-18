<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 012: AI-Powered Suggestion Engine"
description: Dedicated suggestion microservice within the existing FastAPI app
sidebar_position: 37
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: yearly
last_updated: July 2026
---

# ADR 012: AI-Powered Suggestion Engine

## Context

The live-preview WebSocket (`/api/v1/preview/live`) currently generates inline formatting suggestions in-band with document rendering. As the user base grows, this creates two problems:

1. **Latency coupling** — Heavy LLM calls for suggestions block the render response, degrading the preview experience for all users on the same WebSocket connection.
2. **No persistence** — Suggestions are ephemeral; once the WebSocket frame is consumed, the suggestion text is lost. Users cannot review, accept, or reject past suggestions.

The enhancement manager (`backend/app/services/enhancement_manager.py`) dispatches formatting jobs but has no pipeline step dedicated to suggestion generation. A dedicated, scored, and persistent suggestion pipeline is needed.

## Decision

Create a new suggestion microservice within the existing FastAPI application, structured as a separate domain module:

- **New router**: `/api/v1/suggestions` at `backend/app/routers/v1/suggestions.py`, mounted in the `v1_router` with `include_router(suggestions.router, prefix="/suggestions", tags=["Suggestions v1"])`.
- **New service**: `SuggestionService` at `backend/app/services/suggestion_service.py`, responsible for generating, scoring, and persisting suggestions.
- **New DB table**: `suggestions` schema with columns:
  - `id` (UUID, primary key)
  - `user_id` (UUID, FK to `users`)
  - `document_id` (UUID, FK to `documents`)
  - `session_id` (UUID, nullable, FK to `generator_sessions`)
  - `block_id` (text, identifying the document block the suggestion targets)
  - `suggestion_type` (text enum: `rewrite`, `formatting`, `citation`, `structure`, `clarity`)
  - `original_text` (text)
  - `suggested_text` (text)
  - `score` (integer, 0–100)
  - `status` (text enum: `pending`, `accepted`, `rejected`, `dismissed`)
  - `model_used` (text, e.g. `"nvidia/nemotron-4-340b-instruct"`)
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)
- **Scoring**: Each suggestion receives a quality score (0–100) computed from a heuristic mix of:
  - Edit distance from original (lower distance → higher score for minor rewrites)
  - LLM self-consistency (3 rapid samples, pairwise agreement)
  - Block-type appropriateness (e.g., citation suggestions score higher on heading blocks)
- **Threshold filtering**: Suggestions below `settings.SUGGESTION_MIN_SCORE` (default: 45) are discarded pre-storage.
- **Caching**: Suggestions are cached in Redis with a 1-hour TTL. Cache key: `suggestion:{document_id}:{block_id}`. Cache invalidation on user accept/reject.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/suggestions/{document_id}` | List suggestions for a document |
| GET | `/api/v1/suggestions/{document_id}/{block_id}` | Get suggestion for a specific block |
| POST | `/api/v1/suggestions/generate` | Trigger suggestion generation for a document |
| PATCH | `/api/v1/suggestions/{suggestion_id}` | Accept/reject/dismiss a suggestion |
| DELETE | `/api/v1/suggestions/{suggestion_id}` | Delete a suggestion |

### Data Flow

```
POST /api/v1/suggestions/generate
  → SuggestionService.generate(document_id)
    → LLM call (generate_with_fallback)
    → Score & threshold filter
    → Store in `suggestions` table
    → Cache in Redis (TTL 1h)
    → Return list of scored suggestions
```

## Consequences

- **Schema migration** — Alembic revision required to create the `suggestions` table. The migration is additive (no existing tables modified).
- **Redis TTL** — The 1-hour cache TTL must be configured in `settings.py` as `SUGGESTION_CACHE_TTL = 3600`. If Redis is unavailable, suggestion generation degrades to database-only storage.
- **LLM cost** — Each `generate` call uses `generate_with_fallback` (NVIDIA NIM → Groq → DeepSeek). To control costs, a per-user rate limit of 10 suggestion generations per hour applies.
- **Preview integration** — The live-preview WebSocket is modified to emit suggestion-ready events (`event: suggestion_ready`) rather than blocking on generation. The frontend polls `GET /api/v1/suggestions/{document_id}` lazily.
- **Audit logging** — All suggestion accept/reject actions are logged via `audit_log_service.log` with action `suggestion_interaction`.
- **Frontend changes** — A new suggestion drawer component renders the scored list, allowing users to apply or dismiss individual suggestions.

## Compliance

This decision has been implemented and is verified by:
- `backend/tests/test_suggestion_service.py` — `SuggestionService` generation, scoring, threshold filtering
- `backend/tests/test_routers_suggestions.py` — all 5 suggestion API endpoints
- `backend/app/routers/v1/suggestions.py` — suggestion router mount at `/api/v1/suggestions`
- `backend/app/services/suggestion_service.py` — scoring heuristics, LLM integration
- `backend/app/models/suggestion.py` — suggestion model (UUID, user_id, document_id, block_id, etc.)
- `backend/tests/test_models_uncovered.py` — suggestion model validation

**See also:**
- [ADR 006: Celery Background Tasks](006-celery-background-tasks.md) — background task dispatch
- [ADR 008: LiteLLM LLM Routing](008-litellm-llm-routing.md) — provider fallback for LLM calls
- [ADR 002: Redis Realtime Backbone](002-redis-realtime-backbone.md) — suggestion cache (TTL 1h)
- [Suggestion Service API](#api-endpoints) — endpoint reference above
- [AI Architecture](../AI_ARCHITECTURE.md) — suggestion pipeline overview
