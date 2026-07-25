# ScholarForm AI — Configuration Reference

> **Source of truth:** `backend/app/config/settings.py` via `pydantic-settings`.
> All backend variables are read from a `.env` file located at `backend/.env`.
> Frontend variables are read at build-time via `process.env.*` (prefix `NEXT_PUBLIC_*`).

---

## 1. Core

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `DEBUG` | Enable debug mode (detailed error pages, relaxed CORS defaults, hot-reload) | No | `false` | `true` | `DeploymentSettings` (`backend/app/config/settings.py:387`) |
| `ENCRYPTION_KEY` | 32-byte base64-encoded Fernet key for encrypting user API keys and sensitive data at rest. **Must be stable across restarts** or all encrypted data is lost. | **Production: Yes** | *(none)* | `cGxlYXNlLXJlcGxhY2UtbWUtd2l0aC1hLTI1Ni1iaXQta2V5LTEyMzQ1Njc4OTA=` | `encryption_service.py:20` via `os.environ.get("ENCRYPTION_KEY")` |
| `ALGORITHM` | JWT signing algorithm used by Supabase auth verification | No | `HS256` | `HS256` | `SecuritySettings` (`settings.py:326`) |
| `SIGNED_URL_SECRET` | Secret key for generating signed (pre-signed) document URLs | No | `None` | `a9f3c7b1d8e4f2a6c0b...` | `SecuritySettings` (`settings.py:328`) |
| `CSRF_SECRET` | Secret used for CSRF token generation | No | `""` | *auto-generated* | `SecuritySettings` (`settings.py:335`) |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins. When `DEBUG=false` and unset, defaults to empty (no CORS). When `DEBUG=true` and unset, defaults to localhost:5173,3000. | No | *(see description)* | `http://localhost:5173,https://app.example.com` | `SecuritySettings` (`settings.py:327`), normalized by `_normalize_cors_origins()` |
| `ENABLE_STRUCTURED_LOGGING` | Output JSON-structured logs instead of plain text | No | `false` | `true` | `DeploymentSettings` (`settings.py:388`) |
| `ENVIRONMENT` | Deployment environment label (not read by settings.py; used implicitly by `NODE_ENV` on frontend) | No | *(not set)* | `production` | Inferred; no explicit setting in `settings.py` |
| `ALLOWED_HOSTS` | **Not implemented.** Host filtering is done via CORS + reverse proxy headers on Render. | — | — | — | Not present in codebase |

---

