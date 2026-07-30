<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# 📄 ScholarForm AI v1.0 — Automated Academic Manuscript Formatting, Powered by AI

**The first open-source, AI-powered platform that formats academic manuscripts to any journal style in seconds.**

---

## The Problem

Academics waste hours — sometimes days — formatting manuscripts for journal submission. Every journal has its own style guide: IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, and a dozen more. Researchers juggle citation managers, template files, and manual tweaks, burning time that should go into the science itself. A 2023 survey estimated that formatting consumes **15–25% of the total writing time** for a typical conference or journal paper.

## The Solution

ScholarForm AI is the first open-source, end-to-end platform purpose-built to solve this. Upload a manuscript in any format (DOCX, PDF, LaTeX, Markdown, HTML, or plain text) and get a publisher-ready document in any of **17 journal templates** — in seconds. Or use the AI Agent Generator to produce a complete research document from a simple prompt, with outline approval and section-by-section streaming.

It's not just formatting. ScholarForm AI understands document structure, validates citations, scores quality, and can even synthesize multiple source documents into a single coherent manuscript.

## Key Features

- **12-Stage Formatter Pipeline** — Virus scan → MIME validation → parsing → structure detection → classification → formatting → equation handling → reference assembly → quality scoring → preview → export → audit. Every stage is modular and swappable.
- **AI Agent Generator** — Generate a complete research document from a topic prompt. The agent proposes an outline, you approve, then it streams each section with citations, figures, and references.
- **Multi-Doc RAG Synthesis** — Upload 2–6 source documents. ChromaDB-powered semantic retrieval merges them into one unified manuscript with coherent flow and deduplicated content.
- **Real-Time Live Preview** — Split-pane editor with before/after diff via WebSocket/SSE. Edit formatted output inline and re-download.
- **17 Journal Templates** — IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, Harvard, Vancouver, Numeric, plus custom and blank.
- **Enterprise-Grade Security** — JWKS JWT authentication, CSRF protection, rate limiting, ClamAV virus scanning, dependency SBOMs, SLSA L3 provenance, Cosign-signed containers, OpenSSF Scorecard 10/10.
- **Batch Processing** — Upload and format multiple manuscripts in parallel with background Celery workers.

## Architecture

```
Frontend          Backend            Infrastructure        Data Layer
─────────         ───────            ──────────────        ──────────
Next.js 16    →   FastAPI         →  Celery Workers     →  Supabase (PostgreSQL)
React 19         26 Pipeline         Redis Pub/Sub         Supabase Storage
Tailwind CSS     34 REST Routes      ChromaDB (RAG)        Redis Cache
TanStack Query   15 Route Modules    Prometheus/Grafana
                 25 Services
```

**LLM Tiering:** NVIDIA NIM (Llama 3.3 70B, primary) → Groq (fallback) → DeepSeek R1 via Ollama (local/offline)

**PDF Extraction:** GROBID → Docling → PyMuPDF → PyPDF2 (4-tier fallback)

## Open Source

ScholarForm AI is released under the **MIT license** — free to use, modify, and distribute. We're building this in the open, with a community-first governance model.

| Metric | Status |
| -------- | -------- |
| License | MIT |
| CI/CD | 25 workflows, green |
| Coverage | 61% backend, growing |
| Containers | Multi-arch (amd64 + arm64), Cosign-signed |
| SBOM | CycloneDX for backend + frontend |
| Supply Chain | OpenSSF Scorecard, SLSA L3, Renovate |

## Getting Started

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` and upload your first manuscript.

**Docker:**

```bash
cd backend/docker
docker-compose up -d
```

## Call to Action

- **Star on GitHub** → [github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI)
- **Try the Demo** → [scholarform.ai](https://scholarform.ai)
- **Read the Docs** → See the `docs/` directory for 80+ documentation files
- **Contribute** → We welcome PRs. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the [`ROADMAP.md`](docs/Roadmap.md).
- **Report Issues** → [GitHub Issues](https://github.com/rohitkumarnaidu/ScholarFormAI/issues)

---

*ScholarForm AI v1.0 — Because your time is better spent on research than on margins and font sizes.*
