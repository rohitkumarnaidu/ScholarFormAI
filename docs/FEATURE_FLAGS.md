---
title: ScholarForm AI — Feature Flags & Enhancement Manager
description: Feature flag system for gradual rollouts, toggles, and enhancement capability management
sidebar_position: 55
version: "1.0"
status: &#x2705; Complete
owner: Engineering
review_cadence: quarterly
last_updated: July 2026
---

# Feature Flags & Enhancement Manager

- [Overview](#overview)
- [Feature Flag Service](#feature-flag-service)
    - [Resolution Order](#resolution-order)
    - [Singleton Access](#singleton-access)
- [Feature Flag Middleware](#feature-flag-middleware)
    - [Response Header Injection](#response-header-injection)
- [Enhancement Manager](#enhancement-manager)
    - [EnhancementProfile](#enhancementprofile)
    - [Capability Discovery](#capability-discovery)
    - [Fallback Dispatching](#fallback-dispatching)
- [Available Flags](#available-flags)
    - [Pipeline Flags](#pipeline-flags)
    - [Security Flags](#security-flags)
    - [Cache Flags](#cache-flags)
    - [Deployment Flags](#deployment-flags)
    - [Enhancement Flags](#enhancement-flags)
- [Configuration Reference](#configuration-reference)
    - [Pipeline Settings](#pipeline-settings)
    - [Security Settings](#security-settings)
    - [Cache Settings](#cache-settings)
    - [Deployment Settings](#deployment-settings)
- [Usage](#usage)
    - [Checking Flags in Code](#checking-flags-in-code)
    - [Per-Request Override](#per-request-override)
    - [Enhancement Manager Dispatch](#enhancement-manager-dispatch)
- [Frontend Integration](#frontend-integration)
- [See Also](#see-also)

## Overview

ScholarForm AI uses a two-layer feature flag architecture:

1. **Feature Flag Service** (`app/services/feature_flags.py`) — a database-backed, Redis-cached service for dynamic feature toggles (e.g., `new_upload_flow`, `ai_suggestions`). Ideal for gradual rollouts and A/B testing.
2. **Enhancement Manager** (`app/services/enhancement_manager.py`) — a startup-time capability registry that probes the runtime environment for installed backends (OCR engines, keyword extractors, Celery) and builds an immutable `EnhancementProfile`. Flags like `GROBID_ENABLED`, `LOW_MEMORY_MODE`, and `DEFAULT_FAST_MODE` are read from `pydantic-settings` at import time.

The **Feature Flag Middleware** (`app/middleware/feature_flags.py`) bridges the two, resolving all flags per-request and injecting them into `request.state.feature_flags`. In debug mode, the full flags dict is also returned as the `X-Feature-Flags` response header for client-side consumption.

## Feature Flag Service

`app/services/feature_flags.py` — `FeatureFlagService` manages an in-memory cache of default flags and supports optional persistence via a database and Redis caching layer.

### Resolution Order

`get_flag(name, default, user_id)` uses a four-tier resolution chain:

1. **Redis cache** — fastest lookup; cached values have a 5-minute TTL (`flag:{name}` key).
2. **In-memory cache** — loaded from defaults at construction and updated on DB/cache hits.
3. **Database** — authoritative source; `_load_from_db()` and `_load_all_from_db()` are stub methods overridable for Supabase or Postgres.
4. **Default value** — falls back to the provided `default` argument, then to `_DEFAULT_FLAGS`.

### Singleton Access

```python
from app.services.feature_flags import get_feature_flag_service, get_feature_flag

service = get_feature_flag_service()          # singleton
flags = service.get_all_flags(user_id="usr_1")

enabled = get_feature_flag("ai_suggestions")   # convenience function
```

## Feature Flag Middleware

`app/middleware/feature_flags.py` — `FeatureFlagMiddleware` is a Starlette `BaseHTTPMiddleware` registered in the FastAPI application lifespan.

**Dispatch flow:**

1. Optionally extracts `user_id` from the `Authorization` header (JWT token).
2. Calls `get_feature_flag_service().get_all_flags(user_id)`.
3. Stores the resolved dict on `request.state.feature_flags`.
4. Calls the next middleware or route handler.
5. Injects the `X-Feature-Flags` response header when `app.debug` is `True`.

### Response Header Injection

When `DEBUG=true`, every response includes:

```
X-Feature-Flags: {"new_upload_flow":false,"ai_suggestions":true,"batch_processing":true,...}
```

This allows frontend clients and debugging proxies to inspect the active flags without additional API calls.

## Enhancement Manager

`app/services/enhancement_manager.py` — `EnhancementManager` is a capability registry and intelligent dispatcher that determines which backends are available at runtime and routes work to the best available path.

### EnhancementProfile

The immutable `EnhancementProfile` dataclass captures the full capability state:

| Field | Type | Description |
| ------- | ------ | ------------- |
| `enabled` | `bool` | Master enhancement toggle |
| `queue_enabled` | `bool` | Celery background queue enabled |
| `queue_provider` | `str` | Resolved provider (`"celery"`, `"local"`) |
| `queue_available` | `bool` | Both `celery` and `redis` modules importable |
| `ocr_enabled` | `bool` | OCR post-processing enabled |
| `ocr_backends` | `List[str]` | Available OCR backends (e.g., `["tesseract"]`) |
| `keyword_enabled` | `bool` | Keyword extraction enabled |
| `keyword_backends` | `List[str]` | Available keyword backends (e.g., `["keybert", "basic"]`) |

### Capability Discovery

`_build_profile()` probes the environment at each `refresh()` call:

- **OCR backends**: checks `pytesseract` + `pdf2image` for Tesseract, `paddleocr` for Paddle, `surya` for Surya. Falls back to `["builtin"]` if none are installed.
- **Keyword backends**: checks `keybert`, `yake`, and API key availability for `keyllm` (any of `NVIDIA_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`). Falls back to `["basic"]`.
- **Celery queue**: probes `celery` and `redis` modules. Requires both for queue-based dispatching.

### Fallback Dispatching

The Enhancement Manager provides four dispatch methods, each with a Celery-first / `BackgroundTasks`-fallback pattern:

- `dispatch_document_pipeline()` — upload → format pipeline
- `dispatch_generation_pipeline()` — AI generation pipeline
- `dispatch_edit_flow()` — edit/reformat flow
- `dispatch_synthesis_pipeline()` — multi-document synthesis

Each method checks `should_queue_job()` which compares `estimated_duration_seconds` against `ENHANCEMENT_QUEUE_MIN_SECONDS` (default 5.0). If the job is below the threshold — or Celery is unavailable — the task runs inline via `background_tasks.add_task()`.

### refresh() During Startup

`EnhancementManager.refresh()` is called during application startup to build the initial `EnhancementProfile`. The profile is lazily computed on first property access if `refresh()` was not called explicitly, but calling it at startup ensures the initial log line and avoids a first-request delay.

```python
# At startup:
enhancement_manager.refresh()
logger.info("Enhancement profile: %s", enhancement_manager.profile.to_dict())
```

## Available Flags

### Pipeline Flags

| Flag | Default | Setting Class | Description |
| ------ | --------- | -------------- | ------------- |
| `GROBID_ENABLED` | `True` | `PipelineSettings` | Enable GROBID PDF parsing service |
| `USE_DOCLING_FALLBACK` | `True` | `PipelineSettings` | Fall back to Docling when GROBID fails or is disabled |
| `PYMUPDF_FALLBACK` | `True` | `PipelineSettings` | Fall back to PyMuPDF when Docling also fails |
| `USE_LLM_CLASSIFICATION` | `False` | `PipelineSettings` | Enable LLM-based section classification (disabled by default; requires GPU) |
| `LLM_CLASSIFIER_AUTO_ENABLE_FROM_BENCHMARK` | `True` | `PipelineSettings` | Auto-enable LLMClassifier based on benchmark F1 score |
| `ENABLE_LLM_PDF_PARSER` | `False` | `PipelineSettings` | Enable LLMPDFParser LaTeX OCR parser |
| `ENABLE_NVIDIA_REASONER` | `False` | `PipelineSettings` | Enable NVIDIA NIM reasoning pipeline stage |
| `PRELOAD_AI_MODELS` | `True` | `PipelineSettings` | Preload AI models at startup (set `False` to reduce memory) |
| `LOW_MEMORY_MODE` | `False` | `PipelineSettings` | Reduce memory footprint: disable model preloading, reduce batch sizes |
| `DEFAULT_FAST_MODE` | `False` | `PipelineSettings` | Skip optional AI-heavy pipeline stages (classifier, RAG, advanced formatting) |
| `RAG_USE_TRANSFORMERS` | `True` | `PipelineSettings` | Use HuggingFace Transformers for RAG embeddings (vs. sentence-transformers) |

### Security Flags

| Flag | Default | Setting Class | Description |
|------|---------|--------------|-------------|
| `FORCE_HTTPS` | `False` | `SecuritySettings` | Redirect all HTTP to HTTPS; enables HSTS headers |

### Cache Flags

| Flag | Default | Setting Class | Description |
| ------ | --------- | -------------- | ------------- |
| `REDIS_ENABLED` | `False` | `CacheSettings` | Enable Redis for caching and Celery broker/backend |
| `VLLM_ADOPTION_ENABLED` | `True` | `DeploymentSettings` | Enable vLLM auto-scaling decision engine |

### Deployment Flags

| Flag | Default | Setting Class | Description |
| ------ | --------- | -------------- | ------------- |
| `ENABLE_FILE_CLEANUP` | `True` | `DeploymentSettings` | Enable periodic cleanup of uploaded and generated files |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | `True` | `DeploymentSettings` | Enable circuit breaker for external service calls |
| `DEBUG` | `False` | `DeploymentSettings` | Enable debug mode (also enables `X-Feature-Flags` header) |
| `ENABLE_STRUCTURED_LOGGING` | `False` | `DeploymentSettings` | Output JSON-structured logs for log aggregation |

### Enhancement Flags

| Flag | Default | Setting Class | Description |
| ------ | --------- | -------------- | ------------- |
| `ENHANCEMENTS_ENABLED` | `True` | `DeploymentSettings` | Master toggle for all enhancement capabilities |
| `ENHANCEMENT_QUEUE_ENABLED` | `False` | `DeploymentSettings` | Enable Celery background task queue |
| `ENHANCEMENT_QUEUE_PROVIDER` | `"auto"` | `DeploymentSettings` | Queue provider (`"auto"`, `"celery"`, `"local"`) |
| `ENHANCEMENT_OCR_ENABLED` | `True` | `DeploymentSettings` | Enable OCR post-processing |
| `ENHANCEMENT_OCR_BACKENDS` | `"tesseract,paddle,surya"` | `DeploymentSettings` | Comma-separated OCR backend preference order |
| `ENHANCEMENT_KEYWORD_ENABLED` | `True` | `DeploymentSettings` | Enable keyword extraction |
| `ENHANCEMENT_KEYWORD_BACKENDS` | `"keyllm,keybert,yake,basic"` | `DeploymentSettings` | Comma-separated keyword backend preference order |
| `ENHANCEMENT_QUEUE_MIN_SECONDS` | `5.0` | `DeploymentSettings` | Minimum estimated duration to trigger Celery queuing |

> **Note**: `DOCLING_ENABLED` is not a direct setting. Docling is controlled via `USE_DOCLING_FALLBACK` — when `True`, Docling serves as the second-tier PDF parser when GROBID is unavailable.

## Configuration Reference

All flags are set via environment variables or `.env` file. The canonical env-file template is generated by:

```bash
python scripts/generate_env_template.py
```

### Pipeline Settings

| Env Variable | Type | Default | Description |
| ------------- | ------ | --------- | ------------- |
| `GROBID_ENABLED` | `bool` | `True` | Enable GROBID PDF-to-XML service |
| `USE_DOCLING_FALLBACK` | `bool` | `True` | Enable Docling as fallback PDF parser |
| `PYMUPDF_FALLBACK` | `bool` | `True` | Enable PyMuPDF as third-tier fallback |
| `USE_LLM_CLASSIFICATION` | `bool` | `False` | Enable LLMClassifier ML classifier for section detection |
| `LLM_CLASSIFIER_AUTO_ENABLE_FROM_BENCHMARK` | `bool` | `True` | Auto-enable LLMClassifier when benchmark F1 > `LLM_CLASSIFIER_MIN_BENCHMARK_F1` |
| `PRELOAD_AI_MODELS` | `bool` | `True` | Preload models into GPU memory at startup |
| `LOW_MEMORY_MODE` | `bool` | `False` | Reduce memory usage; disables model preloading |
| `DEFAULT_FAST_MODE` | `bool` | `False` | Skip optional AI stages (LLMClassifier, RAG, advanced analysis) |
| `RAG_USE_TRANSFORMERS` | `bool` | `True` | Use HuggingFace transformers for RAG embeddings |
| `ENABLE_LLM_PDF_PARSER` | `bool` | `False` | Enable LLMPDFParser LaTeX-based PDF parser |
| `ENABLE_NVIDIA_REASONER` | `bool` | `False` | Enable NVIDIA NIM reasoning step |
| `PIPELINE_DOCLING_SKIP_DIGITAL_PDF` | `bool` | `False` | Skip Docling on born-digital PDFs |
| `PIPELINE_DOCLING_FORCE` | `bool` | `False` | Always use Docling even when GROBID succeeds |
| `GROBID_TIMEOUT` | `int` | `10` | GROBID request timeout (seconds) |
| `PIPELINE_GROBID_TIMEOUT_SECONDS` | `int` | `30` | Pipeline-level GROBID timeout |
| `PIPELINE_DOCLING_TIMEOUT_SECONDS` | `int` | `30` | Pipeline-level Docling timeout |
| `PIPELINE_REASONING_TIMEOUT_SECONDS` | `int` | `60` | Pipeline-level reasoning timeout |
| `PIPELINE_SEMANTIC_TIMEOUT_SECONDS` | `int` | `30` | Pipeline-level semantic analysis timeout |

### Security Settings

| Env Variable | Type | Default | Description |
|-------------|------|---------|-------------|
| `FORCE_HTTPS` | `bool` | `False` | Redirect HTTP to HTTPS; set `True` in production behind TLS-terminating proxy |

### Cache Settings

| Env Variable | Type | Default | Description |
| ------------- | ------ | --------- | ------------- |
| `REDIS_ENABLED` | `bool` | `False` | Enable Redis for caching and Celery broker |
| `REDIS_URL` | `str` | `"redis://localhost:6379"` | Redis connection URL |
| `REDIS_HOST` | `str` | `"localhost"` | Redis host (fallback when URL not used) |
| `REDIS_PORT` | `int` | `6379` | Redis port |
| `LLM_CACHE_TTL_SECONDS` | `int` | `3600` | LLM response cache TTL |

### Deployment Settings

| Env Variable | Type | Default | Description |
| ------------- | ------ | --------- | ------------- |
| `ENABLE_FILE_CLEANUP` | `bool` | `True` | Periodic file cleanup for uploaded/generated files |
| `DEBUG` | `bool` | `False` | Enable debug mode (also injects `X-Feature-Flags` header) |
| `ENABLE_STRUCTURED_LOGGING` | `bool` | `False` | JSON-structured log output |
| `GLOBAL_RATE_LIMIT_PER_MINUTE` | `int` | `120` | Global API rate limit |
| `MAX_FILE_SIZE` | `int` | `62914560` | Max upload file size (60 MB) |
| `ENHANCEMENTS_ENABLED` | `bool` | `True` | Master enhancement toggle |
| `ENHANCEMENT_QUEUE_ENABLED` | `bool` | `False` | Enable Celery queue |
| `ENHANCEMENT_QUEUE_PROVIDER` | `str` | `"auto"` | Queue provider selection |
| `ENHANCEMENT_OCR_ENABLED` | `bool` | `True` | Enable OCR post-processing |
| `ENHANCEMENT_OCR_BACKENDS` | `str` | `"tesseract,paddle,surya"` | OCR backend preference order |
| `ENHANCEMENT_KEYWORD_ENABLED` | `bool` | `True` | Enable keyword extraction |
| `ENHANCEMENT_KEYWORD_BACKENDS` | `str` | `"keyllm,keybert,yake,basic"` | Keyword backend preference order |
| `ENHANCEMENT_QUEUE_MIN_SECONDS` | `float` | `5.0` | Queue threshold in seconds |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | `bool` | `True` | Enable circuit breaker for external services |

## Usage

### Checking Flags in Code

**Feature flags** (dynamic, per-user):

```python
from app.services.feature_flags import get_feature_flag

if get_feature_flag("new_upload_flow", user_id=request.user.id):
    # Show new upload flow
    ...
```

**Pipeline settings** (static, startup-time):

```python
from app.config.settings import settings

if settings.GROBID_ENABLED:
    result = await grobid_client.parse_pdf(path)

if settings.DEFAULT_FAST_MODE:
    # Skip expensive AI stages
    pipeline.skip_optional_stages()
```

**Enhancement capabilities** (runtime-detected):

```python
from app.services.enhancement_manager import enhancement_manager

profile = enhancement_manager.profile
available_ocr = enhancement_manager.get_ocr_backends()
# e.g., ["tesseract", "paddle"]

if enhancement_manager.is_celery_queue_active():
    # Dispatch to Celery
    ...
```

### Per-Request Override

The Feature Flag Middleware stores flags in `request.state.feature_flags`. Route handlers and downstream services can read or override flags for the duration of a request:

```python
from fastapi import Request

async def my_handler(request: Request):
    flags = request.state.feature_flags

    # Override for this request only
    flags["batch_processing"] = False

    # Pass to service layer
    result = await process_document(flags=flags)
```

### Enhancement Manager Dispatch

```python
from app.services.enhancement_manager import enhancement_manager
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    job_id: str = Body(...),
    ...
):
    result = enhancement_manager.dispatch_document_pipeline(
        background_tasks=background_tasks,
        orchestrator=orchestrator,
        input_path=input_path,
        job_id=job_id,
        template_name=template_name,
        estimated_duration_seconds=15.0,  # > 5.0 → Celery (if available)
    )
    # result: {"mode": "celery", "task_id": "..."}
    #      or  {"mode": "background", "task_id": None}
```

## Frontend Integration

Flags propagate to the frontend through two mechanisms:

1. **Response header** (debug mode): When `DEBUG=true`, every API response includes the `X-Feature-Flags` header as a JSON object. The frontend can read this in interceptors:

```typescript
// Axios interceptor
api.interceptors.response.use((response) => {
  const flagsHeader = response.headers["x-feature-flags"];
  if (flagsHeader) {
    const flags = JSON.parse(flagsHeader);
    store.dispatch(setFeatureFlags(flags));
  }
  return response;
});
```

2. **Dedicated endpoint**: The feature flags service can expose a `/api/v1/flags` endpoint for the frontend to poll on initial load and after reconnection.

Flags control frontend behavior such as:

| Flag | Frontend Impact |
| ------ | ----------------- |
| `new_upload_flow` | Route to new vs. legacy upload wizard |
| `dark_mode_beta` | Enable dark mode toggle in settings |
| `ai_suggestions` | Show/hide AI-suggestion panel |
| `api_key_manager` | Enable/disable the API key management page |
| `export_latex` | Show/hide LaTeX export option |
| `export_jats` | Show/hide JATS XML export option |
| `collaborative_editing` | Enable collaborative editing UI |
| `advanced_analytics` | Show/hide analytics dashboard |
| `batch_processing` | Enable batch upload flow |

## Testing

### Feature Flag Middleware Tests

Test patterns in `tests/test_middleware_feature_flags.py`:

```python
async def test_feature_flag_middleware_injects_flags(client):
    response = await client.get("/api/v1/templates")
    assert response.status_code == 200
    assert hasattr(response.request.state, "feature_flags")

async def test_debug_mode_injects_header(client):
    client.app.debug = True
    response = await client.get("/api/v1/templates")
    assert "X-Feature-Flags" in response.headers
    flags = json.loads(response.headers["X-Feature-Flags"])
    assert "ai_suggestions" in flags
```

### Mocking EnhancementManager

```python
@pytest.fixture
def mock_enhancement_manager():
    with patch("app.services.enhancement_manager.EnhancementManager") as mock:
        mock_instance = mock.return_value
        mock_instance.profile.enabled = True
        mock_instance.profile.ocr_enabled = True
        mock_instance.is_celery_queue_active.return_value = False
        yield mock_instance
```

### Flag Resolution Tests

| Test Pattern | Description |
| --- | --- |
| `test_flag_default_fallback` | Verify default value is returned when no source has the flag |
| `test_flag_env_override` | Verify environment variable takes precedence over default |
| `test_flag_redis_cache` | Verify Redis cached value is preferred over DB value |
| `test_flag_db_source` | Verify DB value overrides in-memory default |
| `test_flag_per_user` | Verify user-specific flag resolution |

### Flag Resolution Chain

```mermaid
graph TD
    A[get_flag request] --> B{REDIS_ENABLED?}
    B -->|Yes| C[Redis cache<br/>flag:{name}<br/>TTL: 5min]
    B -->|No| D["In-memory cache<br/>_DEFAULT_FLAGS"]
    C -->|Hit| E[Return cached value]
    C -->|Miss| D
    D -->|Found| E
    D -->|Miss| F["Database<br/>_load_from_db"]
    F -->|Found| G[Update caches]
    F -->|Miss| H[Return default]
    G --> E
```

## Deployment

### Environment Configuration

Flags are configured per-environment through a layered approach:

| Layer | Local Dev | Staging | Production |
| --- | --- | --- | --- |
| `.env` file | `backend/.env` | `backend/.env.render` | Render Dashboard |
| Redis overrides | Optional local Redis | Shared staging Redis | Production Upstash Redis |
| Per-request | `request.state.feature_flags` | Same | Same |

### Render Env Vars (Production)

In the Render Dashboard → Environment, set flags as environment variables:

```env
AI_SUGGESTIONS_ENABLED=true
BATCH_PROCESSING_ENABLED=true
NEW_UPLOAD_FLOW=false
COLLABORATIVE_EDITING=false
```

### Per-Environment Overrides

```bash
# Local development
echo "NEW_UPLOAD_FLOW=true" >> backend/.env

# Verify flag after deploy
curl -s https://api.scholarform.ai/api/v1/flags | jq .
```

## API Coverage

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/v1/flags` | GET | Retrieve all effective flags (frontend polling) |
| `/api/v1/flags/{name}` | GET | Retrieve a single flag value |
| `/api/v1/flags` | POST | Create or update a flag (admin) |
| `/api/v1/flags/{name}` | DELETE | Remove a flag override (admin) |
| `/api/v1/health/ready` | GET | Readiness probe — checks required services |

The `X-Feature-Flags` response header (debug mode) provides a zero-latency alternative to polling the dedicated endpoint.

## See Also

- [Configuration Reference](CONFIGURATION_REFERENCE.md) — full settings catalog
- [Architecture Overview](architecture.md) — system architecture
- [AI Architecture](AI_ARCHITECTURE.md) — AI/ML pipeline details
- [Deployment Guide](Deployment.md) — environment variable setup
- [Frontend Architecture](FRONTEND_ARCHITECTURE.md) — frontend integration patterns
