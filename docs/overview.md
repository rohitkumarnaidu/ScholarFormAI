<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Project Overview
description: High-level overview of ScholarForm AI for new readers
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: July 2026
---

# Project Overview

ScholarForm AI is an open-source platform that automates academic manuscript formatting. It transforms unstructured DOCX/PDF manuscripts into journal-submission-ready documents — consistent formatting, proper citations, correct section layout — with a single click.

## What It Solves

Every academic journal has different formatting requirements. Researchers waste hours adjusting margins, fonts, heading styles, citation formats, and reference lists for each submission. ScholarForm AI eliminates this friction.

## Core Capabilities

| Feature | Description |
|---------|-------------|
| **Document Formatting** | Format any DOCX/PDF against 17+ journal templates via 12-stage pipeline |
| **AI Agent Generation** | Generate complete manuscripts from a prompt (11-step pipeline) |
| **Multi-Doc Synthesis** | Combine 2-6 source PDFs into a single coherent manuscript |
| **Live Preview** | WYSIWYG editor with real-time WebSocket rendering |
| **Template System** | Create custom journal templates with Jinja2 + `contract.yaml` validation |

## Architecture in Brief

- **Frontend:** Next.js 16 (App Router) + React 19 + Tailwind CSS
- **Backend:** FastAPI on Uvicorn (34 API routes under `/api/v1/`)
- **Database:** PostgreSQL via Supabase (auth, storage, RLS)
- **Cache/Queue:** Redis (Celery broker + SSE pub/sub)
- **Vector Store:** ChromaDB (RAG for multi-doc synthesis)
- **LLM:** NVIDIA NIM → Groq → Ollama (3-tier fallback via LiteLLM)
- **PDF Parsing:** GROBID → Docling → PyMuPDF (3-tier fallback)
- **Deployment:** Render (backend) + Vercel (frontend)

## Who It's For

- **Researchers** — format manuscripts for journal submission
- **Academics** — generate and synthesize academic papers
- **Publishers** — create journal-specific templates
- **Developers** — integrate manuscript formatting into workflows via API

## Quick Start

```bash
cd backend
python -m venv .venv && .\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI.

See the [Quickstart Guide](quickstart.md) for a full 5-minute setup.

## License

MIT License — free to use, modify, and distribute. See [LICENSE](../LICENSE).

## Next Steps

| Topic | Resource |
|-------|----------|
| 5-minute quickstart | [Quickstart](quickstart.md) |
| Full user workflow | [User Guide](user_guide.md) |
| Architecture deep-dive | [Architecture](architecture.md) |
| API documentation | [API Reference](API.md) |
| Custom templates | [Template Creation](template_creation.md) |
| AI Agent | [Agent Documentation](Agent.md) |
| Deployment | [Deployment Guide](Deployment.md) |
| Contributing | [CONTRIBUTING.md](../CONTRIBUTING.md) |
