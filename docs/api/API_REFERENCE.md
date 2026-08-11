# ScholarForm AI — API Reference

## Table of Contents

- [Overview & Base URL](#overview--base-url)
- [API Route Map](#api-route-map)
- [Request Lifecycle & Sequence Architecture](#request-lifecycle--sequence-architecture)
- [Authentication Headers](#authentication-headers)
- [Documents API](#1-documents-api)
- [Generator API](#2-generator-api)
- [Synthesis API](#3-synthesis-api)
- [Citations API](#4-citations-api)
- [Templates API](#5-templates-api)
- [Quality Score API](#6-quality-score-api)
- [Webhooks API](#7-webhooks-api)
- [Users & API Keys](#8-users-api-keys)
- [Feedback API](#9-feedback-api)
- [Health & Metrics](#10-health--metrics)

---

## Overview & Base URL

ScholarForm AI exposes a RESTful API for manuscript formatting, paper generation, multi-document synthesis, citation style management, and platform administrative operations.

- **Development Base URL:** `http://localhost:8000`
- **Production Base URL:** `https://api.scholarform.ai`
- **API Version Prefix:** `/api/v1`

> [!IMPORTANT]
> All endpoints return responses in the standard `APIResponse` envelope: `{ "data": ..., "error": null, "request_id": "...", "timestamp": "..." }`. See the [Standardized Response Envelope](../architecture/SYSTEM_DESIGN.md#api-design--standardized-response-envelopes) section in SYSTEM_DESIGN.md.

---

## API Route Map

The diagram below shows all 16 router modules grouped by domain and their relationship to backend services.

```mermaid
flowchart LR
    subgraph Gateway["FastAPI Gateway /api/v1"]
        direction TB
        Docs["/documents\nUpload · Status · Preview\nDownload · Edit · Share"]
        Gen["/generator\nSessions · Messages\nOutline · RAG"]
        Synth["/synthesis\nMulti-doc merge\n& RAG synthesis"]
        Cite["/citations\nCSL search\n& CrossRef lookup"]
        Tmpl["/templates\nList · Get ·\nCustomize"]
        Quality["/quality\nScore · Report"]
        Hook["/webhooks\nSubscribe · Deliver\n& Logs"]
        Users["/users\nProfile · Keys\n& Usage"]
        Health["/health\nLiveness · Readiness"]
    end

    subgraph Services["Backend Services"]
        PipelineSvc["DocumentPipelineService"]
        GenSvc["GeneratorSessionService"]
        SynthSvc["SynthesisService"]
        CiteSvc["CitationAssemblyService"]
        StyleReg["StyleRegistry"]
        QualitySvc["QualityScoreService"]
        WebhookSvc["WebhookService"]
        UserSvc["UserService + APIKeyService"]
    end

    Docs --> PipelineSvc
    Gen --> GenSvc
    Synth --> SynthSvc
    Cite --> CiteSvc
    Tmpl --> StyleReg
    Quality --> QualitySvc
    Hook --> WebhookSvc
    Users --> UserSvc
```

---

## Request Lifecycle & Sequence Architecture

All incoming API requests pass through FastAPI middleware (CORS, Rate Limiter, Authentication) before routing to specific v1 endpoint controllers and business services.

```mermaid
sequenceDiagram
    autonumber
    actor Client as "API Client / Frontend"
    participant Gateway as "FastAPI Middleware("CORS / Security / RateLimiter")"
    participant Router as "V1 Router("/api/v1/*")"
    participant Service as "Business Service Layer"
    participant Downstream as "Database / Supabase / LLM / GROBID"
    participant Envelope as "ApiEnvelope[T] Builder"


    Client->>Gateway: HTTP Request("Method, Path, Bearer Token, Body/Files")
    alt Rate Limit Exceeded or Unauthorized Token
        Gateway-->>Client: 429 RATE_LIMITED / 401 UNAUTHORIZED ("APIResponse Envelope")
    else Request Allowed
        Gateway->>Router: Forward Validated Request
        Router->>Service: Dispatch to Endpoint Handler & Pydantic Schema
        Service->>Downstream: Perform Business Logic & DB / External Queries
        Downstream-->>Service: Return Execution Result / Payload
        Service->>Envelope: Construct success_response(data, request_id)
        Envelope-->>Client: HTTP 200/201/202 with Standard APIResponse Envelope
    end
```

---

## Authentication Headers

Authenticated endpoints require a Bearer token header issued by Supabase Auth:

```http
Authorization: Bearer <your_access_token>
```

For custom integrations using API keys, set the API key in the `Authorization` header:

```http
Authorization: Bearer amf_live_secret_key_here
```

Certain public routes (such as `/api/v1/health`, `/api/v1/config`, `/api/v1/templates`, and `/metrics`) do not require authentication headers.

---

## Response Envelope Standard (`ApiEnvelope[T]` / `APIResponse`)

All responses from `/api/v1` endpoints strictly wrap payloads in a standardized response envelope model (`APIResponse`).

### Envelope Fields

| Field | Type | Description |
| --- | --- | --- |
| `data` | `Any \| null` | Response payload object when request succeeds; `null` on error |
| `error` | `APIError \| null` | Structured error details when request fails; `null` on success |
| `request_id` | `str` | Unique request correlation identifier for distributed tracing |
| `timestamp` | `datetime` | UTC timestamp in ISO 8601 format when envelope was generated |

### Success Response Example (`HTTP 200 OK`)

```json
{
  "data": {
    "job_id": "job_987654321",
    "status": "processing",
    "filename": "manuscript.docx",
    "template": "ieee",
    "progress": 45
  },
  "error": null,
  "request_id": "req-8f7a9c12-3b4e",
  "timestamp": "2026-07-29T12:00:00Z"
}
```

### Error Response Example (`HTTP 422 Unprocessable Entity`)

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Manuscript structure validation failed: missing required title.",
    "details": {
      "missing_fields": ["title"],
      "sections_found": 3
    }
  },
  "request_id": "req-8f7a9c12-3b4e",
  "timestamp": "2026-07-29T12:00:00Z"
}
```

---

## Endpoints Reference (All 16 `/api/v1/` Router Modules)

### 1. Health Router (`/api/v1/health`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/health` | `GET` | No | Returns basic health status (`ok`) |
| `/api/v1/health/live` | `GET` | No | Liveness probe endpoint for Kubernetes / Cloud Run |
| `/api/v1/health/ready` | `GET` | No | Readiness probe checking Database, GROBID, and Redis connections |
| `/api/v1/health/detailed` | `GET` | No | Detailed health status of all dependent services |
| `/api/v1/health/admin` | `GET` | Admin | Administrative health breakdown with memory usage and system uptime |

---

### 2. Auth Router (`/api/v1/auth`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/auth/me` | `GET` | Yes | Get currently authenticated user profile and subscription metadata |
| `/api/v1/auth/signup` | `POST` | No | Register a new user account with email and password |
| `/api/v1/auth/login` | `POST` | No | Authenticate credentials and return JWT bearer token |
| `/api/v1/auth/forgot-password` | `POST` | No | Request password reset email / OTP code |
| `/api/v1/auth/verify-otp` | `POST` | No | Verify email/phone OTP code |
| `/api/v1/auth/reset-password` | `POST` | No | Complete password reset using verified OTP token |

---

### 3. Config Router (`/api/v1/config`)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/config` | `GET` | No | Exposes public runtime configuration, feature flags, max file sizes, and default rate limits |

---

### 4. Documents Router (`/api/v1/documents`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/documents/upload` | `POST` | Optional | Upload manuscript file (`multipart/form-data`) for automated formatting |
| `/api/v1/documents/upload/chunked` | `POST` | Optional | Initiate chunked upload session for large manuscripts (>10MB) |
| `/api/v1/documents/{jobId}/status` | `GET` | Optional | Poll document processing progress and current pipeline stage |
| `/api/v1/documents/{jobId}/summary` | `GET` | Optional | Retrieve extracted metadata summary (title, authors, word count, sections) |
| `/api/v1/documents/{jobId}/preview` | `GET` | Optional | Fetch rendered HTML body and CSS stylesheet for inline visual editor |
| `/api/v1/documents/{jobId}/compare` | `GET` | Optional | Fetch unified side-by-side diff comparing raw manuscript vs styled output |
| `/api/v1/documents/{jobId}/download` | `GET` | Optional | Download formatted document stream (`format=docx\|pdf\|latex`) |
| `/api/v1/documents/{jobId}/edit` | `POST` | Yes | Apply visual editor (TipTap/ProseMirror) modifications to active document job |
| `/api/v1/documents` | `GET` | Yes | List user's historical uploaded manuscripts with pagination |
| `/api/v1/documents/{jobId}` | `DELETE` | Yes | Delete manuscript document and associated storage artifacts |
| `/api/v1/documents/batch-upload` | `POST` | Yes | Process multiple manuscript files in a single batch request |

---

### 5. Templates Router (`/api/v1/templates`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/templates` | `GET` | No | List all 17 supported academic citation & formatting templates (IEEE, APA, Nature, etc.) |
| `/api/v1/templates/csl/search` | `GET` | No | Search CSL (Citation Style Language) repository by keyword |
| `/api/v1/templates/csl/fetch` | `GET` | No | Fetch CSL style XML definition by CSL identifier |
| `/api/v1/templates/csl/{styleId}` | `GET` | No | Get metadata and rules for a specific CSL citation style |
| `/api/v1/templates/custom` | `GET` | Yes | List user's custom created templates |
| `/api/v1/templates/custom` | `POST` | Yes | Upload or define a new custom formatting template |
| `/api/v1/templates/custom/{templateId}` | `PUT` | Yes | Update an existing custom template definition |
| `/api/v1/templates/custom/{templateId}` | `DELETE` | Yes | Remove custom formatting template |

---

### 6. AI Generator Router (`/api/v1/generator`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/generator/sessions` | `POST` | Yes | Initialize interactive AI paper drafting session (`202 Accepted`) |
| `/api/v1/generator/sessions` | `GET` | Yes | List active and historical generator sessions for user |
| `/api/v1/generator/sessions/{sessionId}` | `GET` | Yes | Get session details, paper topic, target style, and generated outline |
| `/api/v1/generator/sessions/{sessionId}/messages` | `GET` | Yes | Get message exchange history between user and drafting agent |
| `/api/v1/generator/sessions/{sessionId}/document` | `GET` | Yes | Retrieve current complete paper manuscript state |
| `/api/v1/generator/sessions/{sessionId}/download` | `GET` | Yes | Download generated manuscript as formatted DOCX or LaTeX |
| `/api/v1/generator/sessions/{sessionId}/events` | `GET` | Yes | Real-time Server-Sent Events (SSE) stream for live section generation |
| `/api/v1/generator/sessions/{sessionId}/messages` | `POST` | Yes | Send chat prompt or refinement query to ongoing session |
| `/api/v1/generator/sessions/{sessionId}/outline/approve` | `POST` | Yes | Approve proposed section outline and trigger full draft generation |
| `/api/v1/generator/sessions/{sessionId}/stop` | `POST` | Yes | Stop active background generation job |

---

### 7. Multi-Doc Synthesis Router (`/api/v1/synthesis`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/synthesis/sessions` | `POST` | Yes | Create multi-document synthesis session for 2-6 source PDFs (`202 Accepted`) |
| `/api/v1/synthesis/sessions/{sessionId}` | `GET` | Yes | Get multi-document synthesis session status and comparative matrix |
| `/api/v1/synthesis/sessions/{sessionId}/events` | `GET` | Yes | SSE stream broadcasting synthesis progress and section merging steps |
| `/api/v1/synthesis/sessions/{sessionId}/messages` | `POST` | Yes | Send prompt updates or focus adjustments to synthesis engine |

---

### 8. Feedback Router (`/api/v1/feedback`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/feedback` | `POST` | Optional | Submit user rating, bug report, or feature feedback (`201 Created`) |
| `/api/v1/feedback/summary` | `GET` | Admin | Get aggregate user satisfaction metrics and rating summaries |

---

### 9. Metrics Router (`/api/v1/metrics` & `/metrics`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/metrics` | `GET` | Admin | Retrieve operational API throughput, average latency, and error counts |
| `/api/v1/metrics/db` | `GET` | Admin | Retrieve database connection pool utilization and query performance statistics |
| `/api/v1/metrics/log-error` | `POST` | Optional | Client-side error reporting endpoint for frontend telemetry |
| `/metrics` | `GET` | No | Prometheus metrics scraper target (root level) |

---

### 10. AI Providers Router (`/api/v1/providers`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/providers` | `GET` | Yes | List all registered LLM providers (NVIDIA NIM, Groq, OpenRouter, Ollama) |
| `/api/v1/providers/health` | `GET` | Yes | Ping provider endpoints and check latency / key status |
| `/api/v1/providers/builtin` | `GET` | Yes | List pre-configured system LLM providers |
| `/api/v1/providers/{provider_id}/models` | `GET` | Yes | List available LLM model IDs for specific provider |
| `/api/v1/providers/{provider_id}/models/sync` | `POST` | Yes | Synchronize remote model list from provider API |
| `/api/v1/providers/custom` | `POST` | Yes | Register custom OpenAI-compatible LLM endpoint (`201 Created`) |
| `/api/v1/providers/custom` | `GET` | Yes | List user-registered custom LLM providers |
| `/api/v1/providers/custom/{provider_id}` | `GET` | Yes | Get configuration details for custom provider |
| `/api/v1/providers/custom/{provider_id}` | `PUT` | Yes | Update custom provider API base URL or credentials |
| `/api/v1/providers/custom/{provider_id}` | `DELETE` | Yes | Remove custom provider registration |
| `/api/v1/providers/test` | `POST` | Yes | Test custom provider endpoint connectivity and model availability |

---

### 11. API Keys Router (`/api/v1/keys`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/keys` | `POST` | Yes | Generate new API key with specific scopes (`201 Created`) |
| `/api/v1/keys` | `GET` | Yes | List active API keys associated with user account |
| `/api/v1/keys/{key_id}` | `GET` | Yes | Get API key metadata and creation details |
| `/api/v1/keys/{key_id}` | `PUT` | Yes | Update API key label or rate limit allocation |
| `/api/v1/keys/{key_id}` | `DELETE` | Yes | Revoke API key (`204 No Content`) |
| `/api/v1/keys/usage` | `GET` | Yes | Get aggregate usage statistics across all user keys |
| `/api/v1/keys/{key_id}/usage` | `GET` | Yes | Get detailed request usage breakdown for specific key |
| `/api/v1/keys/providers` | `GET` | Yes | Inspect BYOK (Bring Your Own Key) status for downstream LLMs |
| `/api/v1/keys/test` | `POST` | Yes | Validate API key string |

---

### 12. Live Stream Router (`/api/v1/stream`)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/stream/{jobId}` | `GET` | Optional | Server-Sent Events (SSE) stream delivering real-time document formatting logs and progress |

---

### 13. Billing Router (`/api/v1/billing`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/billing/webhook` | `POST` | Stripe | Webhook endpoint receiving Stripe payment and subscription events |
| `/api/v1/billing/subscription` | `GET` | Yes | Get active subscription plan, usage quota, and billing cycle |
| `/api/v1/billing/checkout-session` | `POST` | Yes | Create Stripe checkout session URL for upgrading tier |
| `/api/v1/billing/portal` | `POST` | Yes | Generate Stripe customer billing management portal link |

---

### 14. Activity Router (`/api/v1/activity`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/activity/recent` | `GET` | Yes | Fetch user's recent document processing and generation audit activity |
| `/api/v1/activity/summary` | `GET` | Yes | Retrieve aggregate usage activity summary by period |

---

### 15. AI Suggestions Router (`/api/v1/suggestions`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/suggestions/generate` | `POST` | Yes | Generate AI writing, grammar, and structural suggestions (`201 Created`) |
| `/api/v1/suggestions/document/{document_id}` | `GET` | Yes | List pending AI suggestions for a document |
| `/api/v1/suggestions/{suggestion_id}/accept` | `POST` | Yes | Accept a specific suggestion edit |
| `/api/v1/suggestions/{suggestion_id}/reject` | `POST` | Yes | Reject a specific suggestion edit |
| `/api/v1/suggestions/{suggestion_id}/dismiss` | `POST` | Yes | Dismiss suggestion without applying |
| `/api/v1/suggestions/{suggestion_id}/apply` | `POST` | Yes | Apply accepted suggestion into document body |
| `/api/v1/suggestions/history` | `GET` | Yes | Get suggestion audit resolution history |

---

### 16. Webhooks Router (`/api/v1/webhooks`)

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/webhooks` | `POST` | Yes | Register new outgoing webhook subscription (`201 Created`) |
| `/api/v1/webhooks` | `GET` | Yes | List active user webhook subscriptions |
| `/api/v1/webhooks/{sub_id}` | `GET` | Yes | Get webhook subscription details |
| `/api/v1/webhooks/{sub_id}` | `PUT` | Yes | Update target webhook URL or subscribed event filters |
| `/api/v1/webhooks/{sub_id}` | `DELETE` | Yes | Delete webhook subscription |
| `/api/v1/webhooks/test` | `POST` | Yes | Trigger dummy test event payload delivery to target URL |
| `/api/v1/webhooks/{sub_id}/deliveries` | `GET` | Yes | Get historical delivery logs and HTTP status codes for subscription |

---

## Standard Error Codes Summary

| Error Code | HTTP Status | Description |
| --- | --- | --- |
| `BAD_REQUEST` | 400 | Malformed client request parameters or invalid payload syntax |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication bearer token |
| `FORBIDDEN` | 403 | Insufficient permissions for requested resource or operation |
| `NOT_FOUND` | 404 | Target resource, document job, or template ID not found |
| `CONFLICT` | 409 | Resource state conflict (e.g., job already completed) |
| `PAYLOAD_TOO_LARGE` | 413 | Uploaded manuscript file exceeds max size limit (60MB) |
| `VALIDATION_ERROR` | 422 | Manuscript structure validation failed |
| `RATE_LIMITED` | 429 | Rate limit quota exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled internal server execution error |
| `NOT_IMPLEMENTED` | 501 | Endpoint or requested feature is not supported |
| `BAD_GATEWAY` | 502 | Downstream gateway or service integration failure |
| `SERVICE_UNAVAILABLE` | 503 | Dependent downstream service (DB, GROBID, LLM) unavailable |

## API Examples

See the full curl examples and response formats below:

<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — API Reference
description: Complete v1 API reference with curl examples for all 19 endpoints
sidebar_position: 5
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: monthly
last_updated: July 2026
---

# ScholarForm AI — API Reference  

> **Base URL:** `http://localhost:8000` (dev) | `https://api.scholarform.ai` (prod)  
> **Auth:** `Authorization: Bearer <supabase_access_token>` on authenticated routes  
> **Versioning:** `/api/v1/` prefix. Legacy routes (without `/v1/`) carry `Deprecation` response headers.

> **See also:** [API Versioning](../archive/API_VERSIONING.md), [Architecture](../architecture/ARCHITECTURE.md), [ADR 003](../adr/003-api-versioning-strategy.md)

---

## Response Envelope (All v1 Endpoints)

All v1 responses follow the standard envelope:

```json
{
  "success": true,
  "data": { ... },
  "request_id": "abc-123"
}
```

Error responses:

```json
{
  "success": false,
  "error": { "code": "VALIDATION_ERROR", "message": "..." },
  "request_id": "abc-123"
}
```

---

## Table of Contents

- [Formatter Endpoints](#formatter-endpoints)
- [Template Endpoints](#template-endpoints)
- [Generator Endpoints](#generator-endpoints)
- [Synthesis Endpoints](#synthesis-endpoints)
- [Live Preview (WebSocket)](#live-preview-websocket)
- [Auth Endpoints](#auth-endpoints)
- [Billing Endpoints](#billing-endpoints)
- [Health & Metrics](#health--metrics)
- [Deprecated Endpoints](#deprecated-endpoints)

---

## Formatter Endpoints

### POST /api/v1/documents/upload

Upload and process a document.

```
Content-Type: multipart/form-data
Body: file (binary), template (string), options (JSON)
Response: { success: true, data: { job_id, status: "processing" } }
```

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@manuscript.docx" \
  -F "template=ieee" \
  -F 'options={"page_numbers":true,"cover_page":false}'
```

- Virus scanning runs before processing (ClamAV)
- Returns `job_id` in <400ms; processing continues in background

### GET /api/v1/documents/{job_id}/status

Poll processing status.

```bash
curl http://localhost:8000/api/v1/documents/abc-123/status \
  -H "Authorization: Bearer $TOKEN"
```

```json
{ "success": true, "data": { "status": "completed", "progress": 100, "current_stage": "export", "stages": ["upload", "validate", "format", "export"] } }
```

### GET /api/v1/documents/{job_id}/preview

Get rendered HTML preview.

```bash
curl http://localhost:8000/api/v1/documents/abc-123/preview \
  -H "Authorization: Bearer $TOKEN"
```

```json
{ "success": true, "data": { "html": "<div>...</div>", "css": ".article {...}" } }
```

### GET /api/v1/documents/{job_id}/compare

Before/after diff view.

```bash
curl http://localhost:8000/api/v1/documents/abc-123/compare \
  -H "Authorization: Bearer $TOKEN"
```

### GET /api/v1/documents/{job_id}/download

Download processed document.

```bash
curl -o formatted.docx http://localhost:8000/api/v1/documents/abc-123/download?format=docx \
  -H "Authorization: Bearer $TOKEN"
```

Query: `format=docx|pdf|latex`

### POST /api/v1/documents/{job_id}/edit

Save TipTap editor content back to job.

```bash
curl -X POST http://localhost:8000/api/v1/documents/abc-123/edit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "<p>Revised text</p>"}'
```

### GET /api/v1/documents

List user's documents (paginated).

```bash
curl "http://localhost:8000/api/v1/documents?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### DELETE /api/v1/documents/{id}

Delete a document and its associated storage files.

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/abc-123 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Template Endpoints

### GET /api/v1/templates

List all 17 templates with metadata and preview CSS.

```bash
curl http://localhost:8000/api/v1/templates
```

```json
{ "success": true, "data": [{ "name": "ieee", "displayName": "IEEE", "description": "IEEE conference format", "preview_css": "..." }] }
```

### GET /api/v1/templates/{name}

Get a specific template's rules and preview CSS.

```bash
curl http://localhost:8000/api/v1/templates/ieee
```

---

## Generator Endpoints

### POST /api/v1/generator/sessions

Create a generator session.

```bash
curl -X POST http://localhost:8000/api/v1/generator/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_type": "agent", "template": "ieee", "prompt": "Write a paper about ML"}'
```

```json
{ "success": true, "data": { "session_id": "xyz-456", "status": "started" } }
```

### GET /api/v1/generator/sessions/{id}

Get session state and progress.

```bash
curl http://localhost:8000/api/v1/generator/sessions/xyz-456 \
  -H "Authorization: Bearer $TOKEN"
```

### GET /api/v1/generator/sessions/{id}/events

SSE stream for real-time progress events.

```bash
curl -N http://localhost:8000/api/v1/generator/sessions/xyz-456/events \
  -H "Authorization: Bearer $TOKEN"
```

### POST /api/v1/generator/sessions/{id}/messages

Send a message for agent chat or RAG Q&A.

```bash
curl -X POST http://localhost:8000/api/v1/generator/sessions/xyz-456/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Expand the methodology section"}'
```

### POST /api/v1/generator/sessions/{id}/outline/approve

Approve generated outline to proceed to section generation.

```bash
curl -X POST http://localhost:8000/api/v1/generator/sessions/xyz-456/outline/approve \
  -H "Authorization: Bearer $TOKEN"
```

Response is an SSE stream that begins writing sections.

---

## Synthesis Endpoints

### POST /api/v1/synthesis/sessions

Create a multi-doc synthesis session (2-6 PDFs).

```bash
curl -X POST http://localhost:8000/api/v1/synthesis/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf"
```

### GET /api/v1/synthesis/sessions/{id}/events

SSE stream for synthesis pipeline stages.

```bash
curl -N http://localhost:8000/api/v1/synthesis/sessions/xyz-456/events \
  -H "Authorization: Bearer $TOKEN"
```

---

## Live Preview (WebSocket)

### WS /api/v1/preview/ws/{session_id}

Real-time preview WebSocket connection.

```javascript
// Node.js example
const WebSocket = require('ws');
const ws = new WebSocket('ws://localhost:8000/api/v1/preview/ws/xyz-456');
ws.on('open', () => ws.send(JSON.stringify({ content: "<p>Hello</p>", template: "ieee" })));
ws.on('message', (data) => console.log(JSON.parse(data).html));
```

Target RTT: <80ms.

---

## Auth Endpoints

### POST /api/v1/auth/signup

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'
```

### POST /api/v1/auth/login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'
```

```json
{ "success": true, "data": { "access_token": "eyJ...", "user": { "id": "...", "email": "..." } } }
```

---

## Billing Endpoints

### POST /api/v1/billing/webhook

Stripe webhook handler. Requires `STRIPE_WEBHOOK_SECRET` in env.

```bash
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
```

### GET /api/v1/billing/portal

Stripe billing portal redirect URL.

```bash
curl http://localhost:8000/api/v1/billing/portal \
  -H "Authorization: Bearer $TOKEN"
```

```json
{ "success": true, "data": { "url": "https://billing.stripe.com/session/..." } }
```

---

## Health & Metrics

### GET /api/v1/health

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "ok",
  "services": { "redis": "ok", "db": "ok", "chromadb": "ok" }
}
```

## Performance Benchmarks

| Endpoint | P50 | P95 | P99 | Notes |
| ---------- | ----- | ----- | ----- | ------- |
| `/api/v1/health/live` | 5ms | 12ms | 25ms | No auth, no DB |
| `/api/v1/templates` | 15ms | 40ms | 80ms | Cached |
| `/api/v1/documents/upload` | 350ms | 800ms | 2s | Includes virus scan |
| `/api/v1/documents/{id}/status` | 8ms | 20ms | 50ms | DB lookup only |
| `/api/v1/documents/{id}/download` | 50ms | 150ms | 400ms | File read + stream |
| `/api/v1/synthesis/sessions` | 500ms | 3s | 8s | 2-6 PDF embed + LLM |
| `/api/v1/generator/sessions` | 200ms | 1s | 3s | LLM task parsing |
| `POST /api/v1/preview/ws` | 40ms | 70ms | 120ms | HTML render, no DOCX |
| `POST /auth/login` | 350ms | 600ms | 1s | Supabase OTP/OAuth |

**Targets:** Health endpoints < 50ms P95. Document operations > 400ms delegated to Celery.

### GET /metrics

Prometheus metrics endpoint (not authenticated).

```bash
curl http://localhost:8000/metrics
```

---

## Deprecated Endpoints

Legacy routes (without `/v1/` prefix) are still active but return a `Deprecation` response header. See `backend/app/routers/deprecation.py`. Clients should migrate to `/api/v1/` paths.

## Related Documentation

- [AI Architecture](../architecture/AI_ARCHITECTURE.md)
- [Frontend Architecture](../architecture/FRONTEND_ARCHITECTURE.md)
- [Realtime Architecture](../architecture/REALTIME_ARCHITECTURE.md)
- [Chroma RAG Architecture](../architecture/CHROMA_RAG_ARCHITECTURE.md)
- [Database Architecture](../architecture/DATABASE_ARCHITECTURE.md)
- [API Reference](API.md)

## Detailed Architecture & Workflows

### Architecture Overview

The API follows a unified layered design with all endpoints under `/api/v1`:

- Single `v1_router` manages all endpoint routing with proper prefixing
- Services orchestrate business logic and integrate with external systems
- Pipelines handle document processing, generation, and synthesis
- Real-time subsystem emits enhanced events via Redis Pub/Sub to SSE clients

### API Flow Diagram

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as API Gateway
    participant S as Service
    participant DB as Database
    C->>GW: HTTP Request (api_envelope)
    GW->>GW: Rate Limit & Auth Check
    GW->>S: Route Request
    S->>DB: Query Data
    DB-->>S: Data
    S-->>GW: Response Model (Pydantic)
    GW-->>C: Standard JSON Response
```

### Authentication and Authorization

- Base path: `/api/v1/auth`
- Requires Supabase authentication; endpoints return user info or manage auth lifecycle
- Protected endpoints require a valid session with enhanced error handling

### Rate Limiting and Abuse Detection

- Global rate limiter: 60 requests per minute with enhanced enforcement
- Tier-based rate limiting: guest daily limit configurable with improved tier management
- Abuse detection records generation requests and LLM calls with enhanced monitoring

### Real-Time Communication (SSE)

- Base path: `/api/v1/stream`
- Clients establish an SSE connection to receive progress updates and notifications
- Events are published to Redis channels and forwarded to connected clients with improved reliability
