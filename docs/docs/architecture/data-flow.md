<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Data Flow Architecture

## Table of Contents

- [Format Request Flow](#format-request-flow)
- [Validation Flow](#validation-flow)
- [Preview Flow](#preview-flow)
- [Real-Time SSE Event Stream](#real-time-sse-event-stream)

---

## Format Request Flow

The following sequence diagram illustrates the end-to-end lifecycle of a manuscript formatting request from any client (Web UI, CLI, or Python SDK) through the API Gateway to persistent storage.

```mermaid
sequenceDiagram
    autonumber
    actor User as "Client (Web / CLI / SDK)"
    participant API as "FastAPI Gateway"
    participant Services as "Pipeline Services"
    participant Storage as "Supabase / Local Disk"

    User->>API: POST /api/v1/format (Manuscript payload + Style)
    activate API
    API->>Services: Parse & Structure Manuscript
    activate Services
    Services-->>API: Structured Manuscript AST
    API->>Services: Validate against CSL Style Rules
    Services-->>API: Validation Result (Pass / Warn)
    API->>Services: Compile DOCX Document (python-docx)
    Services-->>API: Compiled DOCX Binary
    deactivate Services
    API->>Storage: Save Artifact to Storage
    activate Storage
    Storage-->>API: Storage URI / Reference
    deactivate Storage
    API-->>User: 200 OK + DOCX Download Stream
    deactivate API
```

> [!IMPORTANT]
> Large manuscripts (>25 MB) are automatically offloaded to Celery background workers. Clients receive a `task_id` and can monitor progress via SSE streaming or polling `/api/v1/documents/status/{task_id}`.

---

## Validation Flow

Before DOCX compilation, manuscripts pass through a rigorous multi-stage validation check to verify citation structure, figure numbering, and publisher rules.

```mermaid
sequenceDiagram
    autonumber
    actor User as "Client App"
    participant API as "REST API (/api/v1/validate)"
    participant Val as "ValidatorService"
    participant Registry as "StyleRegistry"

    User->>API: POST /api/v1/validate (JSON / DOCX)
    activate API
    API->>Val: Validate Document Structure
    activate Val
    Val->>Registry: Load Rules for Academic Style
    Registry-->>Val: Style Constraints
    Val->>Val: Execute Reference & Citation Audit
    Val->>Val: Check Figure & Table Numbering
    Val-->>API: Validation Report (valid, errors[], warnings[])
    deactivate Val
    API-->>User: 200 OK (Validation Envelope)
    deactivate API
```

---

## Preview Flow

To provide instant visual feedback without downloading `.docx` binaries, the Preview Renderer generates high-fidelity HTML representations.

```mermaid
sequenceDiagram
    autonumber
    actor User as "Next.js Web UI"
    participant API as "FastAPI (/api/v1/preview)"
    participant Formatter as "PreviewRenderer"

    User->>API: POST /api/v1/preview (Manuscript + Style)
    activate API
    API->>Formatter: Generate Styled HTML HTML-DOM
    activate Formatter
    Formatter-->>API: Rendered HTML Snippets
    deactivate Formatter
    API-->>User: 200 OK { html: "<!DOCTYPE html>..." }
    deactivate API
```

---

## Real-Time SSE Event Stream

For long-running pipeline processing, the backend emits Server-Sent Events (SSE) to update the client in real time.

```mermaid
flowchart LR
    Worker["Celery Worker\n(Document Pipeline)"] -->|Publish Status| Redis[("Redis Pub/Sub\nChannel: doc_progress")]
    Redis -->|Subscribe| SSE["FastAPI SSE Endpoint\n(/api/v1/documents/stream)"]
    SSE -->|Event Stream| Client["Next.js UI\nLive Progress Bar"]

    style Worker fill:#4a2a5c,color:#fff
    style Redis fill:#5c3a1a,color:#fff
    style SSE fill:#1a4a3c,color:#fff
    style Client fill:#1a3a5c,color:#fff
```
