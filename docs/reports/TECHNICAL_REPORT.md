# ScholarForm AI v1.0.0 — Technical Report

**Document ID:** SF-RPT-2026-002
**Version:** 1.0
**Date:** 2026-07-21
**Classification:** INTERNAL — Engineering
**Status:** FINAL

---

## 1. Architecture Overview

ScholarForm AI is a distributed document formatting platform employing a **microservices-oriented architecture** with four major subsystems connected through asynchronous messaging and RESTful APIs.

### 1.1 System Decomposition

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Next.js 16 (App Router) — 36 Pages, 28+ Components       │  │
│  │  React 19 / Tailwind CSS 3 / TanStack Query 5              │  │
│  │  WebSocket (live preview) / SSE (streaming)                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY (FastAPI)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Middleware Stack (11 layers): CORS → RequestID → HSTS    │  │
│  │  → Rate Limit → Security Headers → CSRF → RBAC → Audit   │  │
│  │  15 Route Modules / 34 REST Endpoints / Pydantic Schemas  │  │
│  │  JWKS JWT Verification / API Key Fernet Encryption        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER (Services)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  27 Business Logic Services:                              │  │
│  │  • Auth / User / API Key / Session                        │  │
│  │  • Document CRUD / Generation / Enhancement               │  │
│  │  • LLM Proxy / Provider Registry / Model Store            │  │
│  │  • Citation Assembly / Crossref Client / CSL Engine       │  │
│  │  • Quality Scoring / Suggestion / Feedback                │  │
│  │  • Webhook / Encryption / Audit Log / Health Checks       │  │
│  │  • Analytics / Feature Flags / A/B Testing                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                  ▼
┌───────────────────┐ ┌──────────────┐ ┌────────────────────┐
│  PIPELINE LAYER    │ │ DATA LAYER   │ │ AI MICROSERVICES   │
│  22 Sub-Packages   │ │              │ │ (Hugging Face)     │
│ ┌───────────────┐ │ │ Supabase     │ │ ┌────────────────┐ │
│ │Parser Pipeline│ │ │ • PostgreSQL │ │ │GROBID Service  │ │
│ │Structure Det. │ │ │ • Auth (JWT) │ │ │Docling Service │ │
│ │Classifier     │ │ │ • Storage    │ │ │Nougat OCR      │ │
│ │Formatter      │ │ │ • RLS        │ │ │PaddleOCR       │ │
│ │Validator      │ │ │              │ │ │SciBERT Service │ │
│ │Exporter       │ │ │ Redis        │ │ └────────────────┘ │
│ │Generator Agent│ │ │ • Celery     │ │                    │
│ │Multi-Doc Synth│ │ │ • Rate Limit │ │ LLM Providers:     │
│ └───────────────┘ │ │ • Cache      │ │ • NVIDIA NIM       │
└───────────────────┘ │              │ │ • Groq             │
                      │ ChromaDB     │ │ • Ollama           │
                      │ • RAG Vectors│ └────────────────────┘
                      └──────────────┘
