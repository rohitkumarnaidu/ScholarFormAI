<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


<div align="center">
  <br/>
  <h1>📄 ScholarForm AI</h1>
  <h3>Automated Academic Manuscript Formatting — Powered by AI</h3>
  <p>Upload a manuscript → get a publisher-ready DOCX/PDF. Or generate a full research document from scratch.</p>
  <br/>

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![CI — Backend](https://github.com/rohitkumarnaidu/ScholarFormAI/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/rohitkumarnaidu/ScholarFormAI/actions/workflows/backend-ci.yml)
[![CI — Frontend](https://github.com/rohitkumarnaidu/ScholarFormAI/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/rohitkumarnaidu/ScholarFormAI/actions/workflows/frontend-ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-61%25-yellow)](backend/.coverage)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![GitHub stars](https://img.shields.io/github/stars/rohitkumarnaidu/ScholarFormAI?style=social)](https://github.com/rohitkumarnaidu/ScholarFormAI/stargazers)
[![Last commit](https://img.shields.io/github/last-commit/rohitkumarnaidu/ScholarFormAI/main)](https://github.com/rohitkumarnaidu/ScholarFormAI/commits/main)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)
[![SBOM](https://img.shields.io/badge/SBOM-CycloneDX-8A2BE2)](sbom/backend-sbom.json)
[![Dependency Review](https://img.shields.io/badge/dependency%20review-passing-brightgreen)](.github/workflows/dependency-review.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/rohitkumarnaidu/ScholarFormAI/badge)](https://api.scorecard.dev/projects/github.com/rohitkumarnaidu/ScholarFormAI)
[![Renovate](https://img.shields.io/badge/renovate-enabled-1A1F6E)](renovate.json)
[![FOSSA](https://img.shields.io/badge/license%20scan-FOSSA-289E6D)](.fossa.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/rohitkumarnaidu/ScholarFormAI/badge)](https://securityscorecards.dev/viewer/?uri=github.com/rohitkumarnaidu/ScholarFormAI)
[![CodeQL](https://github.com/rohitkumarnaidu/ScholarFormAI/actions/workflows/codeql.yml/badge.svg)](.github/workflows/codeql.yml)
[![SLSA](https://img.shields.io/badge/SLSA-3-brightgreen)](.github/workflows/slsa-provenance.yml)
[![ghcr.io](https://img.shields.io/badge/ghcr.io-packages-2496ED?logo=docker)](https://github.com/rohitkumarnaidu/ScholarFormAI/pkgs/container/scholarform)
[![GitHub Release](https://img.shields.io/github/v/release/rohitkumarnaidu/ScholarFormAI?logo=github)](https://github.com/rohitkumarnaidu/ScholarFormAI/releases)
[![Conventional Commits](https://img.shields.io/badge/conventional%20commits-1.0.0-FE5196)](commitlint.config.js)
[![Signed commits](https://img.shields.io/badge/signed%20commits-required-red)](docs/BRANCH_PROTECTION.md)

</div>

---

## Table of Contents

- [Features](#features)
- [Built With](#built-with)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Docker](#docker)
- [Configuration](#configuration)
- [API Overview](#api-overview)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Quickstart](docs/quickstart.md)
- [Examples](#examples)
- [Building](BUILDING.md)
- [Contributing](CONTRIBUTING.md)
- [Governance](#governance)
- [Roadmap](docs/Roadmap.md)
- [Support](SUPPORT.md)
- [Security](SECURITY.md)
- [FAQ](FAQ.md)
- [License](#license)

---

## Features

- **Formatter Mode** — Upload DOCX, PDF, LaTeX, Markdown, HTML, or plain text; get a publisher-ready manuscript in IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, Harvard, Vancouver, Numeric, and more (17 templates)
- **Generator Mode** — AI Agent generates a complete research document from a prompt, with outline approval and section-by-section streaming
- **Multi-Doc Synthesis** — Merge and synthesize content from multiple source documents into one coherent manuscript
- **Real-Time Preview** — Live editor with split-pane before/after diff via WebSocket/SSE
- **AI-Powered Analysis** — Quality scoring, citation validation, reference assembly, and semantic classification (SciBERT — optional)
- **3-Tier PDF Fallback** — GROBID → Docling → PyMuPDF → PyPDF2 chain for maximum extraction reliability
- **Batch Processing** — Upload and process multiple manuscripts in parallel
- **17 Templates** — IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, Harvard, Vancouver, Numeric, plus custom/blank
- **Export** — Download formatted manuscripts as DOCX or PDF

---

## Built With

| Layer | Technology |
|-------|-----------|
| **Frontend** | [![Next.js 16](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/) [![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev/) [![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss)](https://tailwindcss.com/) [![TanStack Query](https://img.shields.io/badge/TanStack_Query-5-FF4154?logo=reactquery)](https://tanstack.com/query) |
| **Backend** | [![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/) [![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org/) [![Celery](https://img.shields.io/badge/Celery-37814A?logo=celery)](https://docs.celeryq.dev/) [![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis)](https://redis.io/) |
| **Database** | [![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?logo=supabase)](https://supabase.io/) [![ChromaDB](https://img.shields.io/badge/ChromaDB-FC6D26?logo=chromadb)](https://www.trychroma.com/) |
| **AI/ML** | [![NVIDIA NIM](https://img.shields.io/badge/NVIDIA_NIM-76B900?logo=nvidia)](https://build.nvidia.com/) [![Groq](https://img.shields.io/badge/Groq-f55036?logo=groq)](https://groq.com/) [![Ollama](https://img.shields.io/badge/Ollama-000?logo=ollama)](https://ollama.ai/) |
| **PDF** | [![GROBID](https://img.shields.io/badge/GROBID-0.8-5277C3)](https://grobid.readthedocs.io/) [![Docling](https://img.shields.io/badge/Docling-IBM-052FAD)](https://ds4sd.github.io/docling/) |
| **Monitoring** | [![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus)](https://prometheus.io/) [![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana)](https://grafana.com/) [![Sentry](https://img.shields.io/badge/Sentry-362D59?logo=sentry)](https://sentry.io/) [![PostHog](https://img.shields.io/badge/PostHog-000?logo=posthog)](https://posthog.com/) |
| **Deploy** | [![Render](https://img.shields.io/badge/Render-46E3B7?logo=render)](https://render.com/) [![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker)](https://docker.com/) |

---

## Architecture

```mermaid
flowchart TB
    subgraph BROWSER["BROWSER (Next.js 16 + React 19)"]
        A1["Auth"]
        A2["Formatter UI"]
        A3["Generator UI"]
        A4["Live Editor"]
        A5["Admin"]
    end

    subgraph GATEWAY["API GATEWAY — FastAPI"]
        G1["JWKS JWT Verify"]
        G2["Rate Limit"]
        G3["CORS"]
        G4["Request ID"]
        G5["CSRF"]
    end

    subgraph BACKEND["BACKEND (FastAPI + Uvicorn)"]
        direction TB
        B1["25 Services"]
        B2["15 Route Modules"]
        B3["26 Pipeline Packages"]
        B4["Agents │ Classification<br/>Equations │ Export<br/>Formatting │ Figures<br/>Integrity │ NLP │ OCR<br/>Parsing │ References<br/>Safety │ Structure Detection<br/>Synthesis │ Tables │ Validation"]
    end

    subgraph INFRA["INFRASTRUCTURE"]
        I1["Celery Worker<br/>(background jobs)"]
        I2["Redis Pub/Sub<br/>(realtime events)"]
        I3["ChromaDB<br/>(RAG / style-rule store)"]
    end

    subgraph DATA["DATA LAYER"]
        D1["Supabase<br/>(PostgreSQL)"]
        D2["Supabase Storage"]
        D3["Redis Cache"]
    end

    BROWSER <--> GATEWAY
    GATEWAY <--> BACKEND
    BACKEND <--> I1
    BACKEND <--> I2
    BACKEND <--> I3
    I1 <--> D1
    I1 <--> D2
    I2 <--> D3
    I3 <--> D1
```

- **LLM Tier 1:** NVIDIA NIM — Llama 3.3 70B Instruct (primary)
- **LLM Tier 2:** Groq — llama-3.3-70b-versatile (fallback)
- **LLM Tier 3:** DeepSeek R1 via Ollama (local/offline)
- **PDF Parsing:** GROBID → Docling → PyMuPDF → PyPDF2 (4-tier fallback)
- **Realtime:** Redis pub/sub → WebSocket / SSE

---

## Quick Start

### Prerequisites

- Python **3.12.x** (3.11 causes pytest import collisions)
- Node.js **20+ (LTS)**
- Redis (for Celery + realtime features — optional for basic usage)

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and fill in your credentials, then:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs` (requires `DEBUG=true` in `.env`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

### 3. Environment Variables

**Backend** — `backend/.env`:
```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
NVIDIA_API_KEY=nvapi-...
GROQ_API_KEY=gsk_...
REDIS_URL=redis://localhost:6379
LOW_MEMORY_MODE=true
DEFAULT_FAST_MODE=true
```

**Frontend** — `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...
```

> All frontend env vars are prefixed `NEXT_PUBLIC_*`.

---

## Docker

A Docker Compose setup is available at `backend/docker/docker-compose.yml` for running GROBID and other service dependencies:

```bash
cd backend/docker
docker-compose up -d
```

This starts:
- **GROBID** (port 8070) — metadata extraction from PDFs
- Services defined in the Compose file

For full-stack deployment, see [`deploy/`](deploy/) for Prometheus, Grafana, and Hugging Face deployment configs.

---

## API Overview

| Method | Endpoint | Purpose |
|--------|---------|---------|
| `POST` | `/api/v1/documents/upload` | Upload & format document |
| `GET` | `/api/v1/documents/{job_id}/status` | Poll processing status |
| `GET` | `/api/v1/documents/{job_id}/preview` | Rendered HTML preview |
| `GET` | `/api/v1/documents/{job_id}/compare` | Before/after diff |
| `GET` | `/api/v1/documents/{job_id}/download` | Download DOCX/PDF |
| `POST` | `/api/v1/documents/{job_id}/edit` | Save edits |
| `GET` | `/api/v1/templates` | List all 17 templates |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

See [`docs/API.md`](docs/API.md) for the full reference (34 routes).

---

## Testing

**Backend** (fast, no external services):
```bash
cd backend
pytest tests -m "not integration and not llm and not contract" -x -q
```

**Frontend:**
```bash
cd frontend
npm test                    # Vitest unit tests
npm run test:e2e            # Playwright E2E (headless)
npm run test:e2e:headed     # Playwright E2E (headed)
```

See [`docs/Testing.md`](docs/Testing.md) for the full test strategy.

---

## Compliance & Dependency Management

ScholarForm AI maintains a comprehensive license compliance and dependency audit program.

| Capability | Tool/Framework | Frequency |
|-----------|---------------|-----------|
| License inventory | `THIRD_PARTY_NOTICES.md` (auto-generated) | Every commit |
| SBOM (CycloneDX) | `sbom/backend-sbom.json`, `sbom/frontend-sbom.json` | Weekly + on dep change |
| CVE scanning (Python) | pip-audit + safety | Every PR |
| CVE scanning (npm) | npm audit | Every PR |
| SAST (Python) | bandit | Every PR |
| Dependency PRs | Renovate | Weekly (Monday) |
| License compliance | FOSSA | Continuous |
| License policy enforcement | `dependency-review.yml` | Every PR |

See [`docs/compliance.md`](docs/compliance.md) for full documentation.

---

## Project Structure

<details>
<summary>Click to expand</summary>

```
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI application entry
│   │   ├── config/               # Pydantic settings, logging config
│   │   ├── db/                   # SQLAlchemy base, Supabase client
│   │   ├── middleware/           # 11 middleware modules (rate-limit, CSRF, RBAC, etc.)
│   │   ├── models/              # 14 SQLAlchemy models
│   │   ├── pipeline/            # 26 pipeline packages (agents, formatting, export, etc.)
│   │   ├── routers/             # 15 route modules under /api/v1/
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── security/            # JWKS JWT verifier
│   │   ├── services/            # 25 business logic services
│   │   ├── tasks/               # Celery background task definitions
│   │   └── utils/               # Shared utilities
│   ├── tests/                   # 95+ test files (unit, integration, contract)
│   ├── docker/                  # Docker Compose for GROBID + services
│   └── requirements.txt         # 382 Python packages
│
├── frontend/
│   ├── app/                     # Next.js App Router — 36 pages
│   │   ├── (formatter)/         # Formatter route group
│   │   ├── (generator)/         # Generator route group
│   │   └── (shared)/            # Landing, auth, settings, etc.
│   ├── src/
│   │   ├── components/          # 28+ React components
│   │   ├── context/             # 5 context providers (Auth, Theme, Toast, etc.)
│   │   ├── hooks/               # 12 custom hooks
│   │   ├── lib/                 # Supabase client, analytics, schemas
│   │   └── services/            # 13 API service modules
│   └── e2e/                     # Playwright E2E tests
│
├── deploy/                      # Prometheus, Grafana, HF deployment configs
├── docs/                        # Architecture, API, roadmap, audit reports
└── .github/workflows/           # CI/CD pipelines
```
</details>

---

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

- `ruff` + `ruff-format` on backend Python files
- `eslint` on frontend JS/JSX files
- `detect-secrets` with `.secrets.baseline`

```bash
pip install pre-commit
pre-commit install
```

Windows one-liner:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_precommit.ps1
```

Run manually:
```bash
pre-commit run --all-files
```

---

## Building

See [`BUILDING.md`](BUILDING.md) for build-from-source instructions.

## Examples

See the [`examples/`](examples/) directory for working code:

- **[quick-format](examples/quick-format/)** — Format a paper from the CLI
- **[custom-template](examples/custom-template/)** — Create and register a new template
- **[api-scripts](examples/api-scripts/)** — Python API client example

## Contributing

We welcome contributions! All contributors must agree to the [Developer Certificate of Origin](DEVELOPER_CERTIFICATE_OF_ORIGIN.md). Use `git commit -s` to sign off your commits.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines and use the [Pull Request Template](PULL_REQUEST_TEMPLATE.md).

**Quick workflow:**
1. Fork the repo and create a branch from `main`
2. See [`BUILDING.md`](BUILDING.md) to set up your environment
3. Make your changes (keep commits small and focused)
4. Run lint + tests locally (`ruff` → `pytest` → `npm test`)
5. Open a pull request using the [template](PULL_REQUEST_TEMPLATE.md)

All PRs must pass CI checks and include DCO sign-off before merging.

---

## Governance

ScholarForm AI uses a **BDFL + Core Team** governance model. See:
- [GOVERNANCE.md](GOVERNANCE.md) — decision-making, RFC process, roles
- [MAINTAINERS.md](MAINTAINERS.md) — core team and committer roster

---

## Roadmap

See [`docs/Roadmap.md`](docs/Roadmap.md) for the full implementation plan.

---

## Support

- **Community help:** [GitHub Discussions](https://github.com/rohitkumarnaidu/ScholarFormAI/discussions)
- **Bug reports:** [GitHub Issues](https://github.com/rohitkumarnaidu/ScholarFormAI/issues)
- **FAQ:** [FAQ.md](FAQ.md)
- **Security:** [SECURITY.md](SECURITY.md)
- **Commercial:** enterprise@scholarform.ai
- See [SUPPORT.md](SUPPORT.md) for full details.

---

## Security

Found a vulnerability? Please see [`SECURITY.md`](SECURITY.md) for our disclosure policy.

This project uses:
- CSRF protection on all state-changing requests
- Rate limiting (global + per-tier)
- Security headers (CSP, HSTS, X-Frame-Options)
- HTTPS enforcement in production
- Virus scanning (ClamAV) on uploaded files
- Abuse detection middleware

---

## FAQ

See the full [FAQ.md](FAQ.md) for 20+ questions. Quick highlights:

**Q: Does this require a GPU?**  
A: No. All AI inference uses cloud APIs (NVIDIA NIM, Groq) or runs CPU-friendly via Ollama for local fallback.

**Q: Can I run it fully locally?**  
A: Yes, but you'll need Redis for realtime features and Supabase credentials for persistence. The PDF parser works offline via PyMuPDF fallback.

**Q: What file formats are supported?**  
A: Input: DOCX, PDF, LaTeX, Markdown, HTML, TXT. Output: DOCX, PDF (LaTeX export in development).

**Q: How do I add a new template?**  
A: See the [Template Creation Guide](docs/template_creation.md) and [examples/custom-template](examples/custom-template/).

**Q: Does it work on Render free tier?**  
A: Yes — the app runs with `LOW_MEMORY_MODE=true` and `PRELOAD_AI_MODELS=false` on a 512MB RAM instance.

**Q: Where can I get help?**  
A: [SUPPORT.md](SUPPORT.md) — community channels, commercial support, and response SLAs.

---

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

This project includes third-party components under various licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details.

---

<div align="center">
  <sub>Built with ❤️ for researchers, academics, and open science.</sub>
</div>
