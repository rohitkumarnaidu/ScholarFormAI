# System Architecture

```mermaid
graph TB
    subgraph USERS["Users"]
        BROWSER["Browser / Client"]
    end

    subgraph VERCEl["Vercel — Next.js 16 (React 19)"]
        FE["Frontend App"]
        FE_MW["Next.js Middleware<br/>25 Protected Routes"]
        STATIC["Static Assets (CDN)"]
    end

    subgraph EDGE["Edge / CDN"]
        CORS["CORS Gateway"]
        SSL["TLS Termination"]
    end

    subgraph RENDER["Render — FastAPI (Uvicorn, Port 8000)"]
        direction TB
        subgraph MIDDLEWARE["11 Middleware Layers (Execution Order)"]
            M1["1. CORSMiddleware<br/>(CORS_ORIGINS allowlist)"]
            M2["2. RequestIdMiddleware<br/>(X-Request-Id assignment)"]
            M3["3. HTTPSRedirectMiddleware<br/>(HTTP→HTTPS, production only)"]
            M4["4. HSTSMiddleware<br/>(Strict-Transport-Security)"]
            M5["5. SlowAPI + RateLimitMiddleware<br/>(120 req/min global)"]
            M6["6. TierRateLimitMiddleware<br/>(guest 5/day, pro unlimited)"]
            M7["7. SecurityHeadersMiddleware<br/>(CSP, X-Frame-Options)"]
            M8["8. MaxBodySizeMiddleware<br/>(60MB limit)"]
            M9["9. CSRFMiddleware<br/>(CSRF tokens)"]
            M10["10. FeatureFlagMiddleware<br/>(X-Feature-Flags, dev)"]
            M11["11. MonitoringMiddleware<br/>(timing + structured logging)"]
        end
        subgraph HTTP_MW["HTTP Middleware (main.py)"]
            HM12["12. lazy_router_loader<br/>(lazy-load v1/v2/preview)"]
            HM13["13. audit_write_operations<br/>(POST/PUT/DELETE audit log)"]
        end
        subgraph PROM["Prometheus Instrumentation"]
            PROM_EXPOSE["GET /metrics<br/>prometheus_fastapi_instrumentator"]
        end
        subgraph HANDLERS["Error Handlers"]
            EH1["HTTPException → build_error_response()"]
            EH2["RequestValidationError → 422 envelope"]
        end
    end

    subgraph V1_ROUTERS["v1 Routers (15 sub-routers, 95 routes)"]
        R1["health<br/>GET /live, /ready"]
        R2["auth<br/>signup, login, me, OTP"]
        R3["documents<br/>upload, batch, status, preview, edit"]
        R4["templates<br/>list, CSL search, CRUD"]
        R5["generator<br/>sessions, SSE, outline, messages"]
        R6["synthesis<br/>multi-doc sessions"]
        R7["feedback<br/>submit, summary"]
        R8["metrics<br/>dashboard, DB health, usage"]
        R9["providers<br/>built-in + custom CRUD (11 routes)"]
        R10["api_keys<br/>user key CRUD + usage (9 routes)"]
        R11["stream<br/>SSE event stream per job"]
        R12["activity<br/>recent, summary"]
        R13["suggestions<br/>generate, accept, reject (7 routes)"]
        R14["billing<br/>Stripe webhook"]
        R15["webhooks<br/>outbound CRUD + delivery log (7 routes)"]
    end

    subgraph V2_ROUTERS["v2 Routers (2 sub-routers)"]
        V2_DOCS["documents<br/>cursor-paginated list"]
        V2_WEBHOOKS["webhooks<br/>v1-compat re-export"]
    end

    subgraph PREVIEW["Preview Router"]
        PV_LIVE["POST /api/v1/preview/live<br/>HTML render <80ms"]
        PV_AI["GET /preview/{sid}/ai-suggest<br/>SSE AI suggestions"]
        PV_WS["WS /api/v1/ws/preview/{sid}<br/>WebSocket live preview"]
    end

    subgraph CELERY["Celery Worker — Render"]
        direction TB
        CQ_INTERACTIVE["Queue: interactive<br/>concurrency=2"]
        CQ_BATCH["Queue: batch<br/>concurrency=2"]
        CELERY_WORKER["celery -A app.tasks.celery_tasks"]
    end

    subgraph SERVICES["Services Layer (27 services)"]
        LLM_SVC["LLM Service<br/>10 providers, 4-tier fallback"]
        AUTH_SVC["Auth / Supabase JWT"]
        GEN_SVC["Generator Session"]
        QUALITY_SVC["Quality Scorer"]
        PREVIEW_RENDER["Preview Renderer"]
        CROSSREF["CrossRef Client"]
        CITATION["Citation Assembly (CSL)"]
        AUDIT["Audit Log Service"]
        ENC["Encryption Service"]
        MODEL_STORE["Model Store"]
    end

    subgraph DATA["Data Layer"]
        PG[("PostgreSQL<br/>Supabase")]
        REDIS[("Redis<br/>Cache + Pub/Sub + Celery")]
        CHROMA[("ChromaDB<br/>RAG Vector Store")]
        STORAGE[("Supabase Storage<br/>File Storage")]
    end

    subgraph HF_SPACES["HuggingFace Spaces (6 service pairs × 2)"]
        GROBID["GROBID<br/>XML Metadata Extraction<br/>Port 8070"]
        DOCLING["Docling<br/>Layout-Aware PDF Analysis"]
        OCR["RapidOCR<br/>Text Extraction"]
        DOCX_CONV["DOCX Converter<br/>LibreOffice Headless"]
        NOUGAT["Nougat<br/>LaTeX/MD PDF Parser"]
        SCIBERT["SciBERT<br/>Block-Type Classification<br/>12 Labels"]
    end

    subgraph LLM_PROVIDERS["LLM Providers (10 built-in)"]
        NVIDIA["NVIDIA NIM<br/>Primary Tier"]
        GROQ["Groq<br/>Fallback Tier 1"]
        OPENROUTER["OpenRouter<br/>Fallback Tier 2"]
        OLLAMA["Ollama Local<br/>Fallback Tier 3"]
        EXTRA["OpenAI / Anthropic<br/>DeepSeek / Google<br/>Cohere / Mistral<br/>(opt-in)"]
    end

    subgraph MONITORING["Monitoring Stack"]
        PROM_SRV["Prometheus<br/>Scrape interval: 15s"]
        GRAFANA["Grafana Dashboard<br/>10 Panels"]
        ALERTMANAGER["Alertmanager<br/>→ PagerDuty / Slack"]
        SENTRY["Sentry<br/>Error Tracking"]
    end

    BROWSER --> FE
    FE --> FE_MW
    FE_MW --> EDGE
    EDGE --> M1
    M1 --> M2 --> M3 --> M4 --> M5 --> M6
    M6 --> M7 --> M8 --> M9 --> M10 --> M11
    M11 --> HM12 --> HM13
    HM13 --> V1_ROUTERS
    HM13 --> V2_ROUTERS
    HM13 --> PREVIEW
    V1_ROUTERS --> LLM_SVC
    V1_ROUTERS --> AUTH_SVC
    V1_ROUTERS --> PG
    V2_ROUTERS --> PG
    PREVIEW --> REDIS
    LLM_SVC --> NVIDIA
    LLM_SVC --> GROQ
    LLM_SVC --> OPENROUTER
    LLM_SVC --> OLLAMA
    LLM_SVC --> EXTRA
    NVIDIA --> PROM_SRV
    GROQ --> PROM_SRV
    OPENROUTER --> PROM_SRV
    V1_ROUTERS --> CELERY_WORKER
    CELERY_WORKER --> CQ_INTERACTIVE
    CELERY_WORKER --> CQ_BATCH
    SERVICES --> PG
    SERVICES --> REDIS
    SERVICES --> CHROMA
    CELERY_WORKER --> REDIS
    CELERY_WORKER --> HF_SPACES
    V1_ROUTERS --> HF_SPACES
    PROM_SRV --> GRAFANA
    PROM_SRV --> ALERTMANAGER
    SENTRY -.-> V1_ROUTERS
```