## 2. Database (Supabase)

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `SUPABASE_URL` | Supabase project URL (REST endpoint) | **Yes** | `None` | `https://fnpguxbnycsllvttttlk.supabase.co` | `DatabaseSettings` (`settings.py:210`) |
| `SUPABASE_ANON_KEY` | Supabase anon/public key (RLS-enforced, client-safe) | **Yes** | `None` | `eyJhbGciOiJIUzI1NiIs...` | `DatabaseSettings` (`settings.py:211`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (bypasses RLS — server-side only, never expose to client) | **Yes** | `None` | `eyJhbGciOiJIUzI1NiIs...` | `DatabaseSettings` (`settings.py:214`) |
| `SUPABASE_DB_URL` | Direct PostgreSQL connection string for Alembic migrations and direct DB access | No | `None` | `postgresql://postgres:pass@db.project.supabase.co:5432/postgres` | `DatabaseSettings` (`settings.py:215`) |
| `SUPABASE_JWKS_URL` | JWKS endpoint for verifying Supabase-issued JWT tokens | No | `None` | `https://project.supabase.co/auth/v1/.well-known/jwks.json` | `DatabaseSettings` (`settings.py:212`) |
| `SUPABASE_JWT_SECRET` | JWT secret for decoding user auth tokens (get from Supabase Dashboard → Settings → API) | No | `None` | `YghRBGPvfVnM3vVdgBqbqB...` | `DatabaseSettings` (`settings.py:213`) |

---

## 3. LLM Providers

All keys are optional — the system uses a 4-tier fallback chain: NVIDIA NIM → Groq → OpenRouter → Ollama.

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `NVIDIA_API_KEY` | NVIDIA NIM API key (primary tier) | No | `None` | `nvapi-oz03OmEPyup-Doi5pIlFs...` | `LLMSettings` (`settings.py:226`) |
| `NVIDIA_MODEL` | NVIDIA model identifier | No | `""` | `nvidia_nim/meta/llama-3.3-70b-instruct` | `LLMSettings` (`settings.py:227`) |
| `GROQ_API_KEY` | Groq API key (fallback tier 2) | No | `None` | `gsk_Mxz6fhrmoJFcEeADqBG1...` | `LLMSettings` (`settings.py:228`) |
| `GROQ_MODEL` | Groq model name | No | `""` | `groq/llama-3.3-70b-versatile` | `LLMSettings` (`settings.py:229`) |
| `GROQ_API_BASE` | Groq API base URL | No | `""` | `https://api.groq.com/openai/v1` | `LLMSettings` (`settings.py:230`) |
| `OPENAI_API_KEY` | OpenAI API key | No | `None` | `sk-...` | `LLMSettings` (`settings.py:231`) |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API key | No | `None` | `sk-ant-...` | `LLMSettings` (`settings.py:232`) |
| `DEEPSEEK_API_KEY` | DeepSeek API key | No | `None` | `sk-8d8a276da3bc4926...` | `LLMSettings` (`settings.py:233`) |
| `OPENROUTER_API_KEY` | OpenRouter API key (fallback tier 3) | No | `None` | `sk-or-...` | `LLMSettings` (`settings.py:234`) |
| `OPENROUTER_MODEL` | OpenRouter model identifier | No | `openai/gpt-4o-mini` | `openai/gpt-4o-mini` | `LLMSettings` (`settings.py:235`) |
| `OPENROUTER_API_BASE` | OpenRouter API base URL | No | `https://openrouter.ai/api/v1` | `https://openrouter.ai/api/v1` | `LLMSettings` (`settings.py:236`) |
| `GOOGLE_API_KEY` | Google AI (Gemini) API key | No | `None` | `AIza...` | `LLMSettings` (`settings.py:237`) |
| `COHERE_API_KEY` | Cohere API key | No | `None` | *cohere-key* | `LLMSettings` (`settings.py:238`) |
| `MISTRAL_API_KEY` | Mistral AI API key | No | `None` | *mistral-key* | `LLMSettings` (`settings.py:239`) |
| `OLLAMA_URL` | Ollama server URL (fallback tier 4, local) | No | `""` | `http://localhost:11434` | `LLMSettings` (`settings.py:240`) |
| `OLLAMA_BASE_URL` | Ollama base URL (alias for Ollama_URL) | No | `""` | `http://localhost:11434` | `LLMSettings` (`settings.py:241`) |
| `LLM_PROVIDER_TIMEOUT_SECONDS` | Timeout per LLM provider request | No | `15` | `15` | `LLMSettings` (`settings.py:242`) |
| `HF_TOKEN` | HuggingFace token (used for RAG embeddings inference API) | No | *(not in settings)* | `hf_lGwTAFTRkHbcMVGPhJ...` | `.env.template:18` |

---

## 4. Pipeline / Document Processing

### 4.1 Grobid (PDF parsing — primary)

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `GROBID_ENABLED` | Enable GROBID PDF parsing | No | `true` | `true` | `PipelineSettings` (`settings.py:259`) |
| `GROBID_URL` | GROBID service URL (used as first fallback) | No | `http://localhost:8070` | `http://localhost:8070` | `PipelineSettings` (`settings.py:253`) |
| `GROBID_BASE_URL` | Alias for GROBID_URL | No | `http://localhost:8070` | `http://localhost:8070` | `PipelineSettings` (`settings.py:254`) |
| `GROBID_URLS` | Comma-separated list of GROBID URLs for multi-instance fallback | No | `""` | `http://localhost:SERVICE_PORT,http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:255`) |
| `GROBID_HEALTH_PATH` | Health check path for GROBID service | No | `/api/isalive` | `/api/isalive` | `PipelineSettings` (`settings.py:256`) |
| `GROBID_TIMEOUT` | HTTP request timeout for GROBID (seconds) | No | `10` | `60` | `PipelineSettings` (`settings.py:257`) |
| `GROBID_MAX_RETRIES` | Maximum retry attempts for GROBID calls | No | `3` | `3` | `PipelineSettings` (`settings.py:258`) |
| `USE_DOCLING_FALLBACK` | Fall back to Docling if GROBID fails | No | `true` | `true` | `PipelineSettings` (`settings.py:260`) |
| `PYMUPDF_FALLBACK` | Fall back to PyMuPDF if both GROBID and Docling fail | No | `true` | `true` | `PipelineSettings` (`settings.py:261`) |