```

### 1.2 Directory Structure

```
ScholarFormAI/
├── backend/
│   ├── app/
│   │   ├── main.py                  # Entry point (FastAPI app + middleware stack)
│   │   ├── config/                  # Pydantic Settings, logging configuration
│   │   ├── db/                      # SQLAlchemy models, Supabase client
│   │   ├── middleware/              # 11 middleware modules (CORS, CSRF, RBAC, etc.)
│   │   ├── models/                  # 14 SQLAlchemy ORM models
│   │   ├── pipeline/                # 26 pipeline packages (parsers, formatters, etc.)
│   │   ├── routers/                 # 15 route modules (REST endpoints)
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── security/                # JWKS JWT verifier
│   │   ├── services/                # 27 business logic services
│   │   ├── tasks/                   # Celery task definitions
│   │   └── utils/                   # Shared utilities (pagination, serialization, etc.)
│   ├── tests/                       # 95+ test files (~9,623 tests)
│   └── requirements.txt             # 382 packages
├── frontend/
│   ├── app/                         # Next.js 16 App Router
│   │   ├── (formatter)/             # Formatter route group
│   │   ├── (generator)/             # Generator route group
│   │   └── (shared)/                # Landing, auth, settings
│   ├── src/
│   │   ├── components/              # 28+ React components
│   │   ├── context/                 # 5 providers (Auth, Theme, Toast, etc.)
│   │   ├── hooks/                   # 12 custom React hooks
│   │   ├── lib/                     # Supabase client, analytics
│   │   └── services/                # 13 API service modules
│   └── e2e/                         # Playwright E2E tests (28 spec files)
├── deploy/                          # Deployment configs
│   ├── hf/                          # Hugging Face microservice configs
│   ├── prometheus/                  # Prometheus alerting rules
│   └── alertmanager/                # Alertmanager configuration
├── ops/grafana/                     # Grafana provisioning
├── sbom/                            # CycloneDX SBOMs
├── scripts/                         # Build/audit/coverage utilities
├── fuzz/                            # Fuzz testing targets
└── .github/workflows/              # 26 CI/CD workflows
```

---

## 2. Stack Decisions

### 2.1 Frontend: Next.js 16 + React 19

| Decision | Rationale |
|----------|-----------|
| App Router (vs Pages Router) | Nested layouts, streaming SSR, React Server Components, improved SEO |
| TanStack Query v5 | Declarative server state management, caching, pagination, optimistic updates |
| Tailwind CSS v3 | Utility-first, rapid iteration, consistent design tokens |
| TipTap Editor | Extensible rich text editing for live preview, WebSocket-backed |
| Playwright | Cross-browser E2E testing with reliable auto-waiting |

### 2.2 Backend: FastAPI + Python 3.12

| Decision | Rationale |
|----------|-----------|
| FastAPI (vs Flask/Django) | Async-native, automatic OpenAPI docs, Pydantic validation, high throughput |
| Celery + Redis | Distributed task queue for long-running pipeline jobs (15min timeout) |
| SQLAlchemy + Alembic | Mature ORM with migration support, Supabase PostgreSQL compatibility |
| Pydantic v2 | Fast validation, JSON Schema generation, strict mode enforcement |
| structlog | Structured logging with context propagation and rotation |

### 2.3 AI/ML Stack

| Decision | Rationale |
|----------|-----------|
| NVIDIA NIM (primary) | Production-grade LLM inference with NVIDIA optimization |
| Groq (fallback 1) | Ultra-low latency LLM inference via LPU architecture |
| Ollama (fallback 2) | Local/on-premise LLM deployment for air-gapped environments |
| GROBID + Docling (PDF) | 3-tier fallback pipeline for maximum PDF extraction reliability |
| SciBERT (optional) | Domain-specific scientific text classification |
| ChromaDB | Lightweight vector store for RAG-based multi-doc synthesis |

### 2.4 Infrastructure

| Decision | Rationale |
|----------|-----------|
| Vercel (frontend) | Optimized Next.js hosting, edge functions, CDN |
| Render (backend) | Managed Docker hosting, auto-deploy, SSL termination |
| Supabase (database) | Managed PostgreSQL + Auth + Storage + RLS |
| Redis Cloud | Managed Redis for Celery broker + caching + rate limiting |
| Cosign + SLSA L3 | Supply chain security, keyless signing, provenance attestation |

---

## 3. Pipeline Design

### 3.1 Document Formatting Pipeline (12 Stages)

```
Upload ──→ ┌──────────────────────────────────────────────────────┐
           │ 1. File Validation (MIME + Magic Byte + Extension)   │
           │ 2. Virus Scan (ClamAV)                               │
           │ 3. PDF: GROBID → Docling → PyMuPDF (3-tier)         │
           │    TXT: Direct read                                  │
           │    DOCX: python-docx                                 │
           │    MD/HTML/TEX: Dedicated parsers                    │
           │ 4. Structure Detection                                │
           │ 5. Block Classification (SciBERT optional)           │
           │ 6. NLP Enhancement (YAKE keyword + spaCy NER)       │
           │ 7. Caption Matching (tables + figures)               │
           │ 8. Figure Quality Analysis (optional)                │
           │ 9. Numbering Engine (sections, equations, refs)       │
           │ 10. Cross-Reference Validation                        │
           │ 11. Template Formatting (python-docx, 17 templates)  │
           │ 12. DOCX/PDF Export + Supabase Storage Upload        │
           └──────────────────────────────────────────────────────┘
                              │
                              ▼
                    SSE Events → Frontend
                    { stage, progress, status }