## Description

This diagram shows the full ScholarForm AI system architecture across all deployment targets:

- **Vercel** hosts the Next.js 16 frontend (React 19) with 25 protected routes via middleware
- **Render** runs the FastAPI backend (Uvicorn on port 8000) with 11 middleware layers applied in order: CORS → Request ID → HTTPS/HSTS → Rate Limit (global + per-tier) → Security Headers → Max Body Size → CSRF → Feature Flags → Monitoring, plus 2 HTTP middleware functions (lazy router loader + audit logging)
- **15 v1 sub-routers** (95+ routes) and **2 v2 sub-routers** handle all API traffic, mounted lazily on first request for sub-2s cold boot
- **Celery worker** consumes two queues: `interactive` (user-facing, concurrency=2) and `batch` (bulk, concurrency=2), with Redis as the broker
- **27 services** handle LLM orchestration (10 providers with 4-tier fallback), authentication, generation sessions, quality scoring, preview rendering, CrossRef validation, citation assembly, audit logging, and encryption
- **Data layer** comprises PostgreSQL (Supabase for primary DB + auth + storage), Redis (cache + pub/sub + Celery broker), and ChromaDB (RAG vector store)
- **6 HuggingFace Spaces service pairs** (primary + shadow for HA) run GROBID, Docling, OCR, DOCX Converter, Nougat, and SciBERT
- **Prometheus + Grafana** scrape metrics from the backend at 15s intervals with 8 alerting rules, plus Sentry for error tracking
