# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

All responses follow the standard `api_envelope` schema (`APIResponse`).

---

## Response Envelope Schema

### Success Response

```json
{
  "data": { ... },
  "error": null,
  "request_id": "req-12345",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

### Error Response

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Detailed error message",
    "details": { ... }
  },
  "request_id": "req-12345",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

---

## Core v1 Endpoints

### Document Formatter

#### `POST /documents/upload`
Upload and format a manuscript document.
- **Content-Type:** `multipart/form-data`
- **Fields:** `file` (binary), `template` (string), `options` (JSON string)
- **Response:** `200 OK` with `{ "data": { "job_id": "...", "status": "processing" } }`

#### `GET /documents/{job_id}/status`
Get real-time job processing progress and stage.

#### `GET /documents/{job_id}/preview`
Get rendered HTML and inline stylesheet for live document preview.

#### `GET /documents/{job_id}/compare`
Get visual diff comparison payload between original input and formatted output.

#### `GET /documents/{job_id}/download`
Download formatted DOCX, PDF, or LaTeX output.

#### `POST /documents/{job_id}/edit`
Save inline TipTap visual editor updates back to the document job.

---

### Templates

#### `GET /templates`
List all 17 available publication templates (IEEE, APA, Nature, Springer, Elsevier, etc.).

#### `GET /templates/{name}`
Retrieve specific template formatting rules and preview styles.

---

### AI Generator & Synthesis

#### `POST /generator/sessions`
Start a new AI paper generation session.

#### `GET /generator/sessions/{id}/events`
SSE event stream for real-time paper drafting and section generation progress.

#### `POST /generator/sessions/{id}/messages`
Send chat prompt or RAG query to active generator session.

#### `POST /synthesis/sessions`
Synthesize 2-6 source PDFs into a single unified review paper.

---

## Error Codes

| Code | HTTP Status | Description |
|---|---|---|
| `BAD_REQUEST` | 400 | Invalid request formatting |
| `UNAUTHORIZED` | 401 | Missing or invalid auth credentials |
| `FORBIDDEN` | 403 | Action not permitted for role |
| `NOT_FOUND` | 404 | Target resource or job ID not found |
| `CONFLICT` | 409 | Resource state conflict |
| `PAYLOAD_TOO_LARGE` | 413 | Uploaded file size limit exceeded |
| `VALIDATION_ERROR` | 422 | Manuscript structure validation failed |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Server-side execution exception |
| `SERVICE_UNAVAILABLE` | 503 | Upstream AI provider or database unavailable |
