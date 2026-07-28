# ScholarForm AI — API Reference

## Base URL

- Development: `http://localhost:8000`
- Production: `https://api.scholarform.ai`

All modern endpoints are prefixed with `/api/v1`.

## Authentication

Authentication is performed via Bearer tokens (Supabase JWT):

```http
Authorization: Bearer <your_access_token>
```

Certain public routes (such as health checks, metrics, and template listings) do not require authentication headers.

---

## Response Envelope Standard (`api_envelope`)

All `/api/v1` API responses use a standard response envelope schema (`APIResponse`).

### Success Response Format

```json
{
  "data": {
    "job_id": "doc_987654321",
    "status": "processing"
  },
  "error": null,
  "request_id": "req-8f7a9c12-3b4e",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

### Error Response Format

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid manuscript structure or missing required section fields.",
    "details": {
      "missing_fields": ["title"]
    }
  },
  "request_id": "req-8f7a9c12-3b4e",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

---

## Endpoints

### Formatter & Document Management

#### Upload & Process Document
`POST /api/v1/documents/upload`

Uploads a manuscript file (DOCX, PDF, LaTeX, MD, HTML, TXT) for parsing and formatting.

- **Content-Type:** `multipart/form-data`
- **Body Params:**
  - `file`: (binary, required) The manuscript file
  - `template`: (string, optional, default `"ieee"`) Target template ID
  - `options`: (JSON string, optional) Formatting configuration

**Response Envelope Data:**
```json
{
  "data": {
    "job_id": "job_123456789",
    "status": "processing",
    "filename": "manuscript.docx",
    "template": "ieee"
  },
  "error": null,
  "request_id": "req-101",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

#### Poll Processing Status
`GET /api/v1/documents/{job_id}/status`

Retrieves the lifecycle and progress status of an active formatting job.

**Response Envelope Data:**
```json
{
  "data": {
    "job_id": "job_123456789",
    "status": "completed",
    "progress": 100,
    "current_stage": "export",
    "stages": ["upload", "validate", "format", "export"]
  },
  "error": null,
  "request_id": "req-102",
  "timestamp": "2026-07-28T21:00:05Z"
}
```

#### Get Rendered HTML Preview
`GET /api/v1/documents/{job_id}/preview`

Renders and returns formatted manuscript HTML and inline CSS.

**Response Envelope Data:**
```json
{
  "data": {
    "html": "<div class=\"manuscript-body\">...</div>",
    "css": ".manuscript-body { font-family: 'Times New Roman'; }"
  },
  "error": null,
  "request_id": "req-103",
  "timestamp": "2026-07-28T21:00:06Z"
}
```

#### Get Diff / Comparison
`GET /api/v1/documents/{job_id}/compare`

Returns side-by-side or unified diff data between original input and formatted output.

#### Download Processed Document
`GET /api/v1/documents/{job_id}/download`

Downloads the formatted file.
- **Query Params:** `format` (`docx`, `pdf`, `latex`)
- **Returns:** Direct file attachment stream or download envelope payload.

#### Submit Incremental Edits
`POST /api/v1/documents/{job_id}/edit`

Saves live visual editor (TipTap/ProseMirror) modifications back to the document job.

---

### Templates

#### List Templates
`GET /api/v1/templates`

Lists all 17 supported academic templates.

**Response Envelope Data:**
```json
{
  "data": [
    {
      "id": "ieee",
      "name": "IEEE Conference",
      "citation_format": "numeric",
      "description": "Two-column conference format"
    },
    {
      "id": "apa",
      "name": "APA 7th Edition",
      "citation_format": "author-date",
      "description": "American Psychological Association format"
    }
  ],
  "error": null,
  "request_id": "req-201",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

---

### AI Research Generator

#### Create Generator Session
`POST /api/v1/generator/sessions`

Initializes an interactive AI paper drafting session.

#### Stream Generator Events (SSE)
`GET /api/v1/generator/sessions/{id}/events`

Server-Sent Events endpoint streaming real-time paper generation events.

#### Send Session Message / Chat
`POST /api/v1/generator/sessions/{id}/messages`

Appends prompt adjustments or queries to an ongoing generator session.

---

### Multi-Doc Synthesis

#### Create Synthesis Session
`POST /api/v1/synthesis/sessions`

Accepts multiple source PDFs (2-6 documents) for automated synthesis into a single manuscript.

---

### Health & Monitoring

#### Health Check
`GET /api/v1/health`

Returns application service health states.

#### Metrics Endpoint
`GET /metrics`

Exposes Prometheus system and operational metrics (unauthenticated).

---

## Error Codes

| Error Code | HTTP Status | Description |
|---|---|---|
| `BAD_REQUEST` | 400 | Malformed request parameters or invalid JSON body |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication token |
| `FORBIDDEN` | 403 | Insufficient permissions for requested resource |
| `NOT_FOUND` | 404 | Resource, job, or template ID not found |
| `CONFLICT` | 409 | Resource state conflict (e.g. duplicate job) |
| `PAYLOAD_TOO_LARGE` | 413 | Uploaded file exceeds size limit |
| `VALIDATION_ERROR` | 422 | Manuscript structure validation failed |
| `RATE_LIMITED` | 429 | Rate limit quota exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled server error |
| `SERVICE_UNAVAILABLE` | 503 | Dependent downstream service (e.g. LLM provider) unavailable |
