# System Design & Architecture

## Design Principles

1. **Separation of Concerns**: Modular decoupling between route controllers (`routers/v1/`), service layer (`services/`), database repositories (`db/repositories/`), and document processing pipeline (`pipeline/`).
2. **Extensibility**: New journal styles, document parsers, and LLM backends can be registered without modifying core engine logic.
3. **API-First Architecture**: Unified FastAPI backend serving Next.js 16 frontend, Python SDK, and Rich-powered CLI.
4. **Defensive Processing**: Built-in Pydantic v2 validation, ClamAV virus scanning, rate limiting, and standard response envelopes (`api_envelope`).

---

## API Design & Response Standardization

### Base Path & Conventions

- Base path prefix: `/api/v1/`
- Every v1 API response is wrapped in the standard `api_envelope` (`APIResponse`).

### Standard Response Envelopes

**Success Envelope:**
```json
{
  "data": { ... },
  "error": null,
  "request_id": "req-9b8a7c6d",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

**Error Envelope:**
```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Manuscript title is required",
    "details": {
      "field": "title",
      "rule": "min_length_1"
    }
  },
  "request_id": "req-9b8a7c6d",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

---

## Database Schema & Data Persistence

ScholarForm AI uses **Supabase PostgreSQL** for relational persistence and state management across all user activities, documents, sessions, and auditing.

Repository implementations in `backend/app/db/repositories/` manage entity operations:

```
Supabase (PostgreSQL)
├── users (ID, email, auth provider, settings)
├── documents / document_jobs (ID, user_id, status, file_path, template, quality_score, metadata)
├── generator_sessions (ID, user_id, session_type, prompt, template, status, current_step)
├── generator_messages (ID, session_id, role, content, timestamp)
├── synthesis_sessions (ID, user_id, source_files, output_summary, status)
├── issues (tracking_number, title, description, category, severity, status, reporter)
├── audit_logs (id, user_id, action, path, method, status_code, ip_address, timestamp)
└── api_keys (id, user_id, key_hash, name, rate_limit, created_at)
```

Vector embeddings for paper generation and RAG retrieval are stored in **ChromaDB** (`session_vector_store.py`).

---

## Security Model

### Authentication & Authorization

- **Supabase Auth**: JWT verification using public JWKS endpoints (`backend/app/security/jwt.py`).
- **API Keys**: Header-based authentication (`Authorization: Bearer <key>`) with rate limiting per key tier (`api_key_rate_limiter.py`).

### Input Security & File Processing

- **Virus Scanning**: Uploaded manuscripts pass through ClamAV virus scanning (`CLAMAV_HOST` / `CLAMAV_PORT`) before ingestion.
- **File Validation**: Strict file type verification (.docx, .pdf, .tex, .md, .html, .txt) and file size checks (up to 60MB).
- **Sanitization**: TipTap HTML previews are sanitized against XSS prior to rendering.

---

## Logging, Monitoring & Observability

### Structured Logging

- JSON-formatted structured logs in production (`ENABLE_STRUCTURED_LOGGING=true`).
- Correlation via request IDs (`request_id`) attached to all HTTP requests and background Celery tasks.

### Real-Time Monitoring & Prometheus Metrics

- **Metrics Endpoint**: `/metrics` exposes system and request metrics using `prometheus_fastapi_instrumentator`.
- **Persona & Outcome Tracking**: Request counts, error rates, and processing latencies labeled by persona (`formatter`, `authoring`, `synthesis`, `billing`, `templates`) and outcome (`success`, `error`).

### Sentry Error Tracking

- **Sentry Integration**: Active error logging via `sentry-sdk` configured through `SENTRY_DSN` in `backend/app/core/sentry.py`.
