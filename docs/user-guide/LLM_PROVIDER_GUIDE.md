<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — LLM Provider Integration Guide
description: Comprehensive guide to LLM provider architecture, BYOK, custom providers, fallback chain, and configuration
sidebar_position: 50
version: "1.0"
status: ✅ Complete
owner: Engineering
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — LLM Provider Integration Guide

**Audience:** Developers, DevOps, and power users  
**Time:** 15 minutes

> **See also:** [API Key Quick-Start](../api/API_KEY_QUICK_START.md), [API Reference](API.md), [Security](../../SECURITY.md)

---

## Table of Contents

- [Overview](#overview)
- [Provider Architecture](#provider-architecture)
- [Built-in Provider Reference](#built-in-provider-reference)
- [BYOK (Bring Your Own Key)](#byok-bring-your-own-key)
- [Custom Providers](#custom-providers)
- [4-Tier Fallback Chain](#4-tier-fallback-chain)
- [Model Selection](#model-selection)
- [API Key Management](#api-key-management)
- [Configuration Reference](#configuration-reference)
- [Troubleshooting](#troubleshooting)

---

## Overview

ScholarForm AI integrates with **10 built-in LLM providers** out of the box and supports **Bring Your Own Key (BYOK)** and **custom OpenAI-compatible endpoints**. The integration layer is built on [LiteLLM](https://litellm.ai/) for unified provider access, with direct HTTP fallbacks when LiteLLM is unavailable.

### Key Capabilities

| Feature | Description |
| --------- | ------------- |
| 10 Built-in Providers | OpenAI, Anthropic, Groq, DeepSeek, OpenRouter, Google, Cohere, Mistral, Ollama, NVIDIA NIM |
| BYOK | Users store their own API keys, encrypted at rest, overriding environment defaults |
| Custom Providers | CRUD API for any OpenAI-compatible endpoint (vLLM, TGI, local models) |
| 4-Tier Fallback | NVIDIA NIM &rarr; Groq &rarr; OpenRouter &rarr; Ollama/DeepSeek with per-provider circuit breakers |
| Model Discovery | Live `/v1/models` or Ollama `/api/tags` endpoint probing |
| Response Caching | Redis-backed LLM response cache with configurable TTL |
| Prompt Injection Guard | 30+ regex patterns filter known injection vectors before requests leave the server |

---

## Provider Architecture

### Layered Design

```mermaid
flowchart TD
    UI[Chat UI / Pipeline]
    
    subgraph UnifiedLayer [llm_service.py]
        Methods[generate()<br>generate_with_model()<br>generate_with_fallback()<br>check_health()]
    end
    
    subgraph Registry [provider_registry.py]
        RegDefs[BUILTIN_PROVIDERS<br>list_available_models()<br>resolve_model_provider()<br>normalize_model_name()<br>cache_discovered_models()]
    end
    
    subgraph Clients [Provider API Clients / LiteLLM]
        OpenAI[OpenAI Client]
        Anthropic[Anthropic Client]
        Groq[Groq Client]
        Nvidia[NVIDIA direct<br>nvidia_client.py]
    end

    UI --> UnifiedLayer
    UnifiedLayer --> Registry
    Registry --> OpenAI
    Registry --> Anthropic
    Registry --> Groq
    Registry --> Nvidia
```

### Provider Registry (`provider_registry.py`)

The registry at `backend/app/services/provider_registry.py` is the single source of truth for all built-in provider definitions. Each entry specifies:

- `name` &mdash; Human-readable display name
- `base_url` &mdash; API endpoint (may be a callable for dynamic URLs like Ollama)
- `models` &mdash; Static model list (some providers use dynamic discovery)
- `env_key` &mdash; Environment variable name for the API key
- `env_key_actual` &mdash; Lambda that resolves the key from settings at runtime
- `default_model` &mdash; Model used when no preference is specified
- `supports_custom_base_url` &mdash; Whether the provider allows base URL overrides
- `is_local` &mdash; Flag for locally-hosted providers (Ollama)

### Model Discovery

Models come from three sources:

1. **Static definitions** &mdash; Declared in `BUILTIN_PROVIDERS` at startup
2. **Live discovery** &mdash; Via `GET /api/v1/providers/{id}/models` which probes the provider's `/v1/models` or Ollama `/api/tags` endpoint
3. **Cached discovery** &mdash; Discovered models are cached in-memory per user (1-hour TTL) via `cache_discovered_models()`

### OpenAI-Compatible Providers

The following providers support the OpenAI-compatible chat completions format and can be used interchangeably via the same HTTP path:

```python
OPENAI_COMPATIBLE_PROVIDERS = {
    "openai", "groq", "deepseek", "openrouter", "nvidia", "mistral",
}
```

For these providers, calls route through `_generate_openai_compat()` when LiteLLM is unavailable, using the OpenAI Python client.

---

## Built-in Provider Reference

### Provider Table

| ID | Name | Base URL | Models | Env Var | Default Model | Local |
| ---- | ------ | ---------- | -------- | --------- | --------------- | ------- |
| `openai` | OpenAI | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`, `o1`, `o1-mini`, `o3-mini` | `OPENAI_API_KEY` | `gpt-4o-mini` | No |
| `anthropic` | Anthropic | `https://api.anthropic.com/v1` | `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, `claude-3-opus-20240229`, `claude-3-sonnet-20240229` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` | No |
| `groq` | Groq | `https://api.groq.com/openai/v1` | `llama3-70b-8192`, `llama3-8b-8192`, `mixtral-8x7b-32768`, `gemma2-9b-it` | `GROQ_API_KEY` | `llama3-8b-8192` (or `GROQ_MODEL`) | No |
| `deepseek` | DeepSeek | `https://api.deepseek.com` | `deepseek-chat`, `deepseek-reasoner` | `DEEPSEEK_API_KEY` | `deepseek-chat` | No |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` | `openai/gpt-4o`, `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`, `google/gemini-pro`, `meta-llama/llama-3.1-70b-instruct` | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` (or `OPENROUTER_MODEL`) | No |
| `google` | Google AI | `https://generativelanguage.googleapis.com/v1beta` | `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash` | `GOOGLE_API_KEY` | `gemini-2.0-flash` | No |
| `cohere` | Cohere | `https://api.cohere.com/v1` | `command-r-plus`, `command-r`, `command-light` | `COHERE_API_KEY` | `command-r-plus` | No |
| `mistral` | Mistral | `https://api.mistral.ai/v1` | `mistral-large-latest`, `mistral-small-latest`, `open-mistral-7b`, `codestral-latest` | `MISTRAL_API_KEY` | `mistral-small-latest` | No |
| `ollama` | Ollama (Local) | `http://localhost:11434` (or `OLLAMA_BASE_URL`) | Dynamically discovered via `/api/tags` | None | `deepseek-r1` | Yes |
| `nvidia` | NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | Configured by `NVIDIA_MODEL` (e.g. `meta/llama-3.3-70b-instruct`) | `NVIDIA_API_KEY` | Set by `NVIDIA_MODEL` | No |

### Model Name Convention

Models are identified by their provider prefix followed by `/` and the model name:

- `nvidia_nim/meta/llama-3.3-70b-instruct`
- `groq/llama3-8b-8192`
- `openrouter/openai/gpt-4o-mini`
- `ollama/deepseek-r1`
- `gpt-4o` (bare name resolves to OpenAI)

The function `resolve_model_provider()` in `provider_registry.py:269` maps a model name to its provider by checking:

1. Provider-prefixed names (`groq/llama3-8b-8192`)
2. Static model lists in `BUILTIN_PROVIDERS`
3. Heuristic prefixes (`gpt-`, `claude`, `nvidia_nim/`)

---

## BYOK (Bring Your Own Key)

### Key Resolution Priority

When a request requires an API key, `resolve_user_api_key()` at `llm_service.py:90` follows this priority:

1. **User-stored key** &mdash; If `user_id` is provided, look up an active key from the `user_api_keys` table for the given provider
2. **Environment variable** &mdash; Fall back to the `*_API_KEY` environment variable (e.g., `OPENAI_API_KEY`)

```
User API key exists for provider?
  ├── Yes → Decrypt and return
  └── No  → Return env var value (or None)
```

### Encryption at Rest

User-provided API keys are encrypted before storage using **Fernet symmetric encryption** (`encryption_service.py`):

```python
# Encryption
ciphertext = fernet.encrypt(plaintext.encode())
return base64.b64encode(ciphertext).decode()

# Decryption
raw = base64.b64decode(ciphertext)
return fernet.decrypt(raw).decode()
```

Key management details:

- **Encryption key**: Stored in `ENCRYPTION_KEY` environment variable (must be a valid 32-byte base64-encoded Fernet key)
- **Generation**: Run `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` to create a new key
- **Key rotation**: Call `EncryptionService.generate_key()` to produce a new key; re-encrypt all stored keys during rotation
- **Storage**: Encrypted keys stored in `UserApiKey.api_key_encrypted` column (PostgreSQL `TEXT`)

All decryption errors (key mismatch, corrupted data) raise `ValueError("Decryption failed: invalid key or corrupted data")`.

---

## Custom Providers

Custom providers allow users to connect any **OpenAI-compatible** API endpoint (vLLM, TGI, llama.cpp, LocalAI, etc.).

### Data Model (`custom_provider.py`)

| Field | Type | Description |
| ------- | ------ | ------------- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Owner of this provider |
| `name` | String(100) | Display name |
| `base_url` | String(500) | API base URL (e.g. `http://192.168.1.50:8000/v1`) |
| `api_key_encrypted` | Text | Optional encrypted API key |
| `models` | JSON | List of model identifiers |
| `is_local` | Boolean | Whether this is a local/self-hosted endpoint |
| `description` | String(500) | Optional description |
| `is_active` | Boolean | Soft-delete flag |

### CRUD API

All endpoints require authentication and are scoped to the authenticated user.

#### Create Custom Provider

```http
POST /api/v1/providers/custom
Content-Type: application/json

{
  "name": "My vLLM Instance",
  "base_url": "https://vllm.example.com/v1",
  "api_key": "optional-api-key-here",
  "models": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
  "is_local": false,
  "description": "Self-hosted vLLM on GCP"
}
```

**Validation rules:**

- Max **25 custom providers** per user
- `base_url` must be `http`/`https` and is SSRF-protected (blocks private IPs, loopback, metadata endpoints)
- `api_key` must be 8&ndash;2000 characters when provided
- `models` limited to 100 entries

**SSRF Protection** (`providers.py:43-58`):

```python
SSRF_BLOCKED_HOSTS = {
    "169.254.169.254", "metadata.google.internal",
    "100.100.100.200", "127.0.0.1", "localhost",
    "0.0.0.0", "::1"
}
SSRF_BLOCKED_SCHEMES = {"file", "ftp", "dict", "gopher"}
```

All URLs are validated to block private/reserved IP ranges (RFC 1918, loopback, link-local) and dangerous URL schemes.

#### List Custom Providers

```http
GET /api/v1/providers/custom
```

Returns all active custom providers for the authenticated user.

#### Get Custom Provider

```http
GET /api/v1/providers/custom/{provider_id}
```

#### Update Custom Provider

```http
PUT /api/v1/providers/custom/{provider_id}
```

Partial updates supported &mdash; only provided fields are modified. When `api_key` is provided, it is re-encrypted.

#### Delete Custom Provider

```http
DELETE /api/v1/providers/custom/{provider_id}
```

Immediate and irreversible; returns `204 No Content`.

### Test Connection

```http
POST /api/v1/providers/test?provider_id=my-provider&base_url=...&api_key=...
```

Prob es the `/v1/models` endpoint (or `/api/tags` for Ollama) and returns connection status, model list, and response time.

---

## 4-Tier Fallback Chain

The `generate_with_fallback()` function at `llm_service.py:552` implements a four-tier fallback that ensures maximum availability:

```
Tier 1: NVIDIA NIM
  ├── Key: resolve_user_api_key("nvidia") > settings.NVIDIA_API_KEY
  ├── Model: LLM_NVIDIA (from NVIDIA_MODEL)
  └── Circuit breaker: llm_nvidia

  └── On failure →

Tier 2: Groq
  ├── Key: resolve_user_api_key("groq") > settings.GROQ_API_KEY
  ├── Model: LLM_GROQ (from GROQ_MODEL)
  └── Circuit breaker: llm_groq

  └── On failure (rate-limit or configured) →

Tier 3: OpenRouter
  ├── Key: resolve_user_api_key("openrouter") > settings.OPENROUTER_API_KEY
  ├── Model: LLM_OPENROUTER (from OPENROUTER_MODEL)
  ├── Base URL: settings.OPENROUTER_API_BASE
  └── Circuit breaker: llm_openrouter

  └── On failure →

Tier 4: Ollama / DeepSeek (Local)
  ├── Key: None (local endpoint)
  ├── Model: ollama/deepseek-r1
  ├── Base URL: settings.OLLAMA_BASE_URL
  └── Circuit breaker: llm_ollama

  └── On failure →

Raise LLMUnavailableError → Caller uses rule-based heuristics
```

### Fallback Logic Details

- **Tier 1 (NVIDIA):** Always tried first if a key is available. If NVIDIA returns an empty response or raises, fall through to Tier 2.
- **Tier 2 (Groq):** Attempted when NVIDIA fails. If Groq's error is a **rate limit (429)**, Tier 3 (OpenRouter) is tried inside the Groq exception handler before proceeding to Tier 4.
- **Tier 3 (OpenRouter):** Also attempted as a direct jump when Groq has no key configured but OpenRouter does.
- **Tier 4 (Ollama/DeepSeek):** Final local fallback. Requires a running Ollama instance with `deepseek-r1` (or configured model).

### Circuit Breakers

Each provider in the fallback chain has an independent **circuit breaker** (`pybreaker`):

| Parameter | Env Var | Default |
| ----------- | --------- | --------- |
| Enable/Disable | `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | `True` |
| Failure Threshold | `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | 3 |
| Reset Timeout | `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` | 60s |

When a provider circuit breaker opens, all subsequent calls to that provider fail immediately with `RuntimeError("{provider} circuit breaker open")` until the reset timeout expires.

### Response Format

`generate_with_fallback()` returns:

```python
{
    "text": "Generated response text",
    "model": "nvidia_nim/meta/llama-3.3-70b-instruct",
    "tier": 1   # 1, 2, 3, or 4
}
```

When all tiers fail, it raises `LLMUnavailableError("All LLM tiers failed. Use rule-based fallback.")`.

---

## Model Selection

Models are selected through one of three paths:

### 1. Default Model (Fallback Chain)

The fallback chain uses predefined model constants from `llm_service.py:158-162`:

| Constant | Value | Provider |
| ---------- | ------- | ---------- |
| `LLM_NVIDIA` | `nvidia_nim/{NVIDIA_MODEL}` | NVIDIA NIM |
| `LLM_GROQ` | `groq/{GROQ_MODEL}` (or `groq/llama3-8b-8192`) | Groq |
| `LLM_OPENROUTER` | `openrouter/{OPENROUTER_MODEL}` (or `openrouter/openai/gpt-4o-mini`) | OpenRouter |
| `LLM_DEEPSEEK` | `ollama/deepseek-r1` | Ollama (local) |

### 2. User Preference (Per-Request Model)

`generate_with_model()` at `llm_service.py:425` takes a specific `model_name` parameter:

1. The model name is resolved to a provider via `resolve_model_provider()`
2. API key is resolved via `resolve_user_api_key()` (user key > env var)
3. Base URL is resolved from the provider definition (or custom provider record)
4. The request is sent via LiteLLM (or direct HTTP fallback)
5. The provider's circuit breaker wraps the call

### 3. Chat UI / API Model Selector

The frontend model dropdown fetches available models from `GET /api/v1/providers`, which returns all built-in and custom providers with their model lists:

```json
{
  "providers": [
    {
      "provider_id": "openai",
      "name": "OpenAI",
      "models": ["gpt-4o", "gpt-4o-mini", ...],
      "default_model": "gpt-4o-mini",
      "base_url": "https://api.openai.com/v1",
      "key_configured": true,
      "is_local": false,
      "is_custom": false
    },
    {
      "provider_id": "custom_abc-123",
      "name": "My vLLM",
      "models": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
      "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
      "base_url": "http://192.168.1.50:8000/v1",
      "key_configured": true,
      "is_local": false,
      "is_custom": true,
      "custom_provider_id": "abc-123"
    }
  ]
}
```

The `key_configured` field indicates whether a usable key exists (either via environment variable or the user's stored key).

---

## API Key Management

### Model (`api_key.py`)

| Field | Type | Default | Description |
| ------- | ------ | --------- | ------------- |
| `id` | UUID (PK) | auto | Unique key identifier |
| `user_id` | UUID | required | Owner |
| `provider` | String(50) | required | Provider name (lowercase) |
| `api_key_encrypted` | Text | required | Fernet-encrypted key value |
| `key_label` | String(100) | null | Human-readable label |
| `is_active` | Boolean | true | Soft-delete/enable flag |
| `rate_limit_per_minute` | Integer | 60 | Max requests per minute |
| `rate_limit_per_hour` | Integer | 1000 | Max requests per hour |
| `daily_quota` | Integer | 10000 | Max requests per day |
| `total_requests` | Integer | 0 | Lifetime request counter |
| `last_request_at` | DateTime | null | Last use timestamp |

### CRUD Endpoints

All under `/api/v1/keys`, authenticated, scoped to the requesting user.

| Method | Path | Description |
| -------- | ------ | ------------- |
| `POST` | `/api/v1/keys` | Create a new API key (encrypted immediately) |
| `GET` | `/api/v1/keys` | List all keys (filterable by `?provider=openai`) |
| `GET` | `/api/v1/keys/{id}` | Get key details (key value masked) |
| `PUT` | `/api/v1/keys/{id}` | Update label, active status, rate limits |
| `DELETE` | `/api/v1/keys/{id}` | Delete key (immediate, irreversible) |
| `GET` | `/api/v1/keys/usage` | Aggregate usage stats across all keys |
| `GET` | `/api/v1/keys/{id}/usage` | Per-key usage with current rate limit state |
| `POST` | `/api/v1/keys/test` | Test a key against its provider without storing |
| `GET` | `/api/v1/keys/providers` | List supported provider definitions |

### Key Masking

When returning keys via the API, the encrypted value is masked for security:

```python
# Full preview if key > 8 chars: "sk-...abcd"
# Otherwise: "****"
key_preview = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
```

Encrypted keys are never returned in their raw form &mdash; only the masked preview.

### Rate Limiting

Rate limits are enforced per API key via `ApiKeyRateLimiter`:

- Headers on every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- When exceeded: `429 Too Many Requests` with `Retry-After` header
- Default limits: 60/min, 1000/hr, 10000/day (configurable per key)

### Supported Provider Defaults

| Provider | RPM | RPH | Daily Quota |
| ---------- | ----- | ----- | ------------- |
| OpenAI | 60 | 1,000 | 10,000 |
| Anthropic | 50 | 800 | 8,000 |
| DeepSeek | 60 | 1,000 | 10,000 |
| Groq | 30 | 600 | 6,000 |
| Google AI | 60 | 1,000 | 10,000 |
| Cohere | 40 | 800 | 8,000 |
| Mistral | 60 | 1,000 | 10,000 |
| OpenRouter | 60 | 1,000 | 10,000 |
| NVIDIA NIM | 60 | 1,000 | 10,000 |

---

## Configuration Reference

### LLM API Keys

| Env Var | Required | Description |
| --------- | ---------- | ------------- |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `GROQ_API_KEY` | No | Groq API key |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key |
| `OPENROUTER_API_KEY` | No | OpenRouter API key |
| `GOOGLE_API_KEY` | No | Google AI API key |
| `COHERE_API_KEY` | No | Cohere API key |
| `MISTRAL_API_KEY` | No | Mistral API key |
| `NVIDIA_API_KEY` | No | NVIDIA NIM API key |

### Model Selection

| Env Var | Default | Description |
| --------- | --------- | ------------- |
| `NVIDIA_MODEL` | `""` | NVIDIA model string (e.g. `meta/llama-3.3-70b-instruct`) |
| `GROQ_MODEL` | `""` | Groq model override (default: `llama3-8b-8192`) |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | OpenRouter model override |

### Base URLs

| Env Var | Default | Description |
| --------- | --------- | ------------- |
| `GROQ_API_BASE` | `""` | Custom Groq API base URL |
| `OPENROUTER_API_BASE` | `https://openrouter.ai/api/v1` | OpenRouter API base URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_URL` | `""` | Alternative Ollama URL (legacy) |

### Request Timeouts

| Env Var | Default | Description |
|---------|---------|-------------|
| `LLM_PROVIDER_TIMEOUT_SECONDS` | `15` | Per-provider request timeout (3&ndash;60s range) |

### Circuit Breaker

| Env Var | Default | Description |
| --------- | --------- | ------------- |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | `True` | Enable/disable circuit breakers |
| `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `3` | Consecutive failures before opening |
| `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` | `60` | Seconds before attempting half-open |

### Caching

| Env Var | Default | Description |
|---------|---------|-------------|
| `LLM_CACHE_TTL_SECONDS` | `3600` | TTL for cached LLM responses (0 to disable) |

### Encryption

| Env Var | Required | Description |
|---------|----------|-------------|
| `ENCRYPTION_KEY` | Yes (for BYOK) | Fernet key for encrypting user API keys. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

### Advanced LLM Settings

| Env Var | Default | Description |
| --------- | --------- | ------------- |
| `ENABLE_NVIDIA_REASONER` | `False` | Enable NVIDIA reasoning model |
| `PRELOAD_AI_MODELS` | `True` | Preload AI models at startup |
| `VLLM_ADOPTION_ENABLED` | `True` | Enable vLLM auto-scaling logic |
| `VLLM_TARGET_MODEL` | `meta-llama/Meta-Llama-3.1-8B-Instruct` | vLLM deployment target |
| `VLLM_TARGET_GPU` | `L4 24GB` | GPU target for vLLM |
| `VLLM_REQUESTS_PER_HOUR_THRESHOLD` | `2000` | Hourly request threshold for vLLM auto-provision |
| `VLLM_DAILY_TOKENS_THRESHOLD` | `5,000,000` | Daily token threshold for vLLM auto-provision |

---

## Troubleshooting

### "No LLM available" / All tiers failed

1. **Check env vars**: Verify `NVIDIA_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY` are set correctly
2. **Check Ollama**: Ensure Ollama is running (`ollama serve`) and `deepseek-r1` is pulled (`ollama pull deepseek-r1`)
3. **Check circuit breakers**: If a provider recently failed 3+ times, its breaker may be open. Wait `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` (default 60s) or restart the service
4. **Test individual providers**: Use `GET /api/v1/providers/health` to see configured providers

### "API key not found" / 404 on keys

1. Verify you are authenticated as the correct user (keys are user-scoped)
2. Check that the key was created on the same provider (e.g., `openai` not `OpenAI`)
3. List all keys with `GET /api/v1/keys` to verify existence

### Key decryption failures

1. Ensure `ENCRYPTION_KEY` is set to the **same value** used when the key was created
2. Run `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and compare
3. Key rotation invalidates all existing encrypted keys &mdash; users must re-enter their API keys

### Custom provider connection failures

1. Verify the URL is reachable from the server (SSRF rules apply)
2. Ensure the endpoint is OpenAI-compatible (implements `/v1/models` and `/v1/chat/completions`)
3. Check that the `models` list in the custom provider matches actual model IDs served by the endpoint
4. Use `POST /api/v1/providers/test` to diagnose connectivity

### Rate limit exceeded (429)

1. Check `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers in responses
2. Increase limits via `PUT /api/v1/keys/{id}` with updated `rate_limit_per_minute`, `rate_limit_per_hour`, or `daily_quota`
3. Wait for the `Retry-After` period before retrying
4. Consider adding multiple keys for the same provider (round-robin not yet supported)
