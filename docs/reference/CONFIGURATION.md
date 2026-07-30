# ScholarForm AI — Configuration Reference Guide

ScholarForm AI uses Pydantic settings (`pydantic-settings`) in `backend/app/config/settings.py` to load and validate configuration parameters from environment variables (and local `.env` files).

Settings are organized into six logical sub-configuration classes contained within the unified `Settings` model.

---

## Unified Sub-Config Architecture

```python
class Settings:
    database: DatabaseSettings
    llm: LLMSettings
    pipeline: PipelineSettings
    security: SecuritySettings
    cache: CacheSettings
    deployment: DeploymentSettings
```

---

## Comprehensive Environment Variables Reference

### 1. Database Settings (`DatabaseSettings`)

| Environment Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `SUPABASE_URL` | `Optional[str]` | `None` | Supabase project URL (`https://<project-ref>.supabase.co`) |
| `SUPABASE_ANON_KEY` | `Optional[str]` | `None` | Supabase public anonymous API key |
| `SUPABASE_JWKS_URL` | `Optional[str]` | `None` | Supabase JSON Web Key Set URL for JWT verification |
| `SUPABASE_JWT_SECRET` | `Optional[str]` | `None` | Secret key for verifying HMAC JWT signatures |
| `SUPABASE_SERVICE_ROLE_KEY` | `Optional[str]` | `None` | Service role key for admin database access |
| `SUPABASE_DB_URL` | `Optional[str]` | `None` | Direct PostgreSQL connection string |

---

### 2. LLM Provider Settings (`LLMSettings`)

| Environment Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `NVIDIA_API_KEY` | `Optional[str]` | `None` | NVIDIA NIM Tier 1 LLM API key |
| `NVIDIA_MODEL` | `str` | `""` | NVIDIA NIM model identifier |
| `GROQ_API_KEY` | `Optional[str]` | `None` | Groq high-speed fallback LLM API key |
| `GROQ_MODEL` | `str` | `""` | Groq model identifier |
| `GROQ_API_BASE` | `str` | `""` | Base URL override for Groq endpoint |
| `OPENAI_API_KEY` | `Optional[str]` | `None` | OpenAI API key |
| `ANTHROPIC_API_KEY` | `Optional[str]` | `None` | Anthropic Claude API key |
| `DEEPSEEK_API_KEY` | `Optional[str]` | `None` | DeepSeek API key |
| `OPENROUTER_API_KEY` | `Optional[str]` | `None` | OpenRouter multi-provider API key |
| `OPENROUTER_MODEL` | `str` | `"openai/gpt-4o-mini"` | OpenRouter target model |
| `OPENROUTER_API_BASE` | `str` | `"https://openrouter.ai/api/v1"` | OpenRouter API base endpoint |
| `GOOGLE_API_KEY` | `Optional[str]` | `None` | Google Gemini API key |
| `COHERE_API_KEY` | `Optional[str]` | `None` | Cohere API key |
| `MISTRAL_API_KEY` | `Optional[str]` | `None` | Mistral AI API key |
| `OLLAMA_URL` | `str` | `""` | Base URL for local Ollama server |
| `OLLAMA_BASE_URL` | `str` | `""` | Alternative base URL for Ollama service |
| `LLM_PROVIDER_TIMEOUT_SECONDS` | `int` | `15` | Timeout limit per downstream LLM call |

---

### 3. Pipeline & Document Parser Settings (`PipelineSettings`)

| Environment Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `GROBID_URL` | `str` | `"http://localhost:8070"` | GROBID TEI-XML extraction server URL |
| `GROBID_BASE_URL` | `str` | `"http://localhost:8070"` | Alternative GROBID base URL |
| `GROBID_URLS` | `str` | `""` | Comma-separated list of failover GROBID instance URLs |
| `GROBID_HEALTH_PATH` | `str` | `"/health"` | Health check path for GROBID |
| `DOCX_CONVERTER_HEALTH_PATH` | `str` | `"/health"` | Health check path for DOCX converter service |
| `GROBID_TIMEOUT` | `int` | `10` | Request timeout for GROBID extraction (seconds) |
| `GROBID_MAX_RETRIES` | `int` | `3` | Maximum retry attempts for GROBID service |
| `GROBID_ENABLED` | `bool` | `True` | Enable GROBID service integration |
| `GROBID_SERVICE_URL` | `str` | `"http://localhost:8070"` | Target GROBID service URL |
| `PYMUPDF_FALLBACK` | `bool` | `True` | Fallback to PyMuPDF parsing if GROBID fails |
| `DOCX_CONVERTER_SERVICE_URL` | `str` | `"http://localhost:8080"` | Microservice URL for DOCX/PDF conversion |
| `ENABLE_LOCAL_OCR` | `bool` | `True` | Enable local OCR fallback processing (Tesseract/Paddle) |
| `PIPELINE_GROBID_TIMEOUT_SECONDS` | `int` | `30` | Timeout threshold for pipeline GROBID extraction |
| `PIPELINE_REASONING_TIMEOUT_SECONDS` | `int` | `60` | Timeout threshold for AI reasoning pipeline stage |
| `PIPELINE_SEMANTIC_TIMEOUT_SECONDS` | `int` | `30` | Timeout threshold for semantic layout parsing |
| `PIPELINE_ACQUIRE_TIMEOUT_SECONDS` | `float` | `30.0` | Timeout for acquiring document lock |
| `ENABLE_LLM_PDF_PARSER` | `bool` | `True` | Enable AI-assisted PDF structural parsing |
| `LLM_PDF_PARSER_VISION_API_ENABLED` | `bool` | `True` | Enable vision-based LLM parsing for figure/table extraction |
| `ENABLE_NVIDIA_REASONER` | `bool` | `False` | Enable NVIDIA NIM reasoning engine |
| `LLM_CLASSIFICATION_ENABLED` | `bool` | `True` | Enable LLM classification gate for section mapping |
| `LLM_CLASSIFICATION_FALLBACK_TO_RULES` | `bool` | `True` | Fall back to heuristic rule classification if LLM fails |
| `PRELOAD_AI_MODELS` | `bool` | `True` | Preload transformer/AI models on backend startup |
| `LOW_MEMORY_MODE` | `bool` | `False` | Low-memory mode (disables heavy local transformer models) |
| `RAG_USE_TRANSFORMERS` | `bool` | `True` | Use local sentence-transformers for RAG embeddings |
| `DEFAULT_FAST_MODE` | `bool` | `False` | Default to fast processing mode (skips heavy OCR) |

