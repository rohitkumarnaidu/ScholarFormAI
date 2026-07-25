<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: Pipeline Architecture
description: How the 12-stage formatting pipeline processes documents end-to-end
sidebar_position: 3
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# Pipeline Architecture

## Overview

The document formatter pipeline transforms unstructured academic manuscripts into journal-formatted DOCX output through 12 sequential stages:

```mermaid
graph LR
    A[Upload] --> B[Parse]
    B --> C[Structure]
    C --> D[Classify]
    D --> E[NLP]
    E --> F[Validate]
    F --> G[Format]
    G --> H[Export]
    H --> I[Deliver]
```

## Stage Breakdown

### 1. Upload (`<400ms`)
- ClamAV virus scan
- MIME + magic byte + extension tri-validation
- 50MB file size limit
- Returns `job_id` immediately; processing continues in background

### 2. Parse
Three-tier PDF parser fallback:
1. **GROBID** (Docker, ~1.5GB RAM) — highest quality, disabled by default (`GROBID_ENABLED=false`)
2. **Docling** (IBM, Python) — primary parser, handles most formats
3. **PyMuPDF** (fitz) — final fallback, pure Python, no external deps

DOCX files skip this stage (parsed directly by `python-docx`).

### 3. Structure Detection
Identifies document sections (abstract, introduction, methods, results, discussion, references) using:
- Heading hierarchy analysis
- Keyword pattern matching
- Layout analysis (for PDFs)

### 4. Block Classification
Optional (disabled by default: `USE_LLM_CLASSIFICATION=false`):
- LLMClassifier model classifies each block as IMRaD section type
- When disabled, rule-based classification is used

### 5. NLP Enhancement
- Keyword extraction (YAKE) for metadata enrichment
- Entity recognition (spaCy) for author names, affiliations, citations
- Abstract summarization (if LLM available)

### 6. Validation
- Structure completeness check (required sections present?)
- Citation format validation
- Template variable validation against `contract.yaml`
- Schema conformance

### 7. Format & Render
- Template selection (17+ built-in)
- Jinja2 template rendering with `contract.yaml` variables
- CSL citation formatting (Citation Style Language)
- Page layout, font, spacing rules applied

### 8. Export
- DOCX generation (primary, via `python-docx`)
- PDF generation

### 9. Deliver
- Upload to Supabase Storage
- SSE event to frontend with download URL
- Cleanup temporary files (configurable: `ENABLE_FILE_CLEANUP=true`)

## Design Principles

### Async-First
All stages are async. Heavy stages (parsing, LLM calls) are offloaded to Celery workers. The HTTP request thread never blocks for >400ms.

### Graceful Degradation
Each stage has a fallback. If LLMClassifier is unavailable, rule-based classification runs. If GROBID is down, Docling takes over. If no LLM is reachable, NLP enhancement is skipped.

### Observable
Every stage emits structured logs with `request_id`, `stage`, `duration_ms`, and `status`. Prometheus metrics track stage-level latency and error rates.

### Configurable
- `LOW_MEMORY_MODE=true` disables memory-heavy stages (GROBID, LLMClassifier)
- `DEFAULT_FAST_MODE=true` skips optional enhancement stages
- Individual stage flags control behavior without code changes

## See Also

- [Architecture Overview](../architecture.md) — system layers and request flows
- [User Guide](../user_guide.md) — end-to-end formatting workflow
- [LLM Fallback Strategy](llm-fallback-strategy.md) — how LLM failures are handled