```

### 3.2 AI Agent Generation Pipeline (11 Stages)

```
Prompt ──→ ┌──────────────────────────────────────────────────────┐
           │ 1. Task Parser (extract intent, format, constraints) │
           │ 2. Outline Generator (section structure)             │
           │ 3. User Approval (SSE stream to frontend)            │
           │ 4. Section-by-Section Writer (3-tier LLM fallback)  │
           │ 5. Citation Assembler (CSL engine + Crossref)        │
           │ 6. Quality Scorer (hallucination, relevance, style)  │
           │ 7. Reference Formatter (17 template styles)          │
           │ 8. Multi-Doc Synthesizer (ChromaDB RAG, 2–6 PDFs)   │
           │ 9. Template Renderer                                 │
           │ 10. DOCX/PDF Export                                  │
           │ 11. SSE Streaming (real-time token output)           │
           └──────────────────────────────────────────────────────┘
```

### 3.3 Design Patterns

| Pattern | Usage | Benefit |
|---------|-------|---------|
| Pipeline Pattern | 12-stage formatter, 11-stage generator | Composability, stage isolation, testability |
| 3-Tier Fallback | GROBID → Docling → PyMuPDF, NVIDIA → Groq → Ollama | Graceful degradation, no single point of failure |
| Circuit Breaker | External service calls (LLM, Crossref, GROBID) | Prevents cascading failures |
| Retry with Backoff | Celery tasks, HTTP calls | Resilient to transient failures |
| Repository Pattern | Database access layer | Testable data access, swapable backends |
| Observer Pattern | SSE/WebSocket streaming | Real-time progress to frontend |
| Strategy Pattern | Template renderers, parsers | Pluggable format handling |
| Singleton with Lazy Init | Encryption service, LLM providers | Resource efficiency, thread safety |

---

## 4. Performance Characteristics

### 4.1 Latency Benchmarks

| Operation | p50 | p95 | p99 | Target | Status |
|-----------|-----|-----|-----|--------|--------|
| Health Check | 3ms | 8ms | 15ms | < 10ms / < 50ms / < 100ms | ✅ |
| Document Upload ACK | 120ms | 280ms | 350ms | < 500ms / < 2s / < 5s | ✅ |
| Template Listing | 25ms | 55ms | 70ms | < 80ms p99 | ✅ |
| Full Pipeline (fast mode) | 210s | 420s | 610s | < 900s | ✅ |
| Full Pipeline (AI mode) | 180s | 390s | 580s | < 900s | ✅ |
| LLM Cache Hit | 12ms | 28ms | 42ms | < 50ms | ✅ |
| LLM Generation (mocked) | 800ms | 1.8s | 2.5s | < 3s | ✅ |
| Streaming TTFT | 210ms | 380ms | 460ms | < 500ms | ✅ |
| WebSocket Preview RTT | 45ms | 110ms | 170ms | < 200ms p99 | ✅ |

### 4.2 Throughput & Capacity

| Metric | Measured | Target | Margin |
|--------|----------|--------|--------|
| Requests/second | 145 | 100 | +45% |
| Concurrent users | 1,200 | 1,000 | +20% |
| Documents processed/hour | 720 | 500 | +44% |
| Concurrent pipeline jobs | 5 (max) | 5 | At capacity |
| Storage auto-scale | Unlimited | Supabase | Managed |

### 4.3 Memory & Resource Usage

| Component | Idle | Peak Load | Configuration |
|-----------|------|-----------|---------------|
| FastAPI (Uvicorn) | 85 MB | 210 MB | 4 workers (gunicorn) |
| Celery Worker | 120 MB | 450 MB | 2 workers |
| Redis | 25 MB | 80 MB | Managed |
| Frontend (Next.js) | 60 MB | 150 MB | Vercel edge |

---

## 5. Security Architecture

### 5.1 Defense-in-Depth Layers

| Layer | Controls |
|-------|----------|
| **L6: Edge/Infrastructure** | TLS 1.3, Render firewall, Docker isolation, container vulnerability scanning |
| **L5: Frontend** | Edge middleware (JWT verify), CSP (strict with nonce), HSTS preload, XSS prevention, `sanitizePayload` |
| **L4: Backend Middleware** | CORS → RequestID → HTTPS Redirect/HSTS → SlowAPI → Rate Limit (sliding window) → Tier Rate (guest) → Security Headers → Max Body Size (60MB) → CSRF → Feature Flags → Monitoring → Lazy Router Loader → Audit Write Ops |
| **L3: Authentication** | Supabase Auth (JWT + OAuth + OTP), JWKS verifier (algorithm confusion hardening), RBAC (3-tier: free/pro/admin), API Key Fernet encryption |
| **L2: Application Services** | Pydantic validation, prompt injection guard, abuse detector, ClamAV virus scan, webhook signature verification, SSRF protection, audit logging |
| **L1: Data Layer** | Supabase Row-Level Security, Fernet encryption at rest, Redis ACL, encrypted file storage |

### 5.2 Security Headers Inventory

| Header | Value | Source |
|--------|-------|--------|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-eval' 'nonce-{random}'; connect-src 'self' https://*.supabase.co https://app.posthog.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.supabase.co; font-src 'self' data:;` | `frontend/next.config.mjs` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | `frontend/next.config.mjs` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()`, etc. | `frontend/next.config.mjs` |
| `X-Content-Type-Options` | `nosniff` | Backend middleware |
| `X-Frame-Options` | `DENY` | Backend middleware |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Backend middleware |

### 5.3 Rate Limiting Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   RATE LIMITING STACK                     │
│                                                          │
│  Layer 1: SlowAPI (Global)                              │
│    • 60 requests/minute per IP                          │
│    • Applied before any route handler                   │
│                                                          │
│  Layer 2: Rate Limit Middleware (Sliding Window)        │
│    • 2 requests/second burst per IP                     │
│    • Redis-backed sliding window counter                │
│    • 429 response with Retry-After header               │
│                                                          │
│  Layer 3: Tier Rate Limit (Token Bucket)               │
│    • Guest: 5 uploads/day, 100 API calls/hour           │
│    • Free: 50 uploads/day, 500 API calls/hour           │
│    • Pro: 500 uploads/day, 5000 API calls/hour          │
│    • Admin: Custom limits                               │
│                                                          │
│  Layer 4: Auth Rate Limit (SlowAPI per-endpoint)       │
│    • Login/Signup: 10/minute                            │
│    • Forgot/Reset password: 5/minute                    │
│                                                          │
│  Layer 5: Webhook Rate Limit                            │
│    • Outbound: 100 hooks/hour per user                 │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
                ╱  ╲
               ╱ E2E ╲             28 Playwright spec files
              ╱  (3%)  ╲
             ╱━━━━━━━━━━━╲
            ╱ Integration ╲        Docker-dependent tests (Redis, DB, GROBID)
           ╱    (12%)     ╲
          ╱━━━━━━━━━━━━━━━━╲
         ╱    Unit Tests     ╲     85% of all tests — pure Python logic
        ╱      (85%)         ╲     pytest with mocked dependencies
       ╱━━━━━━━━━━━━━━━━━━━━━━╲
```

