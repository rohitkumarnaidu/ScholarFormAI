# ScholarForm AI — System Architecture

## Overview

ScholarForm AI is a distributed document formatting platform with four major subsystems:

| Subsystem | Role | Hosting |
|-----------|------|---------|
| **Frontend** | Next.js 16 (App Router) — 38 pages, 28+ components | Vercel |
| **Backend API** | FastAPI gateway + 93+ REST endpoints + Celery workers | Render |
| **Database** | Supabase (PostgreSQL + Auth + Storage) | Supabase Cloud |
| **AI Microservices** | GROBID (Docker), DOCX Converter (Docker) | Local Docker |

---

## Directory Structure

```
ScholarFormAI/
├── backend/                    # FastAPI + Celery
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── config/            # Pydantic settings, logging
│   │   ├── db/                # SQLAlchemy + Supabase client
│   │   ├── middleware/        # 11 middleware modules
│   │   ├── models/            # 17+ data models
│   │   ├── pipeline/          # 23 pipeline packages
│   │   ├── routers/           # 19 route modules
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── security/          # JWKS JWT verifier
│   │   ├── services/          # 39+ business logic services
│   │   ├── tasks/             # Celery task definitions
│   │   └── utils/             # Shared utilities
│   ├── tests/                 # 500+ test files
│   └── requirements.txt       # 414+ packages
│
├── frontend/                  # Next.js 16 App Router
│   ├── app/
│   │   ├── (formatter)/       # Formatter route group
│   │   ├── (generator)/       # Generator route group
│   │   └── (shared)/          # Landing, auth, settings
│   ├── src/
│   │   ├── components/        # 28+ React components
│   │   ├── context/           # 5 providers (Auth, Theme, Toast)
│   │   ├── hooks/             # 14 custom hooks
│   │   ├── lib/               # Supabase client, analytics
│   │   └── services/          # 13 API service modules
│   └── e2e/                   # Playwright E2E tests
│
├── deploy/                    # Prometheus, Grafana, Docker configs
│   └── services/              # GROBID and DOCX Converter Docker services
│       ├── grobid-service/    # GROBID metadata extraction (Docker)
│       └── docx-converter-service/
├── docs/                      # 80+ documentation files
└── .github/workflows/         # 25 CI/CD workflows
```

---

## Data Flow

### Upload & Format Pipeline

```
User ──→ Frontend Upload
            │
            ▼
    POST /api/v1/documents/upload
            │
            ▼
    [ClamAV Virus Scan]
    [MIME + Magic Byte + Extension Validation]
            │
            ▼
    Returns { job_id }  (< 400ms)
            │
            ▼
    ┌─── Celery Background Task ──────────────────────────┐
    │                                                     │
    │  1. PDF Parsing (Vision API → PyMuPDF+LLM → Raw)   │
    │  2. Structure Detection                             │
    │  3. Block Classification (LLMClassifier - optional) │
    │  4. NLP Enhancement (YAKE + spaCy)                  │
    │  5. Caption Matching (Tables + Figures)             │
    │  6. Figure Quality Analysis (optional)              │
    │  7. Numbering & Validation                          │
    │  8. Template Formatting (python-docx)               │
    │  9. DOCX/PDF Export                                 │
    │ 10. Upload to Supabase Storage                      │
    │                                                     │
    │  SSE events: { stage, progress } → Frontend         │
    └─────────────────────────────────────────────────────┘
```

### AI Agent Generation Pipeline

```
User Prompt ──→ POST /api/v1/generator/sessions
                    │
                    ▼
    Task Parser (LLM → structured JSON)
    Outline Generation (LLM)
    SS-→ User Approves Outline
    Section-by-Section Generation (LLM streaming)
    Citation Assembly (CrossRef API)
    Quality Scoring
    DOCX Render
```

### Multi-Doc Synthesis

```
Upload 2-6 PDFs ──→ POST /api/v1/synthesis/sessions
                       │
                       ▼
    Vector Embed (ChromaDB RAG)
    Dedup → Merge → Synthesize (LLM streaming via SSE)
    Output: coherent merged manuscript
```

---

## Auth Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client   │     │  FastAPI  │     │ Supabase │
│ (Next.js) │     │  Backend  │     │   Auth   │
└─────┬────┘     └─────┬────┘     └─────┬────┘
      │                │                │
      │ 1. Login       │                │
      │────────────────▶ Auth API        │
      │                │────────────────▶│
      │                │◀───────────────│
      │◀── JWT Token ──│                │
      │                │                │
      │ 2. API Request │                │
      │──── JWT ───────▶                │
      │                │ 3. JWKS Verify │
      │                │──── JWKS ──────▶
      │                │◀── Public Key ─│
      │                │                │
      │                │ 4. RBAC Check  │
      │                │ (role: admin/  │
      │                │  pro/free/     │
      │                │  guest)        │
      │◀── Response ───│                │