### 4.2 Docling (PDF parsing — fallback)

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `DOCLING_URL` | Docling service URL | No | `None` | `http://localhost:5002` | `PipelineSettings` (`settings.py:263`) |
| `DOCLING_URLS` | Comma-separated list of Docling URLs for multi-instance fallback | No | `""` | `http://localhost:SERVICE_PORT,http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:264`) |
| `DOCLING_HEALTH_PATH` | Health check path for Docling service | No | `/` | `/` | `PipelineSettings` (`settings.py:265`) |

### 4.3 LLMClassifier (Classification)

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `USE_LLM_CLASSIFICATION` | Enable LLM-based heading/body classification | No | `false` | `true` | `PipelineSettings` (`settings.py:288`) |
| `LLM_CLASSIFIER_URL` | LLMClassifier service URL | No | `None` | `http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:275`) |
| `LLM_CLASSIFIER_URLS` | Comma-separated list of LLMClassifier URLs | No | `""` | `http://localhost:SERVICE_PORT,http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:276`) |
| `LLM_CLASSIFIER_HEALTH_PATH` | Health check path for LLMClassifier | No | `/` | `/` | `PipelineSettings` (`settings.py:277`) |
| `LLM_CLASSIFIER_AUTO_ENABLE_FROM_BENCHMARK` | Auto-enable LLMClassifier if benchmark F1 meets threshold | No | `true` | `true` | `PipelineSettings` (`settings.py:289`) |
| `LLM_CLASSIFIER_MIN_BENCHMARK_F1` | Minimum F1 score to auto-enable LLMClassifier | No | `0.85` | `0.85` | `PipelineSettings` (`settings.py:290`) |
| `classification_benchmark_STATE_PATH` | File path to persist LLMClassifier benchmark state | No | `.metrics/classification_benchmark_state.json` | `.metrics/classification_benchmark_state.json` | `PipelineSettings` (`settings.py:291`) |

### 4.4 Other Pipeline Services

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `OCR_URL` | OCR service URL | No | `None` | `http://localhost:5003` | `PipelineSettings` (`settings.py:266`) |
| `OCR_URLS` | Comma-separated OCR URLs | No | `""` | `http://localhost:SERVICE_PORT,http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:267`) |
| `DOCX_CONVERTER_URL` | DOCX-to-PDF converter service URL (LibreOffice as a service) | No | `None` | `http://localhost:5004` | `PipelineSettings` (`settings.py:269`) |
| `DOCX_CONVERTER_URLS` | Comma-separated DOCX converter URLs | No | `""` | `http://localhost:SERVICE_PORT,http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:270`) |
| `LLM_PDF_PARSER_URL` | LLM-based PDF parsing (math-aware) service URL | No | `None` | `http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:272`) |
| `LLM_PDF_PARSER_URLS` | Comma-separated LLMPDFParser URLs | No | `""` | `http://localhost:SERVICE_PORT,http://localhost:SERVICE_PORT` | `PipelineSettings` (`settings.py:273`) |
| `ENABLE_LLM_PDF_PARSER` | Enable LLM-based PDF parsing parser as optional fallback | No | `false` | `true` | `PipelineSettings` (`settings.py:286`) |
| `ENABLE_NVIDIA_REASONER` | Toggle NVIDIA reasoning tier for semantic instruction generation | No | `false` | `true` | `PipelineSettings` (`settings.py:287`) |