---

### 4. Security & CORS Settings (`SecuritySettings`)

| Environment Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `ALGORITHM` | `str` | `"HS256"` | JWT signature algorithm |
| `CORS_ORIGINS` | `str` | Localhost origins | Comma-separated list of allowed CORS frontend origins |
| `SIGNED_URL_SECRET` | `Optional[str]` | `None` | Secret key for generating signed document download URLs |
| `FORCE_HTTPS` | `bool` | `False` | Enforce HTTPS redirect headers in production |
| `CLAMAV_HOST` | `str` | `"localhost"` | Host address for ClamAV malware scanning daemon |
| `CLAMAV_PORT` | `int` | `3310` | Port for ClamAV daemon |
| `STRIPE_API_KEY` | `Optional[str]` | `None` | Stripe secret API key for billing endpoints |
| `STRIPE_WEBHOOK_SECRET` | `Optional[str]` | `None` | Stripe webhook signing secret |
| `SENTRY_DSN` | `Optional[str]` | `None` | Sentry DSN endpoint for automated error logging |

---

### 5. Caching & Redis Settings (`CacheSettings`)

| Environment Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `REDIS_ENABLED` | `bool` | `False` | Enable Redis caching layer |
| `REDIS_URL` | `str` | `"redis://localhost:6379"` | Primary Redis connection URI |
| `REDIS_HOST` | `str` | `"localhost"` | Redis server host |
| `REDIS_PORT` | `int` | `6379` | Redis server port |
| `CELERY_BROKER_URL` | `str` | `"redis://localhost:6379/0"` | Celery task queue broker connection URL |
| `CELERY_RESULT_BACKEND` | `str` | `"redis://localhost:6379/0"` | Celery asynchronous result storage URL |
| `LLM_CACHE_TTL_SECONDS` | `int` | `3600` | Time-to-live for cached LLM response prompts |
| `READINESS_CACHE_TTL_SECONDS` | `int` | `15` | TTL for caching service readiness health checks |
| `HEALTH_CACHE_TTL_SECONDS` | `int` | `15` | TTL for general health check results |
| `CSL_SEARCH_CACHE_TTL_SECONDS` | `int` | `300` | TTL for cached CSL search results |
| `CSL_FETCH_CACHE_TTL_SECONDS` | `int` | `1800` | TTL for fetched CSL style XML definitions |
| `GENERATOR_SESSION_CACHE_TTL_SECONDS` | `float` | `2.0` | Cache TTL for generator session state |
| `GENERATOR_MESSAGES_CACHE_TTL_SECONDS` | `float` | `1.0` | Cache TTL for generator chat messages |
| `GENERATOR_SESSION_LIST_CACHE_TTL_SECONDS` | `float` | `3.0` | Cache TTL for generator session listings |
| `GENERATOR_DOCUMENT_CACHE_TTL_SECONDS` | `float` | `2.0` | Cache TTL for active generated manuscript state |
| `DOCUMENT_STATUS_CACHE_TTL_SECONDS` | `float` | `1.0` | Cache TTL for document processing status polling |

---

### 6. Deployment & Feature Settings (`DeploymentSettings`)

