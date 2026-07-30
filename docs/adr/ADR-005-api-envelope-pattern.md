# ADR-005: Consistent API Envelope Pattern

- **Status:** Accepted
- **Date:** 2026-01-25
- **Author:** ScholarForm AI Engineering Team

## Context

ScholarForm AI exposes 39 API routes across two API versions (v1 and v2), serving both the Next.js frontend and external integrations. The API must provide:

- A consistent response structure that clients can depend on regardless of endpoint
- Clear error reporting with machine-readable codes and human-readable messages
- Request tracing for debugging distributed formatting pipelines
- Backward-compatible evolution from v1 to v2

The team evaluated three approaches: raw responses (return data directly), a custom envelope pattern, and a standardized envelope used consistently across all routes.

## Decision

We adopted a **consistent JSON envelope** for every API response:

```json
{
  "data": { ... },
  "error": null,
  "request_id": "req_abc123",
  "timestamp": "2026-01-25T14:30:00Z"
}
```

On error, the envelope carries structured error information:

```json
{
  "data": null,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Retry after 30 seconds.",
    "details": { "retry_after": 30 }
  },
  "request_id": "req_def456",
  "timestamp": "2026-01-25T14:30:05Z"
}
```

| Criterion | Raw Response | Ad-hoc Envelope | Standard Envelope |
| ----------- | ------------- | ----------------- | ------------------- |
| Consistency across endpoints | ❌ Varies | ️ Inconsistent | ✅ Uniform |
| Machine-readable errors | ❌ Ad-hoc | ️ Partial | ✅ Structured |
| Request tracing | ❌ Missing | ️ Sometimes | ✅ Always |
| Version evolution | ❌ Breaking | ️ Fragile | ✅ Compatible |
| Client code simplicity | ✅ Simple | ️ Mixed | ️ Wrapper needed |

Raw responses were rejected because they force every client to implement bespoke error handling for each endpoint. An ad-hoc approach was rejected because it would inevitably drift over time as different engineers add endpoints. A standardized envelope enforced at the framework level (via FastAPI exception handlers and response models) guarantees consistency.

## Consequences

**Positive:**

- Single error-handling path in the frontend — a thin wrapper extracts `data` or throws on `error`, regardless of endpoint
- `request_id` in every response enables distributed tracing across Celery workers, LLM providers, and database calls
- Structured error codes (`RATE_LIMITED`, `VALIDATION_ERROR`, `NOT_FOUND`, etc.) support internationalized error messages on the frontend
- Version evolution — v2 can add envelope fields without breaking v1 clients (new fields are additive)
- Consistent pagination envelope (`{ data: [...], error, request_id, timestamp, pagination: { page, per_page, total } }`) for list endpoints
- FastAPI `response_model` and custom `Response` base class enforce the pattern at compile time, not just convention

**Negative:**

- Bandwidth overhead — every response includes envelope fields (~100 bytes), which adds up for paginated list responses with hundreds of items
- Frontend requires a response interceptor or client wrapper to unwrap the envelope on every request
- Error handling in middleware adds latency to every request path, even for success responses
- Envelope versioning — if the envelope format itself needs to change, all clients must be updated simultaneously
- Nested `data` key adds one level of indentation in JSON, making raw `curl` debugging slightly more verbose

## Compliance

This decision has been implemented and is verified by:

- `backend/tests/test_api_envelope.py` — envelope structure, error format, pagination
- `backend/tests/test_routers_enterprise.py` — all 39 routes return consistent envelope
- `backend/tests/test_error_handling.py` — structured error codes and `request_id`
- `backend/app/middleware/error_handling.py` — `build_error_response()` function
- `backend/app/schemas/response.py` — `APIResponse` and `ErrorResponse` Pydantic models
- `backend/app/routers/v1/__init__.py` — envelope enforcement via `response_model`

## Cross-References

- [ADR 003: API Versioning Strategy](003-api-versioning-strategy.md) — version prefix
- [API Error Handling](../ERROR_HANDLING.md) — structured error code reference
- [API Reference](../API.md) — endpoint documentation with envelope examples