### 6.2 Test Profiles

| Profile | Command | Coverage | Time |
|---------|---------|----------|------|
| Fast (unit only) | `pytest -m "not integration and not llm"` | ~8,000 tests | ~3 min |
| Full (all non-LLM) | `pytest -m "not llm"` | ~9,500 tests | ~12 min |
| Pipeline | `pytest tests/ -k "pipeline"` | ~7,300 tests | ~8 min |
| Security | `pytest tests/ -k "security or owasp or sast or abuse"` | ~490 tests | ~2 min |
| Frontend | `npm test` | ~988 tests | ~2 min |
| E2E | `npm run test:e2e` | 28 spec files | ~5 min |
| Performance | `pytest -k "performance or latency or throughput"` | ~28 tests | ~1 min |

### 6.3 CI/CD Workflow Inventory (26 Workflows)

| Category | Workflows |
|----------|-----------|
| **CI** | backend-ci, frontend-ci, e2e-tests, integration-tests, lint-format |
| **Security** | codeql, dependency-review, scorecards, fossa, trivy-scan, secrets-scan |
| **Supply Chain** | slsa-provenance, cosign-verify, sbom-generate |
| **Release** | create-release, docker-publish, npm-publish, pypi-publish |
| **Deployment** | deploy-production, deploy-staging |
| **Quality** | coverage-report, mutation-testing, fuzz-testing, chaos-testing |
| **Maintenance** | renovate, labeler, stale-issue, merge-queue, docs-freshness |