| Environment Variable | Type | Default Value | Description |
| --- | --- | --- | --- |
| `DEBUG` | `bool` | `False` | Enable FastAPI debug mode and interactive OpenAPI UI |
| `ENABLE_STRUCTURED_LOGGING` | `bool` | `False` | Output backend logs as structured JSON |
| `GLOBAL_RATE_LIMIT_PER_MINUTE` | `int` | `120` | Global API rate limit cap per IP/user per minute |
| `MAX_FILE_SIZE` | `int` | `62914560` (60MB) | Maximum allowed manuscript file upload size in bytes |
| `MAX_BATCH_FILES` | `int` | `10` | Maximum number of files in a single batch upload |
| `UPLOADS_PER_MINUTE` | `int` | `10` | Rate limit cap specifically for file upload endpoints |
| `ENABLE_FILE_CLEANUP` | `bool` | `True` | Periodically purge expired uploaded files |
| `RETENTION_DAYS` | `int` | `30` | Number of days to retain document artifacts before deletion |
| `GENERATED_OUTPUT_DIR` | `str` | `"output"` | Local directory for storing formatted outputs |
| `DEFAULT_TEMPLATE` | `str` | `"ieee"` | Default academic template identifier |
| `CROSSREF_MAILTO` | `str` | `"dev@example.com"` | Mailto header passed to CrossRef API for rate limit tier |
| `LIBREOFFICE_PATH` | `Optional[str]` | `None` | Path to LibreOffice binary for headless PDF conversion |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | `bool` | `True` | Enable circuit breakers for external downstream services |
| `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `int` | `3` | Consecutive failure threshold to trip circuit breaker |
| `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` | `int` | `60` | Reset cooldown duration for tripped circuit breaker |
| `VLLM_ADOPTION_ENABLED` | `bool` | `True` | Enable automatic vLLM self-hosted transition gating |
| `VLLM_TARGET_MODEL` | `str` | `"meta-llama/Meta-Llama-3.1-8B-Instruct"` | Target model for vLLM deployment |
| `VLLM_TARGET_GPU` | `str` | `"L4 24GB"` | Target GPU instance specification for vLLM |
| `VLLM_REQUESTS_PER_HOUR_THRESHOLD` | `int` | `2000` | Hourly request threshold triggering vLLM deployment recommendation |
| `VLLM_DAILY_TOKENS_THRESHOLD` | `int` | `5000000` | Daily token volume threshold for vLLM adoption |
| `ENHANCEMENTS_ENABLED` | `bool` | `True` | Enable document enhancement pipelines (OCR, keywords) |
| `ENHANCEMENT_QUEUE_ENABLED` | `bool` | `False` | Offload document enhancements to Celery background queue |
| `ENHANCEMENT_QUEUE_PROVIDER` | `str` | `"auto"` | Queue backend selection (`celery`, `redis`, `auto`) |
| `ENHANCEMENT_OCR_ENABLED` | `bool` | `True` | Enable OCR enhancement pass for embedded images |
| `ENHANCEMENT_OCR_BACKENDS` | `str` | `"tesseract,paddle,surya"` | Comma-separated order of OCR backends |
| `ENHANCEMENT_KEYWORD_ENABLED` | `bool` | `True` | Enable automatic keyword extraction pass |
| `ENHANCEMENT_KEYWORD_BACKENDS` | `str` | `"keyllm,keybert,yake,basic"` | Keyword extraction backend hierarchy |
| `ENHANCEMENT_QUEUE_MIN_SECONDS` | `float` | `5.0` | Minimum execution delay for queued tasks |
| `CROSSREF_MAX_WORKERS` | `int` | `4` | Concurrency worker limit for parallel CrossRef lookup calls |
| `HEADING_STYLE_THRESHOLD` | `float` | `0.8` | Confidence threshold for heading style classification |
| `HEADING_FALLBACK_CONFIDENCE` | `float` | `0.5` | Fallback confidence score for unclassified headings |
| `HEURISTIC_CONFIDENCE_HIGH` | `float` | `0.9` | High-confidence heuristic score threshold |
| `HEURISTIC_CONFIDENCE_MEDIUM` | `float` | `0.7` | Medium-confidence heuristic score threshold |
| `HEURISTIC_CONFIDENCE_LOW` | `float` | `0.4` | Low-confidence heuristic threshold |

---

## Feature Flags Summary

Feature flags allow dynamically enabling or disabling subsystem capabilities without codebase changes:

```env
# Document Processing Feature Flags
GROBID_ENABLED=true
PYMUPDF_FALLBACK=true
ENABLE_LOCAL_OCR=true
ENABLE_LLM_PDF_PARSER=true
LLM_PDF_PARSER_VISION_API_ENABLED=true
ENABLE_NVIDIA_REASONER=false

# Caching & Queue Flags
REDIS_ENABLED=true
ENHANCEMENT_QUEUE_ENABLED=false

# Platform Hardening & Hard Limits
FORCE_HTTPS=false
EXTERNAL_CIRCUIT_BREAKER_ENABLED=true
VLLM_ADOPTION_ENABLED=true
ENHANCEMENTS_ENABLED=true
```

---

## CLI Configuration (`amf.json` / `amf.toml`)

CLI configuration settings are stored in `~/.amf/config.json` (or specified via `amf -c path/to/config.json`):

```json
{
  "style": "apa",
  "api_endpoint": "http://localhost:8000",
  "output_dir": ".",
  "page_size": "A4",
  "font_family": "Times New Roman",
  "font_size": 12,
  "line_spacing": 2.0,
  "include_toc": false,
  "include_page_numbers": true,
  "include_running_header": true,
  "verbose": false
}
```

---

## Frontend Environment Configuration (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...
```
