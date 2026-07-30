<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI — Enterprise Deployment Guide

> **Version:** 1.0 | **Status:** Production Ready | **Owner:** DevOps Team
>
> **See also:** [Architecture](architecture.md) | [Disaster Recovery](DISASTER_RECOVERY.md) | [Monitoring](MONITORING.md)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Render Deployment](#2-render-deployment)
3. [Hugging Face Spaces Deployment](#3-hugging-face-spaces-deployment)
4. [Frontend (Vercel) Deployment](#4-frontend-vercel-deployment)
5. [Monitoring Stack (Prometheus + Grafana)](#5-monitoring-stack-prometheus--grafana)
6. [Docker Builds & Container Registry](#6-docker-builds--container-registry)
7. [Environment Configuration](#7-environment-configuration)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Production Checklist](#9-production-checklist)
10. [Rollback Procedure](#10-rollback-procedure)
11. [Error Budget & SLOs](#11-error-budget--slos)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SCHOLARFORM AI — PRODUCTION                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐     ┌──────────────────────────────────┐     ┌──────────────┐  │
│  │  Vercel   │────▶│      Render (512MB Free)        │     │   Supabase   │  │
│  │ (Next.js) │     │  ┌────────────────────────────┐ │     │  ┌─────────┐ │  │
│  │           │     │  │  Web Service (Uvicorn)      │ │     │  │PostgreSQL│ │  │
│  │  Frontend │     │  │  uvicorn app.main:app       │ │─────│  │ Auth     │ │  │
│  │  Static   │     │  │  --workers WEB_CONCURRENCY  │ │     │  │ Storage  │ │  │
│  │  Assets   │     │  └────────────────────────────┘ │ │     │  └─────────┘ │  │
│  └──────────┘     │  ┌────────────────────────────┐ │ │     └──────────────┘  │
│                   │  │  Celery Worker              │ │ │                      │
│                   │  │  -Q interactive (-c 2)      │ │ │                      │
│                   │  │  -Q batch (-c 2)            │ │ │                      │
│                   │  └────────────────────────────┘ │ │                      │
│                   └──────────────────────────────────┘ │                      │
│                             │                          │                      │
│                             ▼                          │                      │
│                   ┌──────────────────┐                 │                      │
│                   │  Upstash Redis   │                 │                      │
│                   │  (Cache + Celery │                 │                      │
│                   │   Broker)        │                 │                      │
│                   └──────────────────┘                 │                      │
│                                                       │                      │
│                   ┌──────────────────────────────────────────────────┐       │
│                   │     Hugging Face Spaces (6 Service Pairs)       │       │
│                   │                                                  │       │
│                   │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │       │
│                   │  │ GROBID   │  │ Docling  │  │ OCR (Rapid)  │   │       │
│                   │  │ Primary  │  │ Primary  │  │ Primary      │   │       │
│                   │  │ Shadow   │  │ Shadow   │  │ Shadow       │   │       │
│                   │  └──────────┘  └──────────┘  └──────────────┘   │       │
│                   │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │       │
│                   │  │ DOCX     │  │ LLMPDFParser   │  │ LLMClassifier      │   │       │
│                   │  │ Converter│  │ Primary  │  │ Primary      │   │       │
│                   │  │ Primary  │  │ Shadow   │  │ Shadow       │   │       │
│                   │  │ Shadow   │  └──────────┘  └──────────────┘   │       │
│                   │  └──────────┘                                    │       │
│                   └──────────────────────────────────────────────────┘       │
│                                                                              │
│                   ┌──────────────────────────────────────┐                   │
│                   │  Monitoring Stack                    │                   │
│                   │  Prometheus ──▶ Grafana Dashboard    │                   │
│                   │  Alertmanager ──▶ PagerDuty/Slack    │                   │
│                   └──────────────────────────────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Service Responsibilities

| Component | Provider | Plan | Purpose |
|-----------|----------|------|---------|
| **Web Service** | Render | Free (512MB) | FastAPI + Uvicorn HTTP server |
| **Celery Worker** | Render | Free (512MB) | Background document processing |
| **Redis** | Upstash | Free (30MB) | Cache, Celery broker/backend |
| **Database** | Supabase | Free (500MB) | PostgreSQL + Auth + Storage |
| **Frontend** | Vercel | Hobby | Next.js 16 static/SSR |
| **GROBID (×2)** | HF Spaces | Free (2 vCPU) | XML metadata extraction |
| **Docling (×2)** | HF Spaces | Free (2 vCPU) | Layout-aware PDF analysis |
| **OCR (×2)** | HF Spaces | Free (2 vCPU) | RapidOCR text extraction |
| **DOCX Converter (×2)** | HF Spaces | Free (2 vCPU) | LibreOffice format conversion |
| **LLMPDFParser (×2)** | HF Spaces | Free (2 vCPU) | LaTeX/Markdown PDF parsing |
| **LLMClassifier (×2)** | HF Spaces | Free (2 vCPU) | Block-type classification |

### Communication Flow

1. **User** → **Vercel** (Next.js frontend, SSR/static)
2. **Vercel** → **Render Web Service** (REST API calls, `/api/v1/*`)
3. **Render Web Service** → **Supabase** (database queries via `supabase-py`)
4. **Render Web Service** → **Upstash Redis** (response caching)
5. **Render Web Service** → **HF Spaces** (inline document processing)
6. **Celery Worker** → **Upstash Redis** (broker for task queue)
7. **Celery Worker** → **HF Spaces** (heavy document processing)
8. **Celery Worker** → **Supabase** (persist results)

---

## 2. Render Deployment

### 2.1 Service Definition

The infrastructure is defined in `render.yaml` at the project root.

#### Web Service

```yaml
type: web
name: scholarform-backend
runtime: python
rootDir: backend
buildCommand: pip install -r requirements-render.txt
startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --log-level info --workers ${WEB_CONCURRENCY:-1}
healthCheckPath: /api/v1/health/live
```

- **Runtime:** Python 3.12.2 (from `runtime.txt` and `PYTHON_VERSION` env var)
- **Build:** Installs from `requirements-render.txt` which chains `requirements.txt`
- **Start:** Uvicorn with configurable worker count (`WEB_CONCURRENCY` env var, default 1)
- **Health:** `GET /api/v1/health/live` — used by Render's health checker and CI/CD gate
- **Memory profile:** 512MB (Render free tier); set `LOW_MEMORY_MODE=true`, `PRELOAD_AI_MODELS=false`

#### Celery Worker

```yaml
type: worker
name: scholarform-celery-worker
runtime: python
rootDir: backend
buildCommand: pip install -r requirements-render.txt
startCommand: celery -A app.tasks.celery_tasks worker -Q interactive,batch -c ${WORKER_CONCURRENCY:-2} --loglevel=info --prefetch-multiplier=1
```

- **Queues:** `interactive` (user-facing, concurrency 2) and `batch` (bulk, concurrency 2)
- **Prefetch:** `--prefetch-multiplier=1` ensures fair task distribution
- **Broker:** Upstash Redis via `CELERY_BROKER_URL`

#### Redis

```yaml
type: redis
name: scholarform-redis
plan: free
maxmemoryPolicy: allkeys-lru
```

- **Plan:** Render free tier Redis
- **Eviction:** `allkeys-lru` — evicts least-recently-used keys when memory is full
- **Note:** In production, the application connects to **Upstash Redis** via `REDIS_URL` env var (not the Render Redis). The Render Redis service is defined for compatibility.

### 2.2 Environment Variable Groups

Shared configuration is defined in `envVarGroups.shared-config` within `render.yaml`:

| Category | Key Variables |
|----------|--------------|
| **Python** | `PYTHON_VERSION=3.12.2` |
| **Memory** | `LOW_MEMORY_MODE=false`, `PRELOAD_AI_MODELS=false`, `RAG_USE_TRANSFORMERS=false` |
| **Pipeline** | `GROBID_ENABLED=true`, `USE_DOCLING_FALLBACK=true`, `PYMUPDF_FALLBACK=true`, `PIPELINE_DOCLING_FORCE=true` |
| **Enhancements** | `ENHANCEMENTS_ENABLED=true`, `ENHANCEMENT_OCR_ENABLED=true`, `ENHANCEMENT_KEYWORD_ENABLED=true` |
| **Queue** | `ENHANCEMENT_QUEUE_ENABLED=true`, `ENHANCEMENT_QUEUE_PROVIDER=celery` |
| **AI** | `ENABLE_NVIDIA_REASONER=true`, `ENABLE_LLM_PDF_PARSER=true`, `USE_LLM_CLASSIFICATION=true` |
| **Security** | `FORCE_HTTPS=true`, `DEBUG=false`, `ENABLE_LEGACY_ROUTES=false` |
| **Monitoring** | `ENABLE_STRUCTURED_LOGGING=true`, `ENABLE_FILE_CLEANUP=true` |
| **Circuit Breaker** | `EXTERNAL_CIRCUIT_BREAKER_ENABLED=true` |
| **Redis** | `REDIS_URL=${REDIS_URL}` |

### 2.3 Production Runtime Profile

For the 512MB Render free tier, apply this profile in the Render dashboard:

```env
LOW_MEMORY_MODE=true
PRELOAD_AI_MODELS=false
RAG_USE_TRANSFORMERS=false
ENHANCEMENT_QUEUE_ENABLED=false
ENABLE_STRUCTURED_LOGGING=true
ENABLE_FILE_CLEANUP=true
ENABLE_LLM_PDF_PARSER=false
USE_LLM_CLASSIFICATION=false
CROSSREF_MAX_WORKERS=1
```

### 2.4 Deployment Methods

#### Deploy Hook (Recommended)

```bash
curl -X POST https://api.render.com/deploy/srv-xxxxx?key=yyyyy
```

Triggers a deploy without API authentication. Used by CI/CD.

#### Render API

```bash
curl -X POST https://api.render.com/v1/services/srv-xxxxx/deploys \
  -H "Authorization: Bearer ${RENDER_API_KEY}"
```

Requires service ID (starts with `srv-`).

---

## 3. Hugging Face Spaces Deployment

### 3.1 Service Pairs (12 Spaces)

Each AI service runs as a **primary** and **shadow** instance on HF Spaces for high availability. The backend uses `*_URLS` environment variables (comma-separated) for automatic failover.

| Service | Primary URL | Shadow URL | Health Path | Template |
|---------|------------|------------|-------------|----------|
| **GROBID** | `rohith083-scholarform-grobid-primary` | `rohith083-scholarform-grobid-shadow` | `/api/isalive` | `deploy/hf/grobid-service/` |
| **Docling** | `rohith083-scholarform-docling-primary` | `rohith083-scholarform-docling-shadow` | `/` | `deploy/hf/docling-service/` |
| **OCR** | `rohith083-scholarform-ocr-primary` | `rohith083-scholarform-ocr-shadow` | `/` | `deploy/hf/ocr-service/` |
| **DOCX Converter** | `rohith083-scholarform-docx-converter-primary` | `rohith083-scholarform-docx-converter-shadow` | `/` | `deploy/hf/docx-converter-service/` |
| **LLMPDFParser** | `rohith083-scholarform-LLMPDFParser-primary` | `rohith083-scholarform-LLMPDFParser-shadow` | `/` | `deploy/hf/LLMPDFParser-service/` |
| **LLMClassifier** | `rohith083-scholarform-LLMClassifier-primary` | `rohith083-scholarform-LLMClassifier-shadow` | `/` | `deploy/hf/LLMClassifier-service/` |

### 3.2 Service Details

#### GROBID (Metadata Extraction)

- **Base image:** `lfoppiano/grobid:0.8.2`
- **Framework:** FastAPI proxy wrapping GROBID Java service
- **Port:** 7860 (HF Spaces default)
- **Configuration:** `grobid.yaml` tunes models (BidLSTM_CRF for header/citation), sets `nb_threads: 1`, disables consolidation service
- **Startup:** `start.sh` copies config, launches GROBID service, waits for `/api/isalive`, then starts uvicorn proxy
- **Endpoint:** `POST /api/processHeaderDocument`, `POST /api/processFulltextDocument`
- **Health check:** `GET /api/isalive` (proxied to internal GROBID on port 8070)

```bash
# Deploy template files
cp -r deploy/hf/grobid-service/* /path/to/hf-space/
```

#### Docling (Layout-Aware PDF Analysis)

- **Base image:** `python:3.11-slim`
- **Framework:** FastAPI with `docling` library
- **Dependencies:** `docling`, `fastapi`, `uvicorn`, `python-multipart`
- **Endpoint:** `POST /analyze` — accepts multipart file upload, returns markdown text
- **Error handling:** Returns 503 if `DocumentConverter` fails to initialize

#### OCR (RapidOCR Engine)

- **Base image:** `python:3.11-slim`
- **Framework:** FastAPI with `rapidocr-onnxruntime`
- **Dependencies:** `rapidocr-onnxruntime`, `numpy`, `Pillow`
- **Endpoint:** `POST /ocr` — accepts image upload, returns extracted text lines
- **Service state:** Global `_engine` instance loaded at startup; returns 503 if unavailable

#### DOCX Converter (LibreOffice)

- **Base image:** `python:3.11-slim`
- **Framework:** FastAPI + LibreOffice headless
- **Dependencies:** `libreoffice-writer`, `libreoffice-calc`, `libreoffice-impress`
- **Endpoint:** `POST /convert?to=docx|pdf|txt` — converts any supported format
- **Engine detection:** Checks for `soffice` binary at health check; returns 503 if missing
- **Timeout:** 180 seconds per conversion

#### LLMPDFParser (LaTeX/Markdown PDF Parser)

- **Base image:** `python:3.10-slim`
- **Framework:** FastAPI + HuggingFace Transformers
- **Model:** `facebook/LLMPDFParser-small` (configurable via `LLMPDFParser_MODEL`)
- **Dependencies:** `torch`, `transformers`, `PyMuPDF`, `Pillow`
- **Endpoint:** `POST /parse` — accepts PDF, returns markdown
- **Limits:** `LLMPDFParser_MAX_PAGES=30`, `LLMPDFParser_MAX_TOKENS=4096`
- **Device:** Auto-detects CUDA; falls back to CPU
- **Typical startup:** 2-5 minutes (model weight download + loading)

#### LLMClassifier (Block-Type Classification)

- **Base image:** `python:3.10-slim`
- **Framework:** FastAPI + HuggingFace Transformers
- **Model:** `allenai/LLMClassifier_scivocab_uncased` (configurable via `LLMClassifier_MODEL`)
- **Dependencies:** `torch`, `transformers`
- **Endpoint:** `POST /predict` — accepts JSON `{"texts": ["..."]}` returns classification per text
- **Labels:** `HEADING`, `ABSTRACT`, `BODY`, `REFERENCES`, `FIGURE_CAPTION`, `TABLE_CAPTION`, `ACKNOWLEDGEMENTS`, `EQUATION`, `METHODOLOGY`, `CONCLUSION`, `AUTHOR_INFO`, `TITLE`
- **Max length:** 512 tokens (configurable via `LLMClassifier_MAX_LENGTH`)

### 3.3 Creating a New HF Space

For each service (primary and shadow):

1. Create a new Docker Space on [Hugging Face Spaces](https://huggingface.co/spaces):
   - SDK: Docker
   - Space Hardware: Free (2 vCPU + 16GB RAM recommended for LLMPDFParser/LLMClassifier)
2. Copy the template files from `deploy/hf/<service>/` into the Space repository
3. Set environment variables in the Space settings if applicable
4. The container starts serving on `localhost:SERVICE_PORT`
5. Add the URL to the backend `.env.render` and GitHub Secrets

### 3.4 Failover Mechanism

The backend uses URL list variables for automatic failover:

```env
# _URLS takes precedence over single _URL
GROBID_URLS=http://localhost:SERVICE_PORT,http://localhost:SERVICE_PORT
GROBID_URL=http://localhost:SERVICE_PORT    # fallback if URLS not set

# Health check paths
GROBID_HEALTH_PATH=/api/isalive
DOCLING_HEALTH_PATH=/
# ... (all others use /)
```

**Behavior:**
1. Backend queries the first URL in the comma-separated list
2. If request fails (timeout, 5xx, circuit breaker open), tries the next URL
3. Marks failed endpoints temporarily (circuit breaker pattern with `pybreaker`)
4. Keepalive probes all endpoints every 14 minutes

---

## 4. Frontend (Vercel) Deployment

### 4.1 Configuration

The frontend is a Next.js 16 application deployed on Vercel. Configuration is in `frontend/next.config.mjs`:

```mjs
// CDN support for static assets
assetPrefix: process.env.CDN_URL || ""

// Security headers
async headers() {
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  // _next/static and /static cached 1 year (immutable)
}
```

### 4.2 Deployment Command

```bash
cd frontend
VERCEL_ORG_ID=<org_id> VERCEL_PROJECT_ID=<project_id> \
  npx vercel@latest deploy --prod --yes --token <token>
```

### 4.3 Required Environment Variables (Vercel)

Set these in Vercel Dashboard → Project Settings → Environment Variables:

```env
# Supabase (public client)
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>

# Backend API
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com
NEXT_PUBLIC_LATEX_EXPORT_ENABLED=false

# Analytics (PostHog removed — use Prometheus metrics)
```

---

## 5. Monitoring Stack (Prometheus + Grafana)

### 5.1 Prometheus Configuration

**Deployment config** (`deploy/prometheus/error_budget.yml`):
- Scrape interval: 15s
- Alerting rules for error budget, latency, and resource exhaustion

**Local dev config** (`backend/docker/prometheus/prometheus.yml`):
- Scrapes `host.docker.internal:8000/metrics`
- Label: `environment: 'dev'`

**Ops provisioning** (`ops/grafana/provisioning/datasources/prometheus.yml`):
```yaml
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

### 5.2 Prometheus Alerting Rules

| Alert | Expression | Threshold | Severity | For |
|-------|-----------|-----------|----------|-----|
| **ServiceDown** | `up{job="scholarform"} == 0` | — | Critical | 2m |
| **HighErrorRate** | `5xx rate / total rate` | > 5% | Warning | 5m |
| **HighLatency** | `p95 latency` | > 5s | Warning | 5m |
| **DBPoolExhausted** | `active_connections` | > 18/20 | Critical | 2m |
| **RedisMemoryHigh** | `used_bytes / max_bytes` | > 90% | Warning | 5m |
| **QueueBacklog** | `interactive queue depth` | > 100 | Warning | 10m |
| **RateLimitSpike** | `rate_limited_total` | > 10/s | Info | 5m |
| **DiskSpaceLow** | `avail_bytes / size_bytes` | < 10% | Critical | 10m |

### 5.3 Grafana Dashboard

**Dashboard:** `deploy/grafana/dashboards/scholarform-production.json`

**Panels:**
1. **API Request Rate** — `rate(http_requests_total[5m])` by method and path
2. **Error Rate** — percentage of 5xx responses (thresholds: yellow at 1%, red at 5%)
3. **Response Latency** — p50, p95, p99 latency with histogram quantiles
4. **Active Users** — count of active sessions
5. **Pipeline Processing Rate** — documents processed per second
6. **API Key Usage Rate** — requests by provider
7. **Database Connection Pool** — active connections (gauge, max 20)
8. **Redis Memory Usage** — percentage of max memory (gauge)
9. **Error Budget Remaining (30-day)** — SLO-based error budget gauge
10. **Celery Queue Depth** — interactive and batch queue sizes

**Provisioning** (`ops/grafana/provisioning/dashboards/scholarform.yml`):
```yaml
providers:
  - name: "ScholarForm AI"
    type: file
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/dashboards
```

### 5.4 Deploying the Monitoring Stack

For local development (docker-compose):

```bash
cd backend/docker
docker-compose up prometheus grafana
```

For production, deploy Prometheus + Grafana on a separate VM or container service. Configure:
1. Render backend's `/metrics` endpoint as a Prometheus target
2. Grafana datasource pointing to the Prometheus instance
3. Import `scholarform-production.json` dashboard
4. Configure Alertmanager for PagerDuty or Slack notifications

---

## 6. Docker Builds & Container Registry

### 6.1 Backend Dockerfile

Located at `backend/docker/Dockerfile` — multi-stage build:

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements-render.txt requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-render.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime
COPY --from=builder /install /usr/local
COPY app/ app/
COPY alembic.ini alembic/ alembic/
COPY docker-entrypoint.sh /app/
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live')" || exit 1
CMD ["/app/docker-entrypoint.sh"]
```

**Entrypoint** (`docker-entrypoint.sh`) runs Alembic migrations if `SUPABASE_DB_URL` is set, then starts Uvicorn.

### 6.2 Multi-architecture Builds

Supports `linux/amd64` and `linux/arm64`:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/scholarform/backend:latest \
  -f backend/docker/Dockerfile \
  --push \
  backend/
```

### 6.3 Docker Compose (Full Local Stack)

Located at `backend/docker/docker-compose.yml`:

| Service | Image | Purpose |
|---------|-------|---------|
| `grobid` | `lfoppiano/grobid:0.8.0` | Local metadata extraction |
| `redis` | `redis:7-alpine` | Cache + broker |
| `clamav` | `clamav/clamav:latest` | Malware scanning |
| `celery_worker` | (build) | Interactive queue worker |
| `celery_worker_batch` | (build) | Batch queue worker |

```bash
cd backend/docker
docker-compose up --build
```

### 6.4 .dockerignore

Both root-level `.dockerignore` and `backend/docker/.dockerignore` exclude:
- `.git/`, `__pycache__/`, `*.pyc`
- `.env`, `.secrets.baseline`
- `tests/`, `docs/`, `*.md`
- `node_modules/`, `.next/`
- `deploy/`, `.github/`

### 6.5 Dev Container

`.devcontainer/Dockerfile` provides a consistent development environment with Python 3.12-slim, system dependencies (curl, git, nodejs, npm), and both `requirements.txt` + `requirements-dev.txt` pre-installed.

---

## 7. Environment Configuration

### 7.1 Organization

| File | Location | Purpose |
|------|----------|---------|
| `.env.example` | `backend/` | CI-safe mock values (all keys mocked) |
| `.env.render` | `backend/` | Production secrets and URLs (git-crypted) |
| `.env.template` | `backend/` | Template with all variables documented |
| `.env.example` | `frontend/` | Frontend env template |
| `.env.template` | `frontend/` | Frontend env template (same content) |
| `envVarGroups` | `render.yaml` | Shared production config |

### 7.2 Backend Environment Variables

#### Database / Auth

| Variable | Source | Description |
|----------|--------|-------------|
| `SUPABASE_URL` | `.env.render` | Supabase project URL |
| `SUPABASE_JWKS_URL` | `.env.render` | JWKS endpoint for JWT verification |
| `SUPABASE_DB_URL` | Secret | Direct PostgreSQL connection string |
| `SUPABASE_ANON_KEY` | `.env.render` | Public anon key (safe to expose) |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret | Admin key (bypasses RLS) |
| `SUPABASE_JWT_SECRET` | Secret | JWT signing secret |

#### Security / CORS

| Variable | Description |
|----------|-------------|
| `ALGORITHM=HS256` | JWT signing algorithm |
| `SIGNED_URL_SECRET` | Secret for signed URL generation |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `FORCE_HTTPS=true` | Redirect HTTP to HTTPS |
| `ENABLE_LEGACY_ROUTES=false` | Disable deprecated endpoints |

#### LLM / AI Providers

| Variable | Description |
|----------|-------------|
| `NVIDIA_API_KEY` | NVIDIA NIM API key (primary tier) |
| `NVIDIA_MODEL=nvidia_nim/meta/llama-3.3-70b-instruct` | Primary model |
| `GROQ_API_KEY` | Groq API key (first fallback) |
| `GROQ_MODEL=groq/llama-3.3-70b-versatile` | Fallback model |
| `DEEPSEEK_API_KEY` | DeepSeek API key (third fallback) |
| `OPENAI_API_KEY` | OpenAI API key (optional) |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) |
| `OPENROUTER_API_KEY` | OpenRouter API key (optional) |
| `OPENROUTER_MODEL=openai/gpt-4o-mini` | Default OpenRouter model |

#### External Service URLs

Each service has a URL list (primary + shadow) and a legacy single URL:

| Variable | Format | Health Path |
|----------|--------|-------------|
| `GROBID_URLS` | `url1,url2` | `/api/isalive` |
| `GROBID_URL` | single URL | — |
| `DOCLING_URLS` / `DOCLING_URL` | comma-separated | `/` |
| `OCR_URLS` / `OCR_URL` | comma-separated | `/` |
| `DOCX_CONVERTER_URLS` / `DOCX_CONVERTER_URL` | comma-separated | `/` |
| `LLM_PDF_PARSER_URLS` / `LLM_PDF_PARSER_URL` | comma-separated | `/` |
| `LLM_CLASSIFIER_URLS` / `LLM_CLASSIFIER_URL` | comma-separated | `/` |

**Rules:**
- `*_URLS` takes precedence over `*_URL` when both are set
- If the first URL in the list fails, the next is tried (failover)
- Health check paths are separate per service

#### Redis / Celery

| Variable | Description |
|----------|-------------|
| `REDIS_ENABLED=true` | Enable Redis cache |
| `REDIS_URL` | Upstash Redis connection string (TLS) |
| `REDIS_HOST` | Upstash hostname |
| `REDIS_PORT=6379` | Redis port |
| `CELERY_BROKER_URL` | Celery broker (Redis with TLS) |
| `CELERY_RESULT_BACKEND` | Celery result store (Redis with TLS) |
| `WORKER_CONCURRENCY=2` | Celery worker concurrency |

#### Pipeline Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_GROBID_TIMEOUT_SECONDS` | 25 | GROBID request timeout |
| `PIPELINE_DOCLING_TIMEOUT_SECONDS` | 25 | Docling request timeout |
| `PIPELINE_REASONING_TIMEOUT_SECONDS` | 28 | NVIDIA reasoner timeout |
| `PIPELINE_SEMANTIC_TIMEOUT_SECONDS` | 25 | Semantic analysis timeout |
| `PIPELINE_ACQUIRE_TIMEOUT_SECONDS` | 30 | Resource acquisition timeout |
| `PIPELINE_DOCLING_SKIP_DIGITAL_PDF` | false | Skip Docling for digital-native PDFs |
| `PIPELINE_DOCLING_FORCE` | true | Always run Docling |
| `ENABLE_LLM_PDF_PARSER` | true | Enable LLM-based PDF parsing parser |
| `ENABLE_NVIDIA_REASONER` | true | Enable NVIDIA reasoning tier |
| `USE_LLM_CLASSIFICATION` | true | Enable LLMClassifier block classification |

#### Confidence Thresholds

| Variable | Default |
|----------|---------|
| `HEADING_STYLE_THRESHOLD` | 0.4 |
| `HEADING_FALLBACK_CONFIDENCE` | 0.45 |
| `HEURISTIC_CONFIDENCE_HIGH` | 0.95 |
| `HEURISTIC_CONFIDENCE_MEDIUM` | 0.9 |
| `HEURISTIC_CONFIDENCE_LOW` | 0.5 |

#### Cache TTLs

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_CACHE_TTL_SECONDS` | 3600 | LLM response cache |
| `READINESS_CACHE_TTL_SECONDS` | 15 | Readiness probe cache |
| `HEALTH_CACHE_TTL_SECONDS` | 15 | Health endpoint cache |
| `CSL_SEARCH_CACHE_TTL_SECONDS` | 300 | CSL citation search |
| `CSL_FETCH_CACHE_TTL_SECONDS` | 1800 | CSL style fetch |
| `GENERATOR_SESSION_CACHE_TTL_SECONDS` | 2 | Generator session |
| `GENERATOR_MESSAGES_CACHE_TTL_SECONDS` | 1 | Generator messages |
| `DOCUMENT_STATUS_CACHE_TTL_SECONDS` | 1 | Document status |

#### Rate Limits / Upload

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE` | 52428800 | 50MB max upload |
| `MAX_BATCH_FILES` | 10 | Max files per batch |
| `UPLOADS_PER_MINUTE` | 10 | Rate limit per minute |
| `GLOBAL_RATE_LIMIT_PER_MINUTE` | 120 | Global API rate limit |

#### Miscellaneous

| Variable | Description |
|----------|-------------|
| `CROSSREF_MAILTO` | Email for CrossRef API identification |
| `DEFAULT_TEMPLATE=none` | Default formatting template |
| `LIBREOFFICE_PATH` | Path to LibreOffice (local only) |
| `OLLAMA_URL` | Ollama endpoint (local only) |
| `CLAMAV_HOST` | ClamAV host (optional) |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED=true` | Enable circuit breaker for external services |

### 7.3 Frontend Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key |
| `NEXT_PUBLIC_API_URL` | Yes | Backend Render URL |
| `NEXT_PUBLIC_LATEX_EXPORT_ENABLED` | No | LaTeX export toggle |
| `CDN_URL` | No | CDN prefix for static assets |

### 7.4 GitHub Secrets

Required secrets for CI/CD workflows:

| Secret | Workflow | Purpose |
|--------|----------|---------|
| `PROD_BACKEND_URL` | Production | Backend health check target |
| `RENDER_API_KEY` | Both | Render API authentication |
| `RENDER_PROD_SERVICE_ID` | Production | Render production service ID (`srv-*`) |
| `RENDER_PROD_DEPLOY_HOOK_URL` | Production | Render deploy hook URL |
| `RENDER_STAGING_SERVICE_ID` | Staging | Render staging service ID |
| `VERCEL_TOKEN` | Production | Vercel API token |
| `VERCEL_ORG_ID` | Production | Vercel team ID |
| `VERCEL_PROD_PROJECT_ID` | Production | Vercel project ID |
| `DATABASE_URL` | Production | Direct DB URL for migrations |
| `HF_GROBID_PRIMARY_URL` | Keepalive | HF Space health probes |
| `HF_GROBID_SHADOW_URL` | Keepalive | — |
| `HF_DOCLING_PRIMARY_URL` | Keepalive | — |
| `HF_DOCLING_SHADOW_URL` | Keepalive | — |
| `HF_OCR_PRIMARY_URL` | Keepalive | — |
| `HF_OCR_SHADOW_URL` | Keepalive | — |
| `HF_DOCX_PRIMARY_URL` | Keepalive | — |
| `HF_DOCX_SHADOW_URL` | Keepalive | — |

---

## 8. CI/CD Pipeline

### 8.1 Production Deployment

**Workflow:** `.github/workflows/deploy-production.yml`

**Triggers:** `workflow_dispatch` (manual) or automatic when Frontend CI succeeds on `main`.

**Pipeline stages:**

```
verify-ci-gates ──▶ pre-deploy-health ──▶ deploy-production
                                              │
                                      ┌───────┴────────┐
                                      ▼                ▼
                              Deploy Hook        Render API
                              (preferred)        (fallback)
                                      │
                                      ▼
                              Wait for Health (20 attempts, 15s interval)
                                      │
                                      ▼
                          Post-deploy Verification
                                      │
                              ┌───────┴───────┐
                              ▼               ▼
                      Auto-rollback       Deploy Frontend
                      (if health fails)   (Vercel)
```

**Stage details:**

1. **verify-ci-gates**
   - Resolves the commit SHA from the triggering workflow
   - Verifies `backend-ci.yml`, `frontend-ci.yml`, and `security.yml` all passed for this commit
   - If no workflow run exists (path filter excluded), passes (no news is good news)
   - Blocks deploy if any required CI workflow failed

2. **pre-deploy-health**
   - Calls `GET {PROD_BACKEND_URL}/api/v1/health/live`
   - Logs the current production health status (advisory, does not block)

3. **deploy-production** (main deployment stage)
   - **Preflight validation:** Checks all required secrets are present
   - **Render service verification:** Confirms service ID exists via Render API
   - **Vercel project verification:** Confirms project ID exists via Vercel API
   - **Database migrations:** Runs `alembic upgrade head` against production DB
   - **Backend deploy:** Triggers via Deploy Hook or Render API
   - **Wait for health:** Polls health endpoint every 15s for up to 5 minutes
   - **Post-deploy verification:** Final health check
   - **Auto-rollback:** If health check fails after successful deploy, triggers Rollback API
   - **Frontend deploy:** `npx vercel@latest deploy --prod`

### 8.2 Staging Deployment

**Workflow:** `.github/workflows/deploy-staging.yml`

**Triggers:** Push to `develop` branch or `workflow_dispatch`.

**Concurrency:** `group: staging` with `cancel-in-progress: true` — new pushes cancel in-flight deploys.

**Pipeline stages:**

```
test ──▶ deploy
```

- **test:** Runs `pytest`, `ruff`, and `mypy` (continue-on-error for mypy)
- **deploy:** Triggers Render deploy via API to `RENDER_STAGING_SERVICE_ID`

### 8.3 Keepalive Workflow

Triggers every 14 minutes (`*/14 * * * *`) to prevent free-tier services from spinning down:

```
Render backend:  GET /api/v1/health/live
GROBID:          GET /api/isalive (primary + shadow)
Docling:         GET / (primary + shadow)
OCR:             GET / (primary + shadow)
DOCX Converter:  GET / (primary + shadow)
```

**Failure behavior:** If both primary and shadow fail for any service pair, the job fails visibly but does not page (informational).

### 8.4 CI Gate Requirements

Before production deploy, these workflows must pass:

| Workflow File | What It Checks |
|--------------|----------------|
| `backend-ci.yml` | `ruff` (E9,F63,F7,F82), `mypy` (continue-on-error), `pytest` (skip integration + slow) |
| `frontend-ci.yml` | `npm ci` → `eslint` → `vitest` → `build` → Lighthouse → Playwright e2e |
| `security.yml` | Dependency vulnerability scan, secret detection |

---

## 9. Production Checklist

### 9.1 Pre-Deploy Verification

Before every production deployment:

- [ ] **CI gates passed:** All three CI workflows (backend, frontend, security) green on target commit
- [ ] **Feature flags reviewed:** No unreleased features accidentally enabled in `render.yaml`
- [ ] **Database migrations:** Alembic migrations reviewed and backward-compatible
- [ ] **Secret availability:** `RENDER_PROD_DEPLOY_HOOK_URL`, `RENDER_API_KEY`, `VERCEL_TOKEN` all valid
- [ ] **Current production healthy:** `GET /api/v1/health/live` returns 200
- [ ] **HF Spaces healthy:** All 6 service pairs pass health checks
- [ ] **Upstash Redis:** Available and memory below 80%
- [ ] **Supabase:** Connection pool not exhausted (< 15 active connections)
- [ ] **Changelog:** Release notes drafted for the deployment

### 9.2 Deploy Process

1. Merge PR to `main` (frontend CI auto-triggers)
2. Navigate to GitHub Actions → `deploy-production` → `Run workflow`
3. Select `main` branch
4. Monitor pipeline:
   - CI verification (30s)
   - Pre-deploy health (10s)
   - Backend deploy (2-5 min)
   - Health poll (1-5 min)
   - Vercel deploy (2-3 min)
5. Verify in production:
   - `GET /api/v1/health/live` returns 200
   - `GET /api/v1/health/ready` returns 200
   - Smoke test: upload a sample manuscript
   - Grafana dashboard shows no error rate spike

### 9.3 Post-Deploy Verification

- [ ] Health endpoint returns 200
- [ ] Readiness endpoint returns 200
- [ ] Metrics endpoint returns prometheus data
- [ ] Document upload and processing works end-to-end
- [ ] GROBID requests succeed (with shadow failover)
- [ ] Docling analysis returns valid markdown
- [ ] OCR extraction returns text
- [ ] DOCX conversion produces valid files
- [ ] Celery workers processing tasks
- [ ] Supabase queries completing within normal latency
- [ ] Redis cache TTLs respected
- [ ] Error rate unchanged (monitoring via /metrics)
- [ ] Error budget not consumed by deploy (SLO: 99.9%)

---

## 10. Rollback Procedure

### 10.1 Automated Rollback

The production CI/CD workflow includes auto-rollback:

```yaml
steps:
  - name: Auto-rollback on health check failure
    if: failure() && (steps.deploy.outcome == 'success' || steps.deploy-api.outcome == 'success')
    run: |
      DEPLOY_ID="${{ steps.deploy.outputs.deploy_id || steps.deploy-api.outputs.deploy_id }}"
      curl -X POST "https://api.render.com/v1/services/${RENDER_PROD_SERVICE_ID}/deploys/${DEPLOY_ID}/rollback" \
        -H "Authorization: Bearer ${RENDER_API_KEY}"
```

Triggers when:
- A `deploy` step succeeded (deploy completed without error)
- A subsequent step failed (health check, post-deploy verification)

### 10.2 Manual Rollback

If automated rollback fails or the issue is discovered later:

#### Frontend Rollback

```bash
# List deployments
npx vercel list --token $VERCEL_TOKEN

# Rollback to a specific deployment
npx vercel rollback <deployment-id> --token $VERCEL_TOKEN
```

Or use Vercel Dashboard → Deployments → ⋮ → Rollback to this deployment.

#### Backend Rollback

**Via Render Dashboard:**
1. Go to Render Dashboard → `scholarform-backend`
2. Click "Manual Deploy" → "Revert to previous deploy"
3. Select the last known-good deploy
4. Monitor health endpoint

**Via Render API:**

```bash
# List deploys
curl -H "Authorization: Bearer ${RENDER_API_KEY}" \
  "https://api.render.com/v1/services/${RENDER_PROD_SERVICE_ID}/deploys"

# Rollback to a specific deploy
curl -X POST \
  "https://api.render.com/v1/services/${RENDER_PROD_SERVICE_ID}/deploys/${DEPLOY_ID}/rollback" \
  -H "Authorization: Bearer ${RENDER_API_KEY}"
```

### 10.3 Rollback Verification

After rollback, verify:

1. `GET /api/v1/health/live` returns 200
2. All 6 HF service pairs are reachable
3. Frontend loads without errors
4. Document processing pipeline works
5. Grafana shows stable metrics (no error spike)

### 10.4 Database Rollback

If a deploy includes database migrations:

```bash
cd backend
alembic downgrade -1   # Revert one migration
```

**Note:** Alembic migrations run during CI/CD. If automatic rollback triggers before the migration step, no DB rollback is needed. If migrations were committed, execute `alembic downgrade` manually.

---

## 11. Error Budget & SLOs

### 11.1 Service Level Objectives

| Metric | Target | Measurement Period |
|--------|--------|-------------------|
| **Availability** | 99.9% (8h 46m max downtime/year) | 30-day rolling |
| **Error Rate** | < 1% 5xx responses | 5-minute window |
| **Latency p50** | < 2s | 5-minute window |
| **Latency p95** | < 5s | 5-minute window |
| **Latency p99** | < 10s | 5-minute window |
| **DB Pool** | < 15 active connections | 2-minute window |
| **Celery Interactive Queue** | < 100 depth | 10-minute window |

### 11.2 Error Budget Calculation

```promql
(1 - (5xx_total / request_total)) / 0.999 * 100
```

- **Budget starts:** 100% (allowable errors = 0.1% of total requests)
- **Burned by:** Each 5xx response consumes a portion of the error budget
- **Window:** 30-day rolling
- **Alert thresholds:**
  - Green: > 50% remaining
  - Yellow: 25-50% remaining (watch)
  - Red: < 25% remaining (critical — deploy freeze recommended)

### 11.3 Burn Rate Alerts (from `deploy/prometheus/error_budget.yml`)

| Alert | Condition | Response Time |
|-------|-----------|--------------|
| `ScholarFormHighErrorRate` | Error rate > 5% for 5m | Immediate investigation |
| `ScholarFormHighLatency` | p95 > 5s for 5m | Performance review |
| `ScholarFormServiceDown` | `up == 0` for 2m | On-call pages |
| `ScholarFormQueueBacklog` | Queue > 100 for 10m | Scale workers |
| `ScholarFormDBPoolExhausted` | Connections > 18 for 2m | Connection audit |

---

## Appendix A: Deployment Architecture Diagrams

### A.1 Network Flow

```
Internet
    │
    ├──▶ Vercel (CDN + SSR)
    │       │
    │       └──▶ Render Web Service :8000
    │               │
    │               ├──▶ Supabase :5432
    │               ├──▶ Upstash Redis :6379
    │               └──▶ HF Spaces :7860
    │                       │
    │                       ├──▶ GROBID (internal :8070)
    │                       ├──▶ Docling
    │                       ├──▶ OCR
    │                       ├──▶ DOCX Converter
    │                       ├──▶ LLMPDFParser
    │                       └──▶ LLMClassifier
    │
    └──▶ Render Celery Worker
            │
            ├──▶ Upstash Redis (broker)
            ├──▶ Supabase (persistence)
            └──▶ HF Spaces (processing)
```

### A.2 File Reference Map

| File | Content |
|------|---------|
| `render.yaml` | Render service definitions |
| `backend/docker/Dockerfile` | Production image build |
| `backend/docker/docker-compose.yml` | Local full stack |
| `backend/requirements-render.txt` | Production Python deps |
| `backend/runtime.txt` | Python version pin |
| `backend/.env.render` | Production secrets |
| `deploy/hf/*/Dockerfile` | HF Space Dockerfiles |
| `deploy/hf/COPY_TO_SPACES.md` | HF URL map |
| `deploy/prometheus/error_budget.yml` | Prometheus alerting rules |
| `deploy/grafana/dashboards/scholarform-production.json` | Production dashboard |
| `ops/grafana/provisioning/` | Grafana auto-provisioning |
| `.github/workflows/deploy-production.yml` | Production CI/CD |
| `.github/workflows/deploy-staging.yml` | Staging CI/CD |
| `frontend/next.config.mjs` | Vercel/CDN config |
| `.dockerignore` | Docker build exclusions |
| `backend/docker/.dockerignore` | Docker build exclusions (nested) |
| `.devcontainer/Dockerfile` | Dev environment |

---

## 12. Testing — Pre-Deploy Verification & Smoke Tests

### Pre-Deploy Verification Tests

Run these checks before every production deployment:

```bash
#!/bin/bash
# pre-deploy-verify.sh

echo "=== Pre-Deploy Verification ==="

# 1. All CI gates passed
echo "1. Checking CI gates..."
gh run list --workflow backend-ci.yml --branch main --limit 1 --json conclusion
gh run list --workflow frontend-ci.yml --branch main --limit 1 --json conclusion
gh run list --workflow security.yml --branch main --limit 1 --json conclusion

# 2. Current production healthy
echo "2. Checking production health..."
curl -s -o /dev/null -w "Health: %{http_code}\n" https://api.scholarform.ai/api/v1/health/live
curl -s -o /dev/null -w "Readiness: %{http_code}\n" https://api.scholarform.ai/api/v1/health/ready

# 3. HF Services reachable
echo "3. Checking HF Spaces..."
for url in $(echo "$GROBID_URLS" | tr ',' ' '); do
    curl -s -o /dev/null -w "$url: %{http_code}\n" "$url/api/isalive"
done

# 4. Version sync
echo "4. Checking version consistency..."
python scripts/sync_version.py --check

# 5. Migration state
echo "5. Checking migration state..."
alembic check
```

### Smoke Test Procedures

After deployment, run the smoke test suite:

```bash
cd backend
pytest tests/test_smoke.py -v --no-cov --timeout=30

# Expected output:
# ✅ test_health_endpoint ......... PASSED
# ✅ test_readiness_endpoint ..... PASSED
# ✅ test_upload_document ........ PASSED
# ✅ test_list_templates ......... PASSED
# ✅ test_grobid_fallback ........ PASSED
# ✅ test_document_status ........ PASSED
```

Smoke test coverage (`tests/test_smoke.py`):

| Test | Endpoint / Operation | Expected |
|---|---|---|
| `test_health_endpoint` | `GET /api/v1/health/live` | 200 |
| `test_readiness_endpoint` | `GET /api/v1/health/ready` | 200 (or 503 with degraded details) |
| `test_upload_document` | `POST /api/v1/documents/upload` | 202 with job ID |
| `test_list_templates` | `GET /api/v1/templates` | 200 with template list |
| `test_grobid_fallback` | PDF upload via pipeline | Parsing succeeds (possibly via Docling fallback) |
| `test_document_status` | `GET /api/v1/documents/{id}/status` | 200 with valid status |
| `test_llm_generate` | Mocked LLM generation | 200 with generated text |
| `test_frontend_loads` | `GET https://scholarform.ai` | 200 with HTML |

### Canary Analysis

For gradual rollouts, use the canary deployment pattern:

```bash
# 1. Deploy to canary instance
render deploy --service scholarform-backend-canary

# 2. Route 5% traffic to canary
# (Configure via Render blue/green or a reverse proxy)

# 3. Monitor for 10 minutes
watch -n 30 "\
  curl -s https://canary.scholarform.ai/api/v1/health/live && \
  echo '---' && \
  curl -s https://api.scholarform.ai/api/v1/health/live"

# 4. Compare metrics
# Error rate diff < 1% AND p95 latency diff < 200ms → promote
# Otherwise → rollback canary
```

| Metric | Canary Threshold | Action |
|---|---|---|
| Error rate delta | < 1% vs production | Promote |
| p95 latency delta | < 200 ms vs production | Promote |
| Error rate delta | >= 1% vs production | Rollback |
| p95 latency delta | >= 500 ms vs production | Rollback |

### API Reference — Deployment Health Check Endpoints

| Endpoint | Method | Purpose | Used By |
|---|---|---|---|
| `GET /api/v1/health/live` | GET | Liveness probe | Render health checker, CI/CD gate, Keepalive workflow |
| `GET /api/v1/health/ready` | GET | Readiness with dependency status | Post-deploy verification, canary comparison |
| `GET /health` | GET | Legacy liveness (always 200) | External monitoring |
| `GET /ready` | GET | Legacy readiness | External monitoring |
| `GET /metrics` | GET | Prometheus scrape | Performance comparison between canary and production |

*This document is maintained by the DevOps Team. Review cadence: quarterly. Last updated: July 2026.*