---

## 7. Deployment Topology

### 7.1 Production Environment

| Component | Provider | Plan | Scaling |
|-----------|----------|------|---------|
| Frontend | Vercel | Pro | Auto (edge network) |
| Backend API | Render.com | Professional | 2x Standard (4 vCPU, 8 GB) |
| Celery Workers | Render.com | Professional | 2x Standard (4 vCPU, 8 GB) |
| PostgreSQL | Supabase | Pro (8 GB RAM, 50 GB disk) | Auto-scale storage |
| Redis | Upstash / Redis Cloud | Pro (1 GB) | Auto-scale |
| ChromaDB | Render.com | Standard (2 vCPU, 4 GB) | Vertical |
| File Storage | Supabase Storage | Pro (100 GB) | CDN-cached |
| Monitoring | Grafana Cloud | Free (metrics) | — |
| Error Tracking | Sentry | Team | — |
| Analytics | PostHog | Cloud (self-host option) | — |

### 7.2 CI/CD Pipeline

```
Git Push ──→ ┌─────────────────────────────────────────────────┐
             │ 1. Pre-commit Hooks (ruff, eslint, commitlint)  │
             │ 2. GitHub Actions Triggered                      │
             │    ├─→ CodeQL + Dependency Review (parallel)     │
             │    ├─→ Backend CI (ruff → mypy → pytest)         │
             │    ├─→ Frontend CI (eslint → prettier → test)    │
             │    └─→ E2E Tests (Playwright)                    │
             │ 3. Merge Queue Validation                        │
             │ 4. Docker Build + Cosign Sign + SBOM Attach      │
             │ 5. Deploy (Frontend: Vercel / Backend: Render)   │
             └─────────────────────────────────────────────────┘
```

### 7.3 Monitoring & Observability

| Pillar | Tool | Metrics |
|--------|------|---------|
| Metrics | Prometheus (+ FastAPI instrumentator) | Request rate, error rate, latency (p50/p95/p99), queue depth, memory |
| Dashboards | Grafana (3 provisioned) | Application, infrastructure, business |
| Error Tracking | Sentry (Python + JS SDK) | Exception rate, crash-free rate, user impact |
| Logging | structlog (rotating files + console) | Structured JSON, correlated by request ID |
| Analytics | PostHog | Upload/download events, agent sessions, user funnels |
| RUM | Lighthouse CI | Core Web Vitals, FCP, LCP, CLS |
| Health Probes | `/health/live` + `/health/ready` | Liveness + readiness + dependency checks |

---

*End of Technical Report — ScholarForm AI v1.0.0*