### 4.5 Pipeline Tuning & Performance

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `PRELOAD_AI_MODELS` | Pre-load AI models at startup (increases boot time, reduces first-request latency) | No | `true` | `false` | `PipelineSettings` (`settings.py:292`) |
| `LOW_MEMORY_MODE` | Enable memory-conserving mode (recommended on Render free tier 512MB) | No | `false` | `true` | `PipelineSettings` (`settings.py:293`) |
| `DEFAULT_FAST_MODE` | Skip optional/slower pipeline stages by default (opt-in for deep AI analysis) | No | `false` | `true` | `PipelineSettings` (`settings.py:295`) |
| `RAG_USE_TRANSFORMERS` | Use local transformers for RAG embeddings (vs HuggingFace Inference API) | No | `true` | `false` | `PipelineSettings` (`settings.py:294`) |
| `PIPELINE_GROBID_TIMEOUT_SECONDS` | Timeout for GROBID parsing within pipeline context | No | `30` | `25` | `PipelineSettings` (`settings.py:279`) |
| `PIPELINE_DOCLING_TIMEOUT_SECONDS` | Timeout for Docling parsing within pipeline | No | `30` | `25` | `PipelineSettings` (`settings.py:280`) |
| `PIPELINE_REASONING_TIMEOUT_SECONDS` | Timeout for LLM reasoning/semantic analysis stage | No | `60` | `28` | `PipelineSettings` (`settings.py:281`) |
| `PIPELINE_SEMANTIC_TIMEOUT_SECONDS` | Timeout for semantic enrichment stage | No | `30` | `25` | `PipelineSettings` (`settings.py:282`) |
| `PIPELINE_ACQUIRE_TIMEOUT_SECONDS` | Timeout for acquiring pipeline resources (semaphore) | No | `30.0` | `30.0` | `PipelineSettings` (`settings.py:283`) |
| `PIPELINE_DOCLING_SKIP_DIGITAL_PDF` | Skip Docling pass for digital-native PDFs (faster) | No | `false` | `true` | `PipelineSettings` (`settings.py:284`) |
| `PIPELINE_DOCLING_FORCE` | Force Docling on every PDF (even digital-born) | No | `false` | `false` | `PipelineSettings` (`settings.py:285`) |
| `CROSSREF_MAX_WORKERS` | Max concurrent Crossref API workers | No | `4` | `4` | `DeploymentSettings` (`settings.py:418`) |
| `CROSSREF_MAILTO` | Email identifier for Crossref API (polite pool) | **Yes** | `dev@example.com` | `scholarformai@gmail.com` | `DeploymentSettings` (`settings.py:397`) |
| `LIBREOFFICE_PATH` | Path to LibreOffice executable (for local DOCX→PDF conversion) | No | `None` | `/usr/bin/soffice` or `C:/Program Files/LibreOffice/program/soffice.exe` | `DeploymentSettings` (`settings.py:398`) |

### 4.6 Enhancement Layer

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `ENHANCEMENTS_ENABLED` | Master toggle for all enhancement features | No | `true` | `true` | `DeploymentSettings` (`settings.py:410`) |
| `ENHANCEMENT_QUEUE_ENABLED` | Enable async enhancement queue (Celery) | No | `false` | `true` | `DeploymentSettings` (`settings.py:411`) |
| `ENHANCEMENT_QUEUE_PROVIDER` | Queue provider: `auto`, `local`, or `celery` | No | `auto` | `celery` | `DeploymentSettings` (`settings.py:412`) |
| `ENHANCEMENT_QUEUE_MIN_SECONDS` | Minimum seconds before enhancement processing starts | No | `5.0` | `5.0` | `DeploymentSettings` (`settings.py:416`) |
| `ENHANCEMENT_OCR_ENABLED` | Enable OCR enhancement pass | No | `true` | `true` | `DeploymentSettings` (`settings.py:413`) |
| `ENHANCEMENT_OCR_BACKENDS` | Comma-separated OCR backends in priority order | No | `tesseract,paddle,surya` | `rapidocr,paddle,surya,tesseract,basic` | `DeploymentSettings` (`settings.py:414`) |
| `ENHANCEMENT_KEYWORD_ENABLED` | Enable keyword/keyphrase extraction enhancement | No | `true` | `true` | `DeploymentSettings` (`settings.py:415`) |
| `ENHANCEMENT_KEYWORD_BACKENDS` | Comma-separated keyword extraction backends | No | `keyllm,keybert,yake,basic` | `keybert,yake,basic` | `DeploymentSettings` (`settings.py:416`) |

