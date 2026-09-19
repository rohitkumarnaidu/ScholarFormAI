<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI — API Response Envelope Specification (`SPEC`)

> **AUTHORITATIVE INTERFACE CONTRACT**  
> Every REST endpoint under the `/api/v1/` and `/api/v2/` namespaces MUST return responses conforming to this envelope specification.  
> Direct or ad-hoc raw JSON payloads are prohibited on all client-facing routes.

---

## 1. Envelope Schema

All API responses are serialized according to the standard envelope schema:

```json
{
  "data": { ... } | [ ... ] | null,
  "error": {
    "code": "STRING_ENUM",
    "message": "Human-readable description",
    "details": { ... } | null
  } | null,
  "request_id": "req_uuid4_string",
  "timestamp": "YYYY-MM-DDTHH:MM:SS.ffffffZ"
}
```

### Fields Definition

| Field | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `data` | `Any` | Yes | The payload object or list on successful operations. MUST be `null` when `error` is present. |
| `error` | `ErrorDetail` | Yes | Error object on failures. MUST be `null` when `data` is present. |
| `request_id` | `str` | No | Unique correlation UUID assigned by `RequestIdMiddleware`. Propagated in `X-Request-Id` response header. |
| `timestamp` | `str` | No | ISO 8601 UTC timestamp of response generation. |

---

## 2. Success Envelope Example

`GET /api/v1/documents/job_123/status` -> HTTP 200 OK

```json
{
  "data": {
    "job_id": "job_123",
    "status": "completed",
    "template": "ieee",
    "progress_percentage": 100,
    "download_url": "/api/v1/documents/job_123/download"
  },
  "error": null,
  "request_id": "req_7a3d9e21-0bf4-4f12-9c32-b7e1c8d0a5f9",
  "timestamp": "2026-09-19T14:30:00.123456Z"
}
```

---

## 3. Error Envelope Example

`POST /api/v1/documents/upload` -> HTTP 422 Unprocessable Entity

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field": "template",
      "issue": "Template 'nature-neuro' not found. Available: ieee, acm, apa, nature, springer."
    }
  },
  "request_id": "req_5f2b8a10-2de1-4e89-a1b7-c9d3e8f1b4a2",
  "timestamp": "2026-09-19T14:30:05.654321Z"
}
```

---

## 4. Implementation Reference

- **Pydantic Model:** `backend/app/schemas/api_envelope.py` (`ApiResponse[T]`, `ErrorDetail`)
- **Exception Handlers:** `backend/app/main.py` (`build_error_response`)
- **Frontend Interceptor:** `frontend/src/services/api.v1.js` (`unwrapEnvelope`)