```

1. **Login**: Frontend authenticates via Supabase Auth (email/OTP/OAuth)
2. **JWT Issued**: Supabase returns a JWT signed with its private key
3. **Request**: Frontend sends JWT in `Authorization: Bearer <token>` header
4. **Verify**: FastAPI middleware fetches JWKS from Supabase, verifies token signature and expiry
5. **RBAC**: Middleware extracts `role` from JWT claims, enforces route-level permissions
6. **API Keys**: Alternative auth for programmatic access — Fernet-encrypted at rest

---

## Pipeline Architecture (5-Stage)

```
┌─────────────────────────────────────────────────────────┐
│              1. PARSING LAYER                           │
│  GROBID (Docker) ──▶ Vision API ──▶ PyMuPDF+LLM ──▶ Raw│
│  (metadata/struct)    (primary)      (enrichment) (fallback)|
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              2. STRUCTURE & CLASSIFICATION               │
│  Structure Detector → Block Classifier (LLMClassifier)  │
│  Caption Matcher → Numbering Engine                     │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              3. REASONING & ENHANCEMENT                  │
│  NLP (YAKE/spaCy) → OCR (LocalOCRService/RapidOCR)      │
│  → Quality Analysis → Semantic Classification           │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              4. FORMATTING                               │
│  Template Engine (python-docx + Jinja2) → CSL Citations  │
│  → Table Renderer → Figure Renderer → Validation         │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              5. EXPORT                                   │
│  DOCX (python-docx) → PDF (planned: LaTeX via Pandoc)   │
└─────────────────────────────────────────────────────────┘
```

---

## LLM Fallback Architecture (3-Tier)

| Tier | Provider | Model | When |
|------|----------|-------|------|
| 1 | NVIDIA NIM | Llama 3.3 70B Instruct | Primary (fastest) |
| 2 | Groq | llama-3.3-70b-versatile | Fallback if NVIDIA down |
| 3 | Ollama (local) | DeepSeek R1 | Offline/local mode |

All tiers abstracted behind **LiteLLM** — same client code for all providers.

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Vercel                                                      │
│  ┌─────────────────────────────────────────────┐            │
│  │  Next.js 16 (Static + SSR)                  │            │
│  │  Custom domain: scholarform.ai              │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Render                                                      │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │  FastAPI (Uvicorn)   │  │  Celery Worker               │ │
│  │  93+ API endpoints   │  │  Background tasks            │ │
│  │  N/A                 │  │  Redis broker  │ │
│  └──────────┬───────────┘  └──────────┬───────────────────┘ │
└─────────────┼─────────────────────────┼──────────────────────┘
              │                         │
              ▼                         ▼
┌────────────────────────┐  ┌──────────────────────────────┐
│  Supabase               │  │  Upstash Redis               │
│  ├── PostgreSQL (DB)    │  │  ├── Celery broker           │
│  ├── Auth (JWT)         │  │  ├── Cache                   │
│  ├── Storage (files)    │  │  └── Pub/Sub (realtime)      │
│  └── Row-Level Security │  │                              │
└────────────────────────┘  └──────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Local Docker Services (Optional)                           │
│  ┌────────────────────┐  ┌──────────────────────────────┐   │
│  │ GROBID (Docker)    │  │ DOCX Converter (Docker)      │   │
│  │ Metadata extraction│  │ Format conversion service    │   │
│  └────────────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

| Layer | Measures |
|-------|----------|
| **Transport** | TLS 1.3 (HTTPS), HSTS (max-age=31536000), CSP headers |
| **Auth** | Supabase JWT (JWKS-verified), API keys (Fernet-encrypted) |
| **API** | Rate limiting (base + tier-aware), CSRF, CORS strict-origin |
| **Upload** | ClamAV antivirus, MIME + magic byte + extension tri-validation |
| **Storage** | AES-256 at rest (Supabase), Row-Level Security |
| **CI/CD** | CodeQL, Trivy container scan, dependency audit, SLSA L3 |
| **Monitoring** | Prometheus metrics, audit logging |

---

## Tech Stack with Versions

| Category | Technology | Version |
|----------|-----------|---------|
| **Frontend** | Next.js | 16 |
| | React | 19 |
| | Tailwind CSS | 3 |
| | TanStack Query | 5 |
| | TypeScript | 5.x (strict) |
| | TipTap (editor) | 2.x |
| **Backend** | Python | 3.12.x |
| | FastAPI | 0.127.1 |
| | Uvicorn | latest |
| | Celery | latest |
| | SQLAlchemy | 2.x |
| | Alembic | latest |
| **Database** | Supabase (PostgreSQL) | 15+ |
| | Redis | 7.x |
| | ChromaDB | latest |
| **AI/ML** | LiteLLM | latest |
| | LLMClassifier (prompt-based) | user's LLM provider |
| | spaCy | 3.x |
| **PDF** | GROBID | 0.8 (optional, Docker) |
| | PyMuPDF | latest |
| | PIL/iMagick | — |
| **Deploy** | Vercel | — |
| | Render | — |
| | Docker | 24+ |
| **Monitoring** | Prometheus | latest |
| | Grafana | latest |


---

## Related Documents

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | Detailed architecture with request flows |
| [docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) | Frontend component architecture |
| [docs/DATABASE_ARCHITECTURE.md](docs/DATABASE_ARCHITECTURE.md) | Database schema and migrations |
| [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) | Security deep-dive |
| [docs/SECURITY.md](docs/SECURITY.md) | Security policy |
| [docs/Deployment.md](docs/Deployment.md) | Deployment guide |
| [docs/adr/](docs/adr/) | Architecture Decision Records (15 ADRs) |

---

*Last updated: July 2026*