### 4.7 Heuristic & Heading Confidence

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `HEADING_STYLE_THRESHOLD` | Minimum style-match score (0–1) to classify a block as heading | No | `0.8` | `0.4` | `DeploymentSettings` (`settings.py:420`) |
| `HEADING_FALLBACK_CONFIDENCE` | Confidence floor for heuristic heading detection | No | `0.5` | `0.45` | `DeploymentSettings` (`settings.py:421`) |
| `HEURISTIC_CONFIDENCE_HIGH` | High-confidence threshold for heuristics | No | `0.9` | `0.95` | `DeploymentSettings` (`settings.py:422`) |
| `HEURISTIC_CONFIDENCE_MEDIUM` | Medium-confidence threshold | No | `0.7` | `0.9` | `DeploymentSettings` (`settings.py:423`) |
| `HEURISTIC_CONFIDENCE_LOW` | Low-confidence threshold | No | `0.4` | `0.5` | `DeploymentSettings` (`settings.py:424`) |

### 4.8 RAG / Embeddings

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `RAG_USE_TRANSFORMERS` | Use local `sentence-transformers` vs HuggingFace Inference API | No | `true` | `false` | `PipelineSettings` (`settings.py:294`) |
| `RAG_EMBEDDING_PROVIDER` | Embedding provider (e.g., `huggingface_api`) | No | *(not in settings)* | `huggingface_api` | `.env.render:92` |
| `RAG_EMBEDDING_MODEL` | Embedding model identifier | No | *(not in settings)* | `sentence-transformers/all-MiniLM-L6-v2` | `.env.render:93` |
| `RAG_EMBEDDING_API_URL` | Embedding API endpoint | No | *(not in settings)* | `https://router.huggingface.co/hf-inference/models/...` | `.env.render:94` |

### 4.9 Template / Output Defaults

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `DEFAULT_TEMPLATE` | Default manuscript template | No | `ieee` | `none`, `ieee`, `springer`, `apa` | `DeploymentSettings` (`settings.py:396`) |
| `GENERATED_OUTPUT_DIR` | Directory for generated output files | No | `output` | `generated_outputs` | `DeploymentSettings` (`settings.py:395`) |

---

