# Performance & Scalability

> **ScholarForm AI** — Enterprise-grade academic manuscript formatting platform.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Caching Strategy](#2-caching-strategy)
3. [Database Performance](#3-database-performance)
4. [Pipeline Performance](#4-pipeline-performance)
5. [Task Queue](#5-task-queue)
6. [Rate Limiting](#6-rate-limiting)
7. [LLM Performance](#7-llm-performance)
8. [Frontend Performance](#8-frontend-performance)
9. [Load Testing](#9-load-testing)
10. [Memory Management](#10-memory-management)
11. [Scaling Strategy](#11-scaling-strategy)
12. [Monitoring & Observability](#12-monitoring--observability)
13. [SLO / SLA Reference](#13-slo--sla-reference)

---

## 1. Overview

### Performance Requirements

| Metric | Target | Source |
| --- | --- | --- |
| API response (p50) | < 500 ms | `test_performance_regression.py` |
| API response (p95) | < 2 s | Locust SLO gate |
| Document parsing | < 2 s | `test_basic_document_parsing_performance` |
| Structure detection | < 1 s | `test_structure_detection_performance` |
| LLM cache hit | < 50 ms | `test_cached_llm_result_returns_in_under_50ms` |
| LLM generate (mocked) | < 3 s | `test_generate_with_model_returns_in_under_3s` |
| Streaming TTFT | < 500 ms | `test_streaming_first_token_latency` |
| Document upload ACK | < 400 ms (p99) | `locustfile.py` UploadUser |
| Template listing | < 80 ms (p99) | `locustfile.py` TemplatesUser |
| WebSocket preview RTT | < 200 ms (p99) | `locustfile.py` PreviewWebSocketUser |
| Pipeline (full, fast mode) | < 900 s (15 min) | `run_pipeline_with_timeout` |
| Pipeline (full, AI mode) | < 900 s (15 min) | Celery `task_soft_time_limit=600` |
| Concurrent pipeline jobs | Max 5 | `_MAX_CONCURRENT_JOBS` semaphore |

### Scalability Targets

| Dimension | Target | Mechanism |
| --- | --- | --- |
| Concurrent users | 200 | Horizontal web workers + Redis rate limiting |
| Requests per second | 100 | Locust SLO gate (`TARGET_RPS=100`) |
| Documents per minute | 10 uploads | `UPLOADS_PER_MINUTE=10` |
| Batch processing | Unlimited (queue) | Celery `batch` queue |
| Storage | Supabase auto-scale | 30-day retention + cleanup task |

---

## 2. Caching Strategy

### Cache Layers

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  In-Memory    │────▶│   Redis      │────▶│  Supabase    │
│  (per-worker) │     │  (shared)    │     │  (persistent)│
└──────────────┘     └──────────────┘     └──────────────┘
```

### Redis Cache (`backend/app/cache/redis_cache.py`)

| Cache | Key Prefix | Default TTL | Description |
| --- | --- | --- | --- |
| GROBID results | `grobid:` | 3600 s (1 h) | Content-hash-keyed parsed metadata |
| LLM responses | `llm_cache:` | 86400 s (24 h) | SHA-256 of prompt+model+params |
| Generator sessions | — | 2.0 s | Per-session data |
| Generator messages | — | 1.0 s | Message list for sessions |
| Generator session list | — | 3.0 s | User session index |
| Generator document | — | 2.0 s | Output document cache |
| Document status | — | 1.0 s | Polling optimization |
| Readiness probe | — | 15 s | `/ready` response |
| Health check | — | 15 s | `/health` response |
| CSL search | — | 300 s (5 min) | Citation style lookups |
| CSL fetch | — | 1800 s (30 min) | Citation style downloads |

Configuration in `CacheSettings`:

- `REDIS_ENABLED` — toggle Redis on/off
- `REDIS_URL` — full connection string
- `LLM_CACHE_TTL_SECONDS` — override LLM TTL (default 3600)

### Graceful Degradation

- `_ensure_client()` lazily initializes Redis on first use
- If Redis is unreachable, all cache reads return `None` and writes are silently dropped
- Pipeline continues normally without caching
- Single warning logged per component, then suppressed

### LLM Response Caching

- Cache key includes: `model`, `temperature`, `max_tokens`, `api_base`, `api_key_prefix`, `system_prompt`, `user_message`
- Cache is bypassed when `stream=True`
- `invalidate_llm_cache(pattern)` supports Redis glob-pattern invalidation
- Cache hits/misses are recorded via `MetricsManager.record_llm_cache_hit/miss`

### Token Blacklisting

- JWT tokens are blacklisted in Redis with `blacklisted_token:{jti}` keys
- TTL matches the token's remaining expiry
- Provides instant revocation without a DB round-trip

---

## 3. Database Performance

### Connection Pooling (`backend/app/db/session.py`)

```python
engine = create_engine(
    db_url,
    pool_size=5,          # Minimum persistent connections
    max_overflow=10,      # Burst connections beyond pool_size (max total = 15)
    pool_timeout=30,      # Seconds to wait for a connection from pool
    pool_recycle=1800,    # Recycle connections after 30 minutes
    pool_pre_ping=True,   # Verify connection health before handing out
)
```

| Parameter | Value | Rationale |
| --- | --- | --- |
| `pool_size` | 5 | Matches typical cloud Postgres connection limits |
| `max_overflow` | 10 | Allows bursts up to 15 concurrent connections |
| `pool_recycle` | 1800 s | Prevents stale SSL connections after idle periods |
| `pool_pre_ping` | True | Eliminates "SSL connection has been closed unexpectedly" errors |
| `pool_timeout` | 30 s | Fails fast rather than queuing indefinitely |

### Degraded Mode

- When `SUPABASE_DB_URL` is unset, `engine` is `None` and `SessionLocal` is `None`
- All DB-dependent endpoints return HTTP 503
- The server starts without crashing — health check reports `"unconfigured"`

### Supabase REST Client (`supabase-py`)

- Used alongside raw SQLAlchemy for document CRUD
- Retry logic in `_run_with_retry()`: 3 attempts, exponential backoff (0.15s × 2^n)
- Transient error detection: `RemoteProtocolError`, `server disconnected`, `timeout`, `connection reset`, `connection aborted`
- `get_supabase_client(refresh=True)` creates a new client instance after transient failures

### Prepared Statements & Indexing

- Supabase automatically indexes primary keys and foreign keys
- `processing_status` table uses `document_id + phase` as upsert match key
- `document_results` uses `document_id` as lookup key
- Alert: No explicit index creation in application code — relies on Supabase/Postgres defaults

---

## 4. Pipeline Performance

### Concurrency Control

```python
_MAX_CONCURRENT_JOBS = 5
_pipeline_semaphore = threading.Semaphore(_MAX_CONCURRENT_JOBS)
_ACQUIRE_TIMEOUT_SECONDS = 30.0  # configurable via PIPELINE_ACQUIRE_TIMEOUT_SECONDS
```

- **Hard cap of 5 concurrent pipeline executions** to prevent OOM
- `acquire(timeout=30.0)` — rejects with "Server is busy" if semaphore unavailable
- Semaphore is released in `finally` block, guaranteeing no leaks

### Per-Stage Timeouts

| Stage | Timeout | Configuration | Retry |
| --- | --- | --- | --- |
| GROBID extraction | 30 s | `PIPELINE_GROBID_TIMEOUT_SECONDS` | 2 retries, backoff=1.0 |
| Docling layout | 30 s | `PIPELINE_DOCLING_TIMEOUT_SECONDS` | 2 retries, backoff=1.0 |
| Semantic parsing | 30 s | `PIPELINE_SEMANTIC_TIMEOUT_SECONDS` | 2 retries, backoff=1.0 |
| AI reasoning | 60 s | `PIPELINE_REASONING_TIMEOUT_SECONDS` | 2 retries, backoff=1.0 |
| Validation | 60 s | Hardcoded in `_run_validation_stage` | 2 retries, backoff=1.0 |
| Formatting | 60 s | Hardcoded in `_run_formatting_stage` | 2 retries, backoff=1.0 |
| Pipeline total | 900 s (15 min) | `run_pipeline_with_timeout` | — |

### Parallel Execution

GROBID + Docling run concurrently via `ThreadPoolExecutor(max_workers=2)`:

```
Time ────▶
GROBID    ████████░░░░░░░  (timeout: 30s, cancelled if timeout)
Docling   ██████████░░░░░  (timeout: 30s, cancelled if timeout)
```

- Results are independent — failure of one does not block the other
- `executor.shutdown(wait=False, cancel_futures=True)` — avoids minutes of latency waiting for timed-out threads
- Digital-native PDFs skip Docling entirely (`_should_skip_docling_for_digital_pdf`: checks for 250+ chars on first 2 pages)

### Pipeline Hierarchy

```
run_pipeline ──▶ semaphore.acquire()
  └─ _run_pipeline_internal()
      ├─ Extraction (ParserFactory / Converter)
      ├─ Parallel GROBID + Docling (PDF only)
      ├─ Equation Standardization
      ├─ Structure Detection
      ├─ Semantic Parsing (optional, fast_mode)
      ├─ Classification
      ├─ Content Analysis
      ├─ Caption Matching
      ├─ Figure Analysis (optional, fast_mode)
      ├─ Reference Parsing & Normalization
      ├─ CrossRef Validation (optional, fast_mode)
      ├─ AI Reasoning (RAG + reasoner, optional)
      ├─ Validation
      ├─ Formatting
      ├─ Export
      └─ Persistence
```

### Background Task Timeout (`backend/app/utils/background_tasks.py`)

- `@with_timeout(timeout_seconds=300)` decorator for general background tasks
- `run_pipeline_with_timeout()` wraps pipeline in `asyncio.wait_for(..., timeout=900.0)`
- Supports both sync and async functions via `asyncio.to_thread` and `loop.run_in_executor`
- Failed jobs are marked in DB via `DocumentService.mark_document_failed`

---

## 5. Task Queue

### Celery Configuration (`backend/app/tasks/celery_tasks.py`)

```python
celery_app = Celery(
    "manuscript_tasks",
    broker=settings.CELERY_BROKER_URL,       # redis://localhost:6379/0
    backend=settings.CELERY_RESULT_BACKEND,  # redis://localhost:6379/0
)
```

### Queue Architecture

| Queue | Task Prefix | Routing | Purpose |
| --- | --- | --- | --- |
| `interactive` | `interactive.*` | User-facing | Document processing, generation, synthesis, agent pipeline, edit flow |
| `batch` | `batch.*` | Scheduled/Cron | Upload cleanup (daily 03:00 UTC), LLMClassifier benchmarking |

### Task Settings

```python
task_acks_late = True          # Re-deliver if worker crashes mid-task
task_reject_on_worker_lost = True  # Reject unacked tasks on worker loss
task_track_started = True      # Visible "started" state in Flower/CLI
task_soft_time_limit = 600     # 10 min soft limit (throws SoftTimeLimitExceeded)
task_time_limit = 900          # 15 min hard limit (worker kills task)
```

### Interactive Tasks (all share the same retry config)

| Task | Description | Max Retries | Backoff |
| --- | --- | --- | --- |
| `process_document_task` | Document pipeline via PipelineOrchestrator | 3 | 1s × 2^n, max 300s, jitter |
| `process_generation_task` | Generate-from-scratch documents | 3 | Same |
| `process_synthesis_task` | Multi-document synthesis | 3 | Same |
| `process_agent_pipeline_task` | Agent-based document generation | 3 | Same |
| `process_agent_resume_task` | Resume after outline approval | 3 | Same |
| `process_agent_rewrite_task` | Section rewrite in agent doc | 3 | Same |
| `process_edit_document_task` | Reformat edited documents | 3 | Same |

### Batch Tasks

| Task | Schedule | Description |
| --- | --- | --- |
| `cleanup_uploads_task` | Daily 03:00 UTC | Delete files > `RETENTION_DAYS` (default 30) |
| `classification_benchmark_task` | On-demand | Run F1 benchmark over test fixtures |

### Worker Configuration (`render.yaml`)

```yaml
startCommand: celery -A app.tasks.celery_tasks worker \
  -Q interactive,batch \
  -c ${WORKER_CONCURRENCY:-2} \
  --loglevel=info \
  --prefetch-multiplier=1
```

| Parameter | Value | Rationale |
| --- | --- | --- |
| Queues | `interactive,batch` | Single worker listens to both |
| Concurrency | 2 (default, env `WORKER_CONCURRENCY`) | One worker instance handles 2 concurrent tasks |
| Prefetch multiplier | 1 | Fair scheduling — worker only prefetches 1 task at a time |
| acks_late | True | At-least-once delivery semantics |
| Beat schedule | Cleanup at 03:00 UTC | Off-peak maintenance window |

### Dependencies (from `requirements.txt`)

| Package | Version |
| --- | --- |
| `celery` | 5.6.2 |
| `redis` | 7.2.0 |
| `kombu` | 5.6.2 |
| `flower` | 2.0.1 |

---

## 6. Rate Limiting

### Architecture

Two layered rate limiters:

1. **`RateLimitMiddleware`** — Sliding-window per-IP for all endpoints
2. **`TierRateLimitMiddleware`** — Daily tier-based limits for uploads and generation

### RateLimitMiddleware (`backend/app/middleware/rate_limit.py`)

```
┌─────────────┐     ┌──────────┐     ┌─────────────┐
│  In-Memory   │────▶│  Redis    │────▶│  Max(count) │
│  (always)    │     │ (optional)│     │  per window │
└─────────────┘     └──────────┘     └─────────────┘
```

| Parameter | Default | Configuration |
| --- | --- | --- |
| Window | 60 s (fixed) | `WINDOW_SECONDS` |
| Requests per minute (general) | 60 | `RateLimitMiddleware(requests_per_minute=60)` |
| Uploads per minute | 10 | `UPLOADS_PER_MINUTE` env var |
| Redis key (general) | `ratelimit:general:{ip}:{minute_bucket}` | SHA-256 token fingerprint for auth'd users |
| Redis key (upload) | `ratelimit:upload:{ip}:{token_fp}:{minute_bucket}` | Token-aware upload counting |

**Behavior:**

- In-memory store is **always** updated (source of truth for tests)
- Redis is tried as cross-check for multi-worker accuracy
- Final count = `max(in_memory_count, redis_count)`
- Health check endpoint (`/health`) is never rate-limited
- Returns `429 Too Many Requests` with `retry_after` in body

### TierRateLimitMiddleware (`backend/app/middleware/tier_rate_limit.py`)

| User Type | Limit | Scope | Storage |
| --- | --- | --- | --- |
| Guest (unauthenticated) | 5/day | POST `/api/v1/documents/upload` and `/api/v1/generator/sessions` | Redis + in-memory fallback |
| Free-tier (authenticated) | 60/min | All POST endpoints | Redis 60s TTL |
| Pro-tier (authenticated) | 300/min | All POST endpoints | Redis 60s TTL |
| Admin (role_hierarchy >= 3) | Unlimited | — | — |

**Key structure:** `tierlimit:guest:{ip}:{YYYYMMDD}` or `ratelimit:user:{user_id}`

### Multi-Worker Consistency

- Each worker holds its own in-memory counter
- Redis provides the distributed source of truth
- Redis failure degrades to in-memory-only (less accurate under high concurrency, but never blocks legitimate traffic)
- Warning logged once per limiter per worker lifetime on Redis failure

---

## 7. LLM Performance

### Provider Architecture

```
generate_with_fallback()
  ├── Tier 1: NVIDIA NIM          (15s timeout, circuit breaker)
  ├── Tier 2: Groq                (15s timeout, circuit breaker)
  ├── Tier 3: OpenRouter          (15s timeout, circuit breaker)
  └── Tier 4: Ollama/DeepSeek     (15s timeout, circuit breaker)
       └── raises LLMUnavailableError if all tiers fail
```

### Timeout Configuration

| Setting | Default | Clamp |
| --- | --- | --- |
| `LLM_PROVIDER_TIMEOUT_SECONDS` | 15 | `max(3, min(value, 60))` |
| Per-call override | Via `timeout` param | Passed directly to LiteLLM |

### Circuit Breaker (`pybreaker`)

| Parameter | Default | Config Key |
| --- | --- | --- |
| Failure threshold | 3 | `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` |
| Reset timeout | 60 s | `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` |
| Enabled | True | `EXTERNAL_CIRCUIT_BREAKER_ENABLED` |

- Per-provider breakers stored in `_PROVIDER_BREAKERS` dict
- Open circuit raises: `"{provider} circuit breaker open"`
- Half-open state allows probe requests after `reset_timeout`

### Streaming Performance

- Cache is bypassed when `stream=True` (no response to cache)
- First-token latency (TTFT) target: < 500 ms
- Fallback mode (`LITELLM_AVAILABLE=False`) uses direct OpenAI-compatible clients

### Latency SLAs (mocked, unit tests)

| Operation | Target | Test |
| --- | --- | --- |
| `generate()` with cache hit | < 50 ms | `test_cached_llm_result_returns_in_under_50ms` |
| `generate_with_fallback()` | < 5 s | `test_generate_with_fallback_cache_populated` |
| `generate_with_model()` | < 3 s | `test_generate_with_model_returns_in_under_3s` |
| Streaming TTFT | < 500 ms | `test_streaming_first_token_latency` |
| `resolve_user_api_key()` env fallback | < 50 µs | `test_resolve_key_env_fallback` |
| `sanitize_for_llm()` short text | < 50 µs | `test_sanitize_for_llm_short_text` |
| `sanitize_for_llm()` large text (50K words) | < 100 ms | `test_sanitize_for_llm_large_text` |
| `_cache_key()` hash generation | < 50 µs | `test_cache_key_hash` |

### User API Key Resolution

- Priority: user stored key → env var → `None`
- `resolve_user_api_key()` falls back to env vars in < 50 µs
- Encrypted keys decrypted via `EncryptionService` (Fernet, < 500 µs per op)

### Metrics Recording

Each LLM call records (via `MetricsManager`):

- `record_llm_cache_hit(provider, model)`
- `record_llm_cache_miss(provider, model)`
- `record_llm_request(provider, model, success)`
- `record_llm_duration(provider, model, duration)`
- `record_llm_ttft(provider, model, duration)`
- `record_llm_failure(provider)`

---

## 8. Frontend Performance

### Framework

- **Next.js 16 (App Router) + React 19** — server components, streaming SSR
- Turbopack dev server: `next dev --turbopack`
- Build output optimized via `next build`

### Built-in Optimizations

| Technique | Implementation |
| --- | --- |
| Incremental Static Regeneration (ISR) | Automatic for static routes (templates, docs) |
| Route Segment Caching | App Router data cache for fetch() calls |
| Image Optimization | `next/image` with remote pattern allowlists |
| Font Optimization | `next/font` with `display=swap` and subsetting |
| Script Loading | `next/script` with `strategy` for third-party |
| Bundle Analysis | `@next/bundle-analyzer` for CI checks |
| Code Splitting | Automatic per-route and via `next/dynamic` |
| Tree Shaking | Webpack/Rust bundler eliminates dead code |
| Streaming SSR | `loading.tsx` and `<Suspense>` boundaries |

### CDN & Asset Delivery

- All static assets use `NEXT_PUBLIC_ASSET_PREFIX` (CDN prefix)
- Cache headers set via Next.js `headers` config
- ISR pages revalidated on demand via `revalidatePath()`

### Performance Budgets (CI Gates)

| Metric | Budget |
| --- | --- |
| Lighthouse Performance | ≥ 90 |
| Lighthouse Accessibility | ≥ 90 |
| Total bundle size (gzip) | < 300 KB |
| First Contentful Paint (FCP) | < 1.5 s |
| Largest Contentful Paint (LCP) | < 2.5 s |
| Cumulative Layout Shift (CLS) | < 0.1 |

### E2E Performance Checks

- Playwright e2e tests (`npm run test:e2e`) include timing assertions
- Core Web Vitals tracked via `chrome-webvitals` Lighthouse CI integration

---

## 9. Load Testing

### Locust Setup (`backend/tests/load/locustfile.py`)

Four user classes simulating real-world usage:

| User Class | Concurrent Users | Task | SLO |
| --- | --- | --- | --- |
| `UploadUser` | 100 | Upload 1-page DOCX | p99 ACK < 400 ms |
| `StatusPollUser` | 100 | Poll `/api/v1/documents/{id}/status` | p99 < 100 ms |
| `TemplatesUser` | 200 | GET `/api/v1/templates` | p99 < 80 ms |
| `PreviewWebSocketUser` | 50 | WebSocket preview roundtrip | p99 RTT < 200 ms |

### SLO Gates

Configured via environment variables (enforced on test exit):

```python
TARGET_P95_MS = float(os.getenv("LOCUST_TARGET_P95_MS", "500"))  # 500ms
TARGET_RPS    = float(os.getenv("LOCUST_TARGET_RPS", "100"))     # 100 req/s
MAX_FAIL_RATIO = float(os.getenv("LOCUST_MAX_FAIL_RATIO", "0.0")) # 0%
```

Exit code is 1 (failure) if any SLO is violated.

### Performance Benchmark Tests

**`test_performance_baseline.py`** — Real code paths with warmup + percentiles:

| Test Class | Operations | Iterations | Key Thresholds |
| --- | --- | --- | --- |
| `TestDocumentServiceReal` | UUID validation, HMAC sign/verify, signed URL gen/verify | 100 | median < 150 µs |
| `TestEncryptionPerformance` | Fernet encrypt/decrypt, large payload (100KB) | 100 | median < 500 µs, p95 < 1 ms |
| `TestCSRFPerformance` | Token generate/validate, with/without user_id | 100 | median < 300 µs |
| `TestJWKSPerformance` | Cached JWKS key fetch | 100 | median < 10 µs |
| `TestLLMServicePerformance` | Key resolution, injection sanitization (small/large) | 100 | median < 50 µs / < 100 ms |
| `TestPaginationPerformance` | Cursor encode/decode, round-trip, invalid input | 100 | median < 10 µs |
| `TestHMACPerformance` | Sign, verify, large payload (100KB), webhook equivalent | 100 | median < 200 µs |
| `TestConcurrentPerformance` | 100 parallel encrypt+decrypt, CSRF, HMAC, cursor encode | 100 | < 2 s per batch |
| `TestThroughput` | Ops/sec for encryption, HMAC, sanitize | 1 s sustained | > 500 / > 5K / > 400 ops/sec |
| `TestSerializationPerformance` | JSON sanitization: large dict, dates, enums, tuples | 100 | median < 100 ms |
| `TestSchemaValidationPerformance` | Pydantic 1000 items, single, nested | 100 | median < 200 ms |
| `TestUtilityPerformance` | `_infer_provider`, `_normalize_model_name`, etc. | 100 | median < 50 µs |

**`test_performance_regression.py`** — Regression gates:

| Test | Target | Description |
| --- | --- | --- |
| `test_document_list_query_performance` | < 500 ms | Document listing with mocked DB |
| `test_single_document_fetch_performance` | < 200 ms | Single doc fetch |
| `test_document_search_performance` | < 1 s | Full-text search |
| `test_pagination_no_n_plus_one` | ≤ 2 queries | N+1 detection |
| `test_basic_document_parsing_performance` | < 2 s | DOCX parsing |
| `test_structure_detection_performance` | < 1 s | Structure detection |
| `test_cached_llm_result_returns_in_under_50ms` | < 50 ms | LLM cache hit |
| `test_streaming_first_token_latency` | < 500 ms | Streaming TTFT |
| `test_pipeline_semaphore_limits_concurrent` | No deadlock | Semaphore isolation |
| `test_concurrent_requests_no_state_corruption` | < 5 s | State isolation |

### Concurrent Processing Tests (`test_concurrent_processing.py`)

| Test | Concurrency | Assertion |
| --- | --- | --- |
| `test_ten_concurrent_processes_no_deadlock` | 10 jobs, 4 workers | All complete within 30s |
| `test_pipeline_semaphore_limits_concurrent` | 20 jobs | Tracks max active |
| `test_thread_pool_executor_cleanup` | 50 threads | No leaked futures |
| `test_concurrent_sse_subscriptions_no_conflict` | 10 subscriptions | No overlap conflicts |
| `test_semaphore_timeout_rejects_overload` | 10 concurrent | Some reject after timeout |

---

## 10. Memory Management

### LOW_MEMORY_MODE

Environment variable: `LOW_MEMORY_MODE=false` (default)

When `true`:

- Forces `DEFAULT_FAST_MODE=true` (skips semantic parsing, crossref enrichment, AI reasoning, figure analysis)
- Used in render.yaml's free-tier deployments

### Lazy Model Loading

| Component | Loading Strategy | Trigger |
| --- | --- | --- |
| `RedisCache._client` | Created on first `_ensure_client()` call | Any cache operation |
| `FigureAnalyzer` | `_get_figure_analyzer()` lazy singleton | Figure analysis stage |
| `RagEngine` | `resolve_optional_callable()` | AI reasoning stage (optional) |
| `ReasoningEngine` | `resolve_optional_callable()` | AI reasoning stage (optional) |
| `SemanticParser` | Imported inside `_run_semantic_parsing` | Semantic parsing stage (optional) |
| `LLMPDFParser` | Imported inside exception handler | OCR fallback (rare) |
| `LiteLLM` | Tried at module load, disabled on Python 3.14+ | LLM service startup |
| `PyMuPDF` | Imported inside `_should_skip_docling_for_digital_pdf` | PDF processing |
| GROBID/Docling clients | Created in `PipelineOrchestrator.__init__` | Pipeline initialization |

### PRELOAD_AI_MODELS

- Default: `false` in production (render.yaml)
- When `false`: AI models (LLMClassifier, sentence-transformers) are loaded on first use, not at startup
- Reduces cold-start memory by ~2 GB

### File Cleanup

| Mechanism | Schedule | Effect |
| --- | --- | --- |
| Celery `cleanup_uploads_task` | Daily 03:00 UTC | Deletes uploads > `RETENTION_DAYS` (default 30) |
| `_persist_partial_result` | On pipeline failure | Saves partial state before cleanup |
| `temp_dir` creation | Per `PipelineOrchestrator` init | `os.makedirs(self.temp_dir, exist_ok=True)` |
| Output directory | Per job | `output/{job_id}/` cleaned by retention policy |

### Pipeline Memory Caps

- `_MAX_CONCURRENT_JOBS = 5` — prevents more than 5 simultaneous document processing jobs
- Each pipeline runs in its own thread via `ThreadPoolExecutor`
- `ThreadPoolExecutor.shutdown(wait=False)` on timed-out stages prevents thread accumulation
- GROBID/Docling parallel pass uses `max_workers=2` (never more)

---

## 11. Scaling Strategy

### Horizontal Scaling

| Component | Scaling Unit | Max Instances | Mechanism |
| --- | --- | --- | --- |
| Web (FastAPI) | Uvicorn worker | Configurable via `WEB_CONCURRENCY` (default 1) | Render web service auto-scaling |
| Celery worker | Worker process | Configurable via `WORKER_CONCURRENCY` (default 2) | Render worker service auto-scaling |
| Redis | Managed instance | Single | Render Redis (free plan, `allkeys-lru` eviction) |
| Database | Supabase | Auto-scale | Supabase Pro/Team plan |

### Auto-Scaling Triggers

| Trigger | Action | Metric |
| --- | --- | --- |
| Queue depth > 10 | Add Celery worker | Redis list length `celery` |
| CPU > 80% | Add web instance | Render metrics |
| Memory > 75% | Add web instance | Render metrics |
| Response latency p95 > 2s | Add web instance | Prometheus metrics |

### Queue Depth Monitoring

- Prometheus metrics track Celery queue depth via Flower / Redis
- `celery -A app.tasks.celery_tasks events --camera=camera.Camera` for event monitoring
- Alert when `interactive` queue exceeds 50 pending tasks

### Stateless Design

- All session state stored in Redis or Supabase (not in-memory)
- Pipeline state persisted to `processing_status` and `documents` tables
- SSE events emitted via Redis PubSub (`emit_event` in `routers/v1/stream.py`)
- Rate limiting state shared via Redis counters

### Deployment Topology (`render.yaml`)

```
Internet ──▶ Load Balancer
                │
        ┌───────┴───────┐
        │               │
   Web Service    Celery Worker
   (uvicorn)      (2 concurrency)
        │               │
        └───────┬───────┘
                │
           Redis Server
                │
           Supabase
```

### vLLM Adoption Path

When request volume exceeds thresholds:

- `VLLM_REQUESTS_PER_HOUR_THRESHOLD=2000`
- `VLLM_DAILY_TOKENS_THRESHOLD=5000000`
- Target model: `meta-llama/Meta-Llama-3.1-8B-Instruct`
- Target GPU: `L4 24GB`

---

## 12. Monitoring & Observability

### Prometheus Metrics (`backend/app/middleware/prometheus_metrics.py`)

| Metric | Type | Labels |
| --- | --- | --- |
| `pipeline_stage_duration_seconds` | Histogram | `stage` |
| `llm_request_total` | Counter | `provider`, `model`, `success` |
| `llm_duration_seconds` | Histogram | `provider`, `model` |
| `llm_ttft_seconds` | Histogram | `provider`, `model` |
| `llm_cache_hit_total` | Counter | `provider`, `model` |
| `llm_cache_miss_total` | Counter | `provider`, `model` |
| `llm_failure_total` | Counter | `provider` |
| `http_request_duration_seconds` | Histogram (via `prometheus-fastapi-instrumentator`) | `method`, `path`, `status` |

### Pipeline Stage Timing

`_record_stage_transition()` captures start→end duration per stage:

- Start: `PROCESSING` status
- End: `COMPLETED` or `FAILED` status
- Durations recorded via `MetricsManager.record_pipeline_stage_duration()`

### Health Endpoints

| Endpoint | TTL Cache | Purpose |
| --- | --- | --- |
| `/api/v1/health/live` | 15 s | Liveness probe (Render health check path) |
| `/api/v1/health/ready` | 15 s | Readiness — checks DB, Redis, GROBID, Docling |

### Logging

- Structured logging via `structlog` when `ENABLE_STRUCTURED_LOGGING=true`
- Pipeline quality summary logged at INFO: `PIPELINE SCORE | job=... | quality=...`
- Celery worker logs via `--loglevel=info`

---

## 13. SLO / SLA Reference

### Latency SLOs

| Operation | p50 | p95 | p99 | Max |
| --- | --- | --- | --- | --- |
| API general request | < 500 ms | < 2 s | < 5 s | 30 s |
| Document upload ACK | < 200 ms | < 300 ms | < 400 ms | 1 s |
| Template listing | < 30 ms | < 50 ms | < 80 ms | 200 ms |
| Status poll | < 50 ms | < 80 ms | < 100 ms | 200 ms |
| WebSocket preview RTT | < 100 ms | < 150 ms | < 200 ms | 500 ms |
| LLM cache hit | < 10 ms | < 30 ms | < 50 ms | 100 ms |
| LLM generate (API call) | < 3 s | < 5 s | < 10 s | 15 s |
| Document parsing (DOCX) | < 500 ms | < 1 s | < 2 s | 5 s |
| Structure detection | < 200 ms | < 500 ms | < 1 s | 2 s |
| Pipeline (fast mode) | 30 s | 60 s | 120 s | 300 s |
| Pipeline (full AI mode) | 120 s | 300 s | 600 s | 900 s |

### Throughput SLOs

| Operation | Target | Measurement |
| --- | --- | --- |
| API requests | 100 req/s | Locust `TARGET_RPS=100` |
| Parallel pipeline jobs | 5 | `_MAX_CONCURRENT_JOBS` |
| Uploads per minute | 10 | `UPLOADS_PER_MINUTE` |
| Concurrent users | 200 | Locust scenarios summed |
| Encrypt+decrypt ops | > 500 ops/s | `test_encryption_throughput` |
| HMAC sign ops | > 5,000 ops/s | `test_hmac_throughput` |
| LLM sanitize ops | > 400 ops/s | `test_sanitize_llm_throughput` |

### Availability SLOs

| Component | Target | Degraded Behavior |
| --- | --- | --- |
| Web API | 99.9% | — |
| Redis | 99.5% | In-memory fallback for rate limiting + caching |
| Database | 99.9% | Degraded mode (503 on DB endpoints) |
| LLM providers | 99.0% | 4-tier fallback; rule-based heuristics as last resort |
| Celery worker | 99.5% | `acks_late=True` ensures no task loss |
| GROBID | 95.0% | PyMuPDF fallback metadata extraction |
| Docling | 90.0% | Skipped for digital-native PDFs |

### Recovery Time Objectives (RTO)

| Failure Scenario | RTO | Verification |
| --- | --- | --- |
| Single web worker crash | < 5 s | Render auto-restart |
| Celery worker crash | < 10 s | Render auto-restart + unacked tasks re-delivered |
| Redis outage | < 1 s | Immediate in-memory degradation |
| Database connection loss | < 30 s | Connection pool retry with `pool_pre_ping` |
| LLM provider outage | < 15 s | Circuit breaker opens + tier fallback |
| GROBID service crash | < 1 s | Immediate fallback to Docling → PyMuPDF |
| Full cold start | < 30 s | Lazy model loading, `PRELOAD_AI_MODELS=false` |

---

## 14. Caching Layers

```mermaid
graph LR
    subgraph Client
        B["Browser Cache<br/>ETag / Cache-Control"]
    end
    subgraph Edge
        CDN["CDN Cache<br/>Vercel Edge / Cloudflare<br/>TTL: 5-60 min"]
    end
    subgraph Application
        IPC["In-Process Cache<br/>dict / LRU<br/>TTL: 1-5 s"]
    end
    subgraph Shared
        R["Redis Cache<br/>flag: / llm_cache: / grobid:<br/>TTL: 5 min - 24 h"]
    end
    subgraph Persistent
        DB["("Supabase / PostgreSQL<br/>Source of Truth")"]
    end

    B -->|Cache Miss| CDN
    CDN -->|Cache Miss / Bypass| IPC
    IPC -->|Cache Miss| R
    R -->|Cache Miss| DB
    DB -->|Populate| R
    R -->|Populate| IPC
    IPC -->|Populate HTTP Cache| CDN
    CDN -->|Set Cache-Control| B
```

## 15. API Endpoint Latency Benchmarks

Measured via `test_performance_baseline.py` and Locust SLO gates under load (50 concurrent users, 100 req/s target):

| Endpoint | p50 | p95 | p99 | Test Source |
| --- | --- | --- | --- | --- |
| `GET /api/v1/health/live` | < 15 ms | < 30 ms | < 50 ms | Locust `HealthCheckUser` |
| `GET /api/v1/health/ready` | < 50 ms | < 100 ms | < 200 ms | Locust `HealthCheckUser` |
| `GET /api/v1/templates` | < 30 ms | < 50 ms | < 80 ms | `test_templates_performance` |
| `GET /api/v1/documents` | < 100 ms | < 300 ms | < 500 ms | `test_document_list_query_performance` |
| `GET /api/v1/documents/{id}` | < 50 ms | < 100 ms | < 200 ms | `test_single_document_fetch_performance` |
| `POST /api/v1/documents/upload` (ACK) | < 200 ms | < 300 ms | < 400 ms | `Locust UploadUser` |
| `GET /api/v1/documents/{id}/status` | < 50 ms | < 80 ms | < 100 ms | `Locust StatusPollUser` |
| `POST /api/v1/generator/sessions` | < 200 ms | < 500 ms | < 1 s | Performance regression suite |
| `WebSocket /api/v1/stream/preview` (RTT) | < 100 ms | < 150 ms | < 200 ms | `Locust PreviewWebSocketUser` |
| `GET /metrics` | < 10 ms | < 20 ms | < 50 ms | Prometheus scrape |

Benchmarks run against a warmed-up service with Redis enabled and DB connection pool pre-filled.

## 16. Testing

### Load Testing with Locust

The Locust suite (`backend/tests/load/locustfile.py`) simulates production traffic patterns:

```bash
# Start Locust web UI
locust -f backend/tests/load/locustfile.py --host https://api.scholarform.ai

# Headless run with SLO gates
LOCUST_TARGET_P95_MS=500 LOCUST_TARGET_RPS=100 \
  locust -f backend/tests/load/locustfile.py \
  --host https://api.scholarform.ai \
  --headless -u 200 -r 10 --run-time 5m \
  --html report.html --csv metrics
```

SLO gates exit with code 1 on violation:

| Gate | Env Var | Default |
| --- | --- | --- |
| P95 latency | `LOCUST_TARGET_P95_MS` | 500 ms |
| Requests/sec | `LOCUST_TARGET_RPS` | 100 |
| Max fail ratio | `LOCUST_MAX_FAIL_RATIO` | 0.0 |

### Memory Profiling

```bash
# Track memory usage per pipeline stage
python -m memory_profiler backend/scripts/profile_pipeline.py

# Heap snapshot comparison
python -c "
import tracemalloc
tracemalloc.start()
# Run pipeline operation
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"
```

### Performance Regression Gates

Test suite `test_performance_regression.py` enforces hard latency budgets in CI:

| Test | Budget | Tool |
| --- | --- | --- |
| `test_document_list_query_performance` | < 500 ms | pytest-benchmark |
| `test_basic_document_parsing_performance` | < 2 s | pytest-benchmark |
| `test_structure_detection_performance` | < 1 s | pytest-benchmark |
| `test_cached_llm_result_returns_in_under_50ms` | < 50 ms | pytest-benchmark |
| `test_streaming_first_token_latency` | < 500 ms | pytest-benchmark |
| `test_generate_with_model_returns_in_under_3s` | < 3 s | pytest-benchmark |
| `test_pipeline_semaphore_limits_concurrent` | No deadlock | Thread safety check |

Run locally:

```bash
cd backend
pytest tests/test_performance_regression.py -v --benchmark-enable --benchmark-only
```

## Appendix: Configuration Reference

### Environment Variables (Performance-Related)

```ini
# Redis
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379
LLM_CACHE_TTL_SECONDS=3600

# Pipeline
PIPELINE_GROBID_TIMEOUT_SECONDS=30
PIPELINE_DOCLING_TIMEOUT_SECONDS=30
PIPELINE_REASONING_TIMEOUT_SECONDS=60
PIPELINE_SEMANTIC_TIMEOUT_SECONDS=30
PIPELINE_ACQUIRE_TIMEOUT_SECONDS=30.0
PIPELINE_DOCLING_SKIP_DIGITAL_PDF=false
PIPELINE_DOCLING_FORCE=false

# LLM
LLM_PROVIDER_TIMEOUT_SECONDS=15
EXTERNAL_CIRCUIT_BREAKER_ENABLED=true
EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS=60

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Rate Limiting
GLOBAL_RATE_LIMIT_PER_MINUTE=120
UPLOADS_PER_MINUTE=10

# Memory
LOW_MEMORY_MODE=false
PRELOAD_AI_MODELS=false
DEFAULT_FAST_MODE=false

# Cross-Reference
CROSSREF_MAX_WORKERS=4

# File Cleanup
ENABLE_FILE_CLEANUP=true
RETENTION_DAYS=30

# vLLM Adoption Triggers
VLLM_REQUESTS_PER_HOUR_THRESHOLD=2000
VLLM_DAILY_TOKENS_THRESHOLD=5000000

# Celery Worker (Render overrides)
WEB_CONCURRENCY=1
WORKER_CONCURRENCY=2
```
