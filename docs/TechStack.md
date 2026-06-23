<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Technology Stack
description: All technologies, libraries, and services powering the platform
sidebar_position: 3
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Technology Stack

> **See also:** [Architecture](architecture.md), [Deployment](Deployment.md), [API Reference](API.md)

## Frontend

| Component | Stack |
|---|---|
| Framework | Next.js (App Router) |
| UI | React + Tailwind CSS |
| State/API usage | Fetch + React hooks |
| Testing | Vitest + Playwright |
| Hosting | Vercel |

## Backend

| Component | Stack |
|---|---|
| Runtime | Python 3.12 |
| API framework | FastAPI + Uvicorn |
| Background tasks | Celery (present, queue mode currently off) |
| Document generation | python-docx, docxtpl |
| Parsing/fallback | GROBID client + Docling + PyMuPDF/PyPDF2 |
| Caching and broker | Redis (Upstash in production) |
| Data/auth/storage | Supabase |

## Remote Heavy Services (Hugging Face Spaces)

| Service | Routing model | Health path |
|---|---|---|
| GROBID | Primary + Shadow via `GROBID_URLS` | `/api/isalive` |
| Docling | Primary + Shadow via `DOCLING_URLS` | `/` |
| OCR | Primary + Shadow via `OCR_URLS` | `/` |
| DOCX converter | Primary + Shadow via `DOCX_CONVERTER_URLS` | `/` |

All heavy processing is intended to be remote in production. URL-list variables take precedence over single-URL variables.

## Deployment Topology (Strict $0)

| Layer | Provider |
|---|---|
| Frontend | Vercel |
| Backend | Render free web service (512MB) |
| DB/Auth/Storage | Supabase free tier |
| Cache/Broker | Upstash Redis free tier |
| Heavy compute services | Hugging Face Spaces |

## Runtime Profile (Render 512MB)

| Variable | Value |
|---|---|
| `LOW_MEMORY_MODE` | `true` |
| `PRELOAD_AI_MODELS` | `false` |
| `RAG_USE_TRANSFORMERS` | `false` |
| `ENHANCEMENT_QUEUE_ENABLED` | `false` |
| `ENABLE_STRUCTURED_LOGGING` | `true` |
| `ENABLE_FILE_CLEANUP` | `true` |
| `ENABLE_NOUGAT_PARSER` | `false` |
| `USE_SCIBERT_CLASSIFICATION` | `false` |

## CI/CD and Operations

| Area | Current behavior |
|---|---|
| Production deploy | Manual (`workflow_dispatch`) |
| Backend health gate | `/api/v1/health/live` |
| Keepalive | Every 14 minutes for backend + HF primary/shadow pairs |
| Monitoring | Structured logs enabled; Prometheus/Grafana assets available in repo |

## Planned Next Phase (Not enabled yet)

- Queue mode activation after stability window.
- Nougat and SciBERT remote URL adapters with primary/shadow support.