## 5. Security

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `FORCE_HTTPS` | Redirect all HTTP traffic to HTTPS (enforce in production) | No | `false` | `true` | `SecuritySettings` (`settings.py:329`) |
| `GLOBAL_RATE_LIMIT_PER_MINUTE` | Global API rate limit (requests per minute per IP) | No | `120` | `120` | `DeploymentSettings` (`settings.py:389`) |
| `CLAMAV_HOST` | ClamAV daemon host for virus scanning | No | `localhost` | `localhost` | `SecuritySettings` (`settings.py:330`) |
| `CLAMAV_PORT` | ClamAV daemon port | No | `3310` | `3310` | `SecuritySettings` (`settings.py:331`) |
| `STRIPE_API_KEY` | Stripe secret key for billing | No | `None` | `sk_live_...` | `SecuritySettings` (`settings.py:332`) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | No | `None` | `whsec_...` | `SecuritySettings` (`settings.py:333`) |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | Enable circuit breaker for external service calls | No | `true` | `true` | `DeploymentSettings` (`settings.py:400`) |
| `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | Consecutive failures to open circuit | No | `3` | `3` | `DeploymentSettings` (`settings.py:401`) |
| `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` | Seconds before half-open retry | No | `60` | `60` | `DeploymentSettings` (`settings.py:402`) |
| `VLLM_ADOPTION_ENABLED` | Enable vLLM adoption workflow tracking | No | `true` | `true` | `DeploymentSettings` (`settings.py:404`) |
| `VLLM_TARGET_MODEL` | Target model for vLLM deployment planning | No | `meta-llama/Meta-Llama-3.1-8B-Instruct` | `meta-llama/Meta-Llama-3.1-8B-Instruct` | `DeploymentSettings` (`settings.py:405`) |
| `VLLM_TARGET_GPU` | Target GPU for vLLM deployment planning | No | `L4 24GB` | `L4 24GB` | `DeploymentSettings` (`settings.py:406`) |
| `VLLM_REQUESTS_PER_HOUR_THRESHOLD` | Hourly request threshold for vLLM migration trigger | No | `2000` | `2000` | `DeploymentSettings` (`settings.py:407`) |
| `VLLM_DAILY_TOKENS_THRESHOLD` | Daily token threshold for vLLM migration trigger | No | `5000000` | `5000000` | `DeploymentSettings` (`settings.py:408`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | **Not implemented.** JWT expiry is managed by Supabase. | — | — | — | Not present in codebase |
| `CSP_DIRECTIVES` | **Not implemented.** Security headers are set in `next.config.mjs` (X-Content-Type-Options, X-Frame-Options, Referrer-Policy). | — | — | — | `next.config.mjs:28-36` |

---

## 6. Storage / Uploads

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `MAX_FILE_SIZE` | Maximum uploaded file size in bytes (~57MB default) | No | `62914560` (60×1024×1024) | `52428800` (50MB) | `DeploymentSettings` (`settings.py:390`) |
| `MAX_BATCH_FILES` | Maximum number of files per batch upload | No | `10` | `10` | `DeploymentSettings` (`settings.py:391`) |
| `UPLOADS_PER_MINUTE` | Upload rate limit (uploads per minute per user) | No | `10` | `10` | `DeploymentSettings` (`settings.py:392`) |
| `ENABLE_FILE_CLEANUP` | Enable periodic cleanup of stale uploaded files | No | `true` | `true` | `DeploymentSettings` (`settings.py:393`) |
| `RETENTION_DAYS` | Days to retain uploaded / generated files before cleanup | No | `30` | `30` | `DeploymentSettings` (`settings.py:394`) |
| `GENERATED_OUTPUT_DIR` | Directory for generated manuscript outputs | No | `output` | `generated_outputs` | `DeploymentSettings` (`settings.py:395`) |
| `UPLOAD_DIR` | **Hardcoded** as `"uploads"` in `documents_impl.py:37` — not configurable via env var. Upload directory for incoming documents. | — | `uploads` | `uploads` | `backend/app/routers/v1/documents_impl.py:37` |

---

## 7. Redis / Cache

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `REDIS_ENABLED` | Enable Redis caching (disable for local dev without Redis) | No | `false` | `true` | `CacheSettings` (`settings.py:356`) |
| `REDIS_URL` | Redis connection URL | No | `redis://localhost:6379` | `rediss://default:pass@host.upstash.io:6379` | `CacheSettings` (`settings.py:357`) |
| `REDIS_HOST` | Redis host (legacy, used when REDIS_URL not set) | No | `localhost` | `dominant-insect-81050.upstash.io` | `CacheSettings` (`settings.py:358`) |
| `REDIS_PORT` | Redis port | No | `6379` | `6379` | `CacheSettings` (`settings.py:359`) |

### 7.1 Cache TTLs

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `LLM_CACHE_TTL_SECONDS` | LLM response cache TTL | No | `3600` | `3600` | `CacheSettings` (`settings.py:362`) |
| `READINESS_CACHE_TTL_SECONDS` | Readiness probe cache TTL | No | `15` | `15` | `CacheSettings` (`settings.py:363`) |
| `HEALTH_CACHE_TTL_SECONDS` | Health check cache TTL | No | `15` | `15` | `CacheSettings` (`settings.py:364`) |
| `CSL_SEARCH_CACHE_TTL_SECONDS` | CSL style search results cache TTL | No | `300` | `300` | `CacheSettings` (`settings.py:365`) |
| `CSL_FETCH_CACHE_TTL_SECONDS` | CSL style fetch/content cache TTL | No | `1800` | `1800` | `CacheSettings` (`settings.py:366`) |
| `GENERATOR_SESSION_CACHE_TTL_SECONDS` | Generator session state cache TTL | No | `2.0` | `2.0` | `CacheSettings` (`settings.py:367`) |
| `GENERATOR_MESSAGES_CACHE_TTL_SECONDS` | Generator messages list cache TTL | No | `1.0` | `1.0` | `CacheSettings` (`settings.py:368`) |
| `GENERATOR_SESSION_LIST_CACHE_TTL_SECONDS` | Generator session list cache TTL | No | `3.0` | `3.0` | `CacheSettings` (`settings.py:369`) |
| `GENERATOR_DOCUMENT_CACHE_TTL_SECONDS` | Generator document state cache TTL | No | `2.0` | `2.0` | `CacheSettings` (`settings.py:370`) |
| `DOCUMENT_STATUS_CACHE_TTL_SECONDS` | Document status poll cache TTL | No | `1.0` | `1.0` | `CacheSettings` (`settings.py:371`) |

