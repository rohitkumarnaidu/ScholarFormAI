# Configuration Reference

ScholarForm AI uses Pydantic settings (`pydantic-settings`) in `backend/app/config/settings.py` to load and validate environment variables from `backend/.env`.

Settings are logically structured into 6 sub-configuration classes within the unified `Settings` model.

---

## Unified Sub-Config Structure

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

## Environment Variables Reference

### 1. Database Settings (`DatabaseSettings`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `SUPABASE_URL` | `str \| None` | `None` | Supabase project URL (`https://<project-ref>.supabase.co`) |
| `SUPABASE_ANON_KEY` | `str \| None` | `None` | Supabase anonymous API key for public/client operations |
| `SUPABASE_JWKS_URL` | `str \| None` | `None` | Supabase JWKS URL for JWT validation |
| `SUPABASE_JWT_SECRET` | `str \| None` | `None` | Supabase JWT secret for HMAC token verification |
| `SUPABASE_SERVICE_ROLE_KEY` | `str \| None` | `None` | Supabase service role key for admin DB access |
| `SUPABASE_DB_URL` | `str \| None` | `None` | Direct PostgreSQL connection string |

### 2. LLM Settings (`LLMSettings`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `NVIDIA_API_KEY` | `str \| None` | `None` | Primary Tier 1 LLM API key (NVIDIA NIM) |
| `NVIDIA_MODEL` | `str` | `""` | Target NVIDIA NIM model identifier |
| `GROQ_API_KEY` | `str \| None` | `None` | Tier 2 LLM fallback API key (Groq) |
| `GROQ_MODEL` | `str` | `""` | Target Groq model identifier |
| `OPENROUTER_API_KEY` | `str \| None` | `None` | OpenRouter multi-provider API key |
| `OPENROUTER_MODEL` | `str` | `"openai/gpt-4o-mini"` | Target OpenRouter model identifier |
| `OLLAMA_URL` | `str` | `""` | Local Tier 3 Ollama server base URL |
| `LLM_PROVIDER_TIMEOUT_SECONDS` | `int` | `15` | Timeout limit per LLM invocation |

### 3. Pipeline Settings (`PipelineSettings`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `GROBID_URL` | `str` | `"http://localhost:8070"` | GROBID service endpoint for PDF TEI-XML extraction |
| `GROBID_ENABLED` | `bool` | `True` | Enable GROBID service integration |
| `DOCX_CONVERTER_SERVICE_URL` | `str` | `"http://localhost:8080"` | DOCX conversion service endpoint |
| `ENABLE_LOCAL_OCR` | `bool` | `True` | Enable local OCR fallback processing |
| `PYMUPDF_FALLBACK` | `bool` | `True` | Fallback to PyMuPDF parsing if GROBID fails |
| `ENABLE_LLM_PDF_PARSER` | `bool` | `True` | Enable AI-augmented PDF structural parsing |

### 4. Security Settings (`SecuritySettings`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `ALGORITHM` | `str` | `"HS256"` | JWT signature algorithm |
| `CORS_ORIGINS` | `str` | Localhost defaults | Comma-separated list of allowed CORS origin URLs |
| `FORCE_HTTPS` | `bool` | `False` | Force HTTPS redirect header enforcement |
| `CLAMAV_HOST` | `str` | `"localhost"` | ClamAV virus scanning daemon host |
| `CLAMAV_PORT` | `int` | `3310` | ClamAV virus scanning daemon port |
| `SENTRY_DSN` | `str \| None` | `None` | Sentry Error Tracking DSN URI |

### 5. Cache Settings (`CacheSettings`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `REDIS_ENABLED` | `bool` | `False` | Enable Redis caching layer |
| `REDIS_URL` | `str` | `"redis://localhost:6379"` | Connection URI for Redis server |
| `CELERY_BROKER_URL` | `str` | `"redis://localhost:6379/0"` | Celery message broker URI |
| `CELERY_RESULT_BACKEND` | `str` | `"redis://localhost:6379/0"` | Celery async result backend URI |

### 6. Deployment Settings (`DeploymentSettings`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `DEBUG` | `bool` | `False` | Enable FastAPI debug mode and OpenAPI `/docs` |
| `ENABLE_STRUCTURED_LOGGING` | `bool` | `False` | Format server output logs as structured JSON |
| `MAX_FILE_SIZE` | `int` | `62914560` (60MB) | Maximum manuscript file upload size in bytes |
| `RETENTION_DAYS` | `int` | `30` | Number of days to retain processed documents |
| `DEFAULT_TEMPLATE` | `str` | `"ieee"` | Default target template |

---

## Backend `.env` Template

Create or edit `backend/.env`:

```env
# Database & Auth
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
SUPABASE_JWT_SECRET=super-secret-jwt-key

# LLM Providers
NVIDIA_API_KEY=nvapi-...
GROQ_API_KEY=gsk_...

# Caching & Infrastructure
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379

# Environment & Security
DEBUG=true
FORCE_HTTPS=false
SENTRY_DSN=https://example@sentry.io/123456
```

---

## Frontend Environment Variables (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xyz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...
```