---

## 8. Celery / Task Queue

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `CELERY_BROKER_URL` | Celery message broker URL (typically Redis) | No | `redis://localhost:6379/0` | `rediss://default:pass@host.upstash.io:6379/0` | `CacheSettings` (`settings.py:360`) |
| `CELERY_RESULT_BACKEND` | Celery result backend URL (typically same as broker) | No | `redis://localhost:6379/0` | `rediss://default:pass@host.upstash.io:6379/0` | `CacheSettings` (`settings.py:361`) |
| `WORKER_CONCURRENCY` | Celery worker concurrency (number of concurrent tasks) | No | `2` | `2` | `render.yaml:83` (`-c ${WORKER_CONCURRENCY:-2}`) |
| `WEB_CONCURRENCY` | Uvicorn HTTP worker processes | No | `1` | `2` | `render.yaml:71` (`--workers ${WEB_CONCURRENCY:-1}`) |

---

## 9. Frontend (Next.js)

All frontend variables are prefixed with `NEXT_PUBLIC_` (exposed to the browser). Set in `frontend/.env` or at build-time.

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL for client-side auth & data access | **Yes** | *(none)* | `https://fnpguxbnycsllvttttlk.supabase.co` | `frontend/.env.example:2` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key for client-side auth | **Yes** | *(none)* | `eyJhbGciOiJIUzI1NiIs...` | `frontend/.env.example:3` |
| `NEXT_PUBLIC_API_URL` | Backend FastAPI base URL for client-side API calls | **Yes** | *(none)* | `http://localhost:8000` | `frontend/.env.example:6` |
| `NEXT_PUBLIC_API_BASE_URL` | Alternative API base URL (not used by core app code) | No | *(none)* | `http://localhost:8000/api/v1` | `frontend/.env.example:29` |
| `NEXT_PUBLIC_LATEX_EXPORT_ENABLED` | Toggle LaTeX export feature in the UI | No | `false` | `false` | `frontend/.env.example:7` |
| `CDN_URL` | CDN URL prefix for static assets (assetPrefix + image remotePatterns) | No | `""` | `https://cdn.scholarform.ai` | `next.config.mjs:22` |
| `PLAYWRIGHT_BASE_URL` | Base URL for Playwright E2E tests | No | *(none)* | `http://127.0.0.1:3001` | `frontend/.env.example:25` |
| `VITE_APP_SKILLS` | Comma-separated skill names (documentation only) | No | *(none)* | `document-formatter,resume-formatter,...` | `frontend/.env.example:14` |
| `VITE_APP_SKILLS_LINKS` | Semicolon-separated skill repository URLs (documentation only) | No | *(none)* | `https://github.com/...` | `frontend/.env.example:16` |
| `VITE_APP_SKILLS_ADD_COMMAND_*` | Per-skill install commands (documentation only) | No | *(none)* | `npx skills add https://...` | `frontend/.env.example:18-22` |

---

## 10. Render Deployment (Platform-Specific)

Set in `render.yaml` or via Render dashboard environment variables.

| Variable | Description | Required | Default | Example | Source |
|---|---|---|---|---|---|
| `PYTHON_VERSION` | Python runtime version for Render build | **Yes** | *(none)* | `3.12.2` | `render.yaml:8`; `.env.render:140` |
| `PORT` | Port assigned by Render ($PORT injected at runtime) | — | *(Render auto)* | `10000` | `render.yaml:71` |
| `ENABLE_LEGACY_ROUTES` | Toggle legacy API route support | No | `false` | `false` | `render.yaml:12`; `.env.render:143` |

---

## 12. Testing — Configuration Validation

### Testing Configuration Loading

```python
# test_config_loading.py
from app.config.settings import Settings

def test_default_values_used_when_env_unset(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    settings = Settings()
    assert settings.DEBUG is False
    assert settings.SUPABASE_URL is None

def test_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    settings = Settings()
    assert settings.DEBUG is True

def test_bool_coercion_accepts_various_formats(monkeypatch):
    for val in ["true", "True", "1", "yes"]:
        monkeypatch.setenv("DEBUG", val)
        assert Settings().DEBUG is True
    for val in ["false", "False", "0", "no", ""]:
        monkeypatch.setenv("DEBUG", val)
        assert Settings().DEBUG is False

def test_complex_types_parsed_correctly(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,https://app.example.com")
    settings = Settings()
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "https://app.example.com" in settings.CORS_ORIGINS

def test_encryption_key_required_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        Settings()
```

### Validating Required Environment Variables

```bash
# CI check — ensure all required vars are documented
python scripts/validate_env_vars.py

# Check .env against .env.example
python -c "
from dotenv import dotenv_values
example = dotenv_values('.env.example')
actual = dotenv_values('.env')
missing = [k for k in example if k not in actual and example[k]]
if missing:
    print(f'MISSING: {missing}')
    exit(1)
print('All required vars present')
"
```

Test patterns for required variable validation:

```python
# test_config_validation.py
REQUIRED_VARS = [
    "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
    "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY", "NEXT_PUBLIC_API_URL",
]

def test_required_vars_documented():
    """Verify that required vars are documented in CONFIGURATION_REFERENCE.md"""
    with open("docs/CONFIGURATION_REFERENCE.md") as f:
        content = f.read()
    for var in REQUIRED_VARS:
        assert var in content, f"{var} not documented in CONFIGURATION_REFERENCE.md"

def test_all_env_vars_have_settings_class():
    """Verify each documented var has a corresponding Settings class"""
    from app.config.settings import DeploymentSettings, PipelineSettings, CacheSettings, ...
    # Pattern: each env var should map to a pydantic Field in a Settings subclass
```

### Configuration Resolution Chain

```mermaid
graph TD
    A[Configuration Request] --> B{pydantic-settings<br/>Field()}
    B --> C[Default Value<br/>Field(default=...)]
    C --> D{.env file<br/>backend/.env}
    D --> E[Environment Variable<br/>os.environ / Render Dashboard]
    E --> F[Runtime Override<br/>request.state / feature flag]
    F --> G[Effective Value]

    subgraph "Resolution Priority (low → high)"
        C
        D
        E
        F
    end

    style C fill:#e1f5fe
    style D fill:#fff3e0
    style E fill:#e8f5e9
    style F fill:#fce4ec
```

---

## Appendix A: Missing Variables Summary & Remediation

The following variables from the original schema outline do **not** exist in this codebase. Each entry includes a remediation plan.

| Variable | Status | Impact | Remediation |
|---|---|---|---|
| `SECRET_KEY` | **Not present** | No impact — `SIGNED_URL_SECRET` serves URL signing; JWT verification uses Supabase JWKS | N/A — alternative exists |
| `ALLOWED_HOSTS` | **Not present** | Low — host filtering delegated to Render reverse proxy + CORS | If self-hosting, add `ALLOWED_HOSTS` via `uvicorn --forwarded-allow-ips` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | **Not present** | Low — token expiry managed by Supabase Auth dashboard | Configure via Supabase Dashboard → Authentication → Settings → JWT expiry |
| `CSP_DIRECTIVES` | **Not present** | Medium — security headers hardcoded in `next.config.mjs` | Extract to env var: `NEXT_PUBLIC_CSP_DIRECTIVES` with secure defaults |
| `REDIS_TTL_SECONDS` | **Not a single var** | None — replaced by per-use-case TTLs (see §7.1) | Document clearly (already done) |
| `CELERY_WORKER_CONCURRENCY` | **Named `WORKER_CONCURRENCY`** | Confusion risk | Add alias `CELERY_WORKER_CONCURRENCY=WORKER_CONCURRENCY` in `render.yaml` |
| `UPLOAD_DIR` | **Hardcoded** | Low — set as `"uploads"` in `documents_impl.py:37` | Add `UPLOAD_DIR` to `DeploymentSettings` with current value as default |
| `ENVIRONMENT` | **Implicit only** | Low — `NODE_ENV` on frontend, `DEBUG` on backend | Add explicit `ENVIRONMENT` field to `DeploymentSettings` with validation
