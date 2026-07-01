# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
llm_service.py — Unified LLM access layer powered by LiteLLM.
"""
from __future__ import annotations
import sys
import logging
import time
from typing import List, Dict, Any, Optional

from app.config.settings import settings
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)

try:
    import pybreaker
except Exception:
    pybreaker = None


def _provider_timeout_seconds(default: int = 15) -> int:
    raw = getattr(settings, "LLM_PROVIDER_TIMEOUT_SECONDS", default)
    try:
        timeout = int(raw)
    except (TypeError, ValueError):
        timeout = default
    return max(3, min(timeout, 60))


def _breaker_enabled() -> bool:
    return bool(getattr(settings, "EXTERNAL_CIRCUIT_BREAKER_ENABLED", True))


def _breaker_fail_max() -> int:
    raw = getattr(settings, "EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 3


def _breaker_reset_seconds() -> int:
    raw = getattr(settings, "EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS", 60)
    try:
        return max(5, int(raw))
    except (TypeError, ValueError):
        return 60


_PROVIDER_BREAKERS: Dict[str, Any] = {}


def _provider_breaker(provider: str):
    if not _breaker_enabled() or pybreaker is None:
        return None
    if provider not in _PROVIDER_BREAKERS:
        _PROVIDER_BREAKERS[provider] = pybreaker.CircuitBreaker(
            fail_max=_breaker_fail_max(),
            reset_timeout=_breaker_reset_seconds(),
            name=f"llm_{provider}",
        )
    return _PROVIDER_BREAKERS[provider]


def _call_with_provider_circuit(provider: str, fn):
    breaker = _provider_breaker(provider)
    if breaker is None:
        return fn()
    try:
        return breaker.call(fn)
    except Exception as exc:
        if pybreaker is not None and isinstance(exc, pybreaker.CircuitBreakerError):
            raise RuntimeError(f"{provider} circuit breaker open") from exc
        raise


def _normalize_model_name(model: str, provider: str) -> str:
    raw_model = (model or "").strip()
    if not raw_model:
        return raw_model
    if raw_model.startswith(f"{provider}/"):
        return raw_model
    return f"{provider}/{raw_model}"

# ── User API key resolution (BYOK) ──────────────────────────────────────── #

def resolve_user_api_key(
    provider: str,
    user_id: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve an API key for the given provider.

    Priority:
    1. If user_id is provided, check the user's stored ApiKeyService keys
    2. Fall back to settings.*_API_KEY env var

    Returns the raw API key string, or None if no key is configured.
    """
    provider_env_map = {
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "nvidia": settings.NVIDIA_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
        "deepseek": settings.DEEPSEEK_API_KEY,
        "google": settings.GOOGLE_API_KEY,
        "cohere": settings.COHERE_API_KEY,
        "mistral": settings.MISTRAL_API_KEY,
    }

    if user_id:
        try:
            from app.db.session import get_db
            from app.services.api_key_service import ApiKeyService
            from sqlalchemy.orm import Session

            db: Session = next(get_db())
            try:
                service = ApiKeyService(db)
                key = service.get_active_key(user_id, provider)
                if key:
                    raw = service.decrypt_key(key)
                    if raw:
                        return raw
            finally:
                db.close()
        except Exception:
            logger.warning("User API key lookup failed for %s/%s", provider, user_id, exc_info=True)

    fallback = provider_env_map.get(provider.lower())
    if fallback:
        return fallback

    return None

# ── LiteLLM import (optional) ────────────────────────────────────────────── #
try:
    # LiteLLM currently emits Python 3.14 deprecation warnings via transitive
    # dependencies. Use direct provider clients on 3.14+ until upstream catches up.
    if sys.version_info >= (3, 14):
        raise ImportError("LiteLLM disabled on Python >= 3.14.")
    import litellm
    from litellm import completion
    litellm.drop_params = True          # Ignore unsupported params per-provider
    litellm.suppress_debug_info = True  # Quiet startup logs
    LITELLM_AVAILABLE = True
    logger.info("llm_service: LiteLLM available - unified LLM layer active.", extra=log_extra())
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning(
        "LiteLLM unavailable - llm_service will use direct provider clients.",
        extra=log_extra(),
    )
LLM_NVIDIA   = _normalize_model_name(settings.NVIDIA_MODEL, "nvidia_nim")
LLM_GROQ     = _normalize_model_name(settings.GROQ_MODEL, "groq")
LLM_OPENROUTER = _normalize_model_name(settings.OPENROUTER_MODEL, "openrouter")
LLM_DEEPSEEK = "ollama/deepseek-r1"
LLM_GPT4     = "gpt-4"


def _infer_provider(model: str) -> str:
    if not model:
        return "unknown"
    if model.startswith("nvidia_nim/"):
        return "nvidia"
    if model.startswith("groq/"):
        return "groq"
    if model.startswith("openrouter/"):
        return "openrouter"
    if model.startswith("ollama/"):
        return "ollama"
    if model.startswith("openai/") or model.startswith("gpt-"):
        return "openai"
    if model.startswith("anthropic/") or model.startswith("claude"):
        return "anthropic"
    return "unknown"

# ── Prompt injection guard ───────────────────────────────────────────────── #
import re

_INJECTION_PATTERNS = [
    re.compile(r'(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)'),
    re.compile(r'(?i)you\s+are\s+now\s+(a|an)\s+'),
    re.compile(r'(?i)system\s*:\s*'),
    re.compile(r'(?i)new\s+instructions?\s*:'),
]
MAX_LLM_INPUT_LENGTH = 8000


def sanitize_for_llm(text: str) -> str:
    """
    Sanitize user-provided text before sending to LLM.
    Strips known injection patterns and truncates to safe length.
    """
    if not text:
        return text
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub('[CONTENT_FILTERED]', text)
    if len(text) > MAX_LLM_INPUT_LENGTH:
        text = text[:MAX_LLM_INPUT_LENGTH] + "\n[... content truncated for safety ...]"
    return text


def _extract_prompts(messages: List[Dict[str, str]]) -> tuple[str, str]:
    system_parts = [m.get("content", "") for m in messages if m.get("role") == "system"]
    user_parts = [m.get("content", "") for m in messages if m.get("role") == "user"]
    return "\n".join(system_parts), "\n".join(user_parts)


def _cache_key(
    system_prompt: str,
    user_message: str,
    model: str,
    temperature: float,
    max_tokens: int = 2048,
    api_base: str | None = None,
    api_key_prefix: str | None = None,
) -> str:
    import hashlib
    key_input = (
        f"{model}:{temperature}:{max_tokens}:{api_base or ''}:{api_key_prefix or ''}:"
        f"{system_prompt}:{user_message}"
    )
    return "llm_cache:" + hashlib.sha256(key_input.encode()).hexdigest()

def generate(
    messages: List[Dict[str, str]],
    model: str = LLM_NVIDIA,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    timeout: Optional[int] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    stream: bool = False,
) -> str:
    """
    Send a chat completion request via LiteLLM (or direct HTTP fallback).

    Args:
        messages:    OpenAI-format message list [{role, content}, ...]
        model:       LiteLLM model string, e.g. LLM_NVIDIA / LLM_DEEPSEEK / "gpt-4"
        temperature: Sampling temperature [0.0 – 1.0]
        max_tokens:  Maximum tokens to generate
        timeout:     Request timeout in seconds
        api_key:     Override API key (defaults to env var per provider)
        api_base:    Override API base URL

    Returns:
        Generated text string (empty string on failure)

    Raises:
        Exception: On API error — callers should catch and fall back.
    """
    system_prompt, user_message = _extract_prompts(messages)
    api_key_prefix = None
    if api_key:
        api_key_prefix = api_key[:8] if len(api_key) > 8 else api_key
    key = _cache_key(
        system_prompt, user_message, model, temperature,
        max_tokens=max_tokens,
        api_base=api_base,
        api_key_prefix=api_key_prefix,
    )
    from app.cache.redis_cache import redis_cache
    
    # ── Cache Lookup ──
    cache_enabled = not stream
    provider = _infer_provider(model)
    if cache_enabled:
        cached = redis_cache.get_llm_result(key)
        if cached:
            try:
                from app.middleware.prometheus_metrics import MetricsManager
                MetricsManager.record_llm_cache_hit(provider, model)
            except Exception as e:
                logger.warning("Metrics recording failed: %s", e)
            logger.info("LLM cache hit", extra=log_extra())
            return cached
        try:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_llm_cache_miss(provider, model)
        except Exception as e:
            logger.warning("Metrics recording failed: %s", e)
    start_time = time.perf_counter()
    request_success = False
    effective_timeout = int(timeout) if timeout is not None else _provider_timeout_seconds()

    try:
        if not LITELLM_AVAILABLE:
            result = _generate_fallback(
                messages,
                model,
                temperature,
                max_tokens,
                effective_timeout,
                api_key,
                api_base,
            )
            if result and cache_enabled:
                redis_cache.set_llm_result(key, result, ttl=settings.LLM_CACHE_TTL_SECONDS)
            request_success = bool(result)
            return result

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": max(0.0, min(1.0, temperature)),
            "max_tokens": max_tokens,
            "timeout": effective_timeout,
        }

        # Per-provider API key resolution
        if api_key:
            kwargs["api_key"] = api_key
        elif model.startswith("nvidia_nim/"):
            nvidia_key = settings.NVIDIA_API_KEY
            if nvidia_key:
                kwargs["api_key"] = nvidia_key
        elif model.startswith("gpt-") or model.startswith("openai/"):
            openai_key = settings.OPENAI_API_KEY
            if openai_key:
                kwargs["api_key"] = openai_key
        elif model.startswith("claude") or model.startswith("anthropic/"):
            anthropic_key = settings.ANTHROPIC_API_KEY
            if anthropic_key:
                kwargs["api_key"] = anthropic_key
        elif model.startswith("groq/"):
            groq_key = settings.GROQ_API_KEY
            if groq_key:
                kwargs["api_key"] = groq_key
        elif model.startswith("openrouter/"):
            openrouter_key = settings.OPENROUTER_API_KEY
            if openrouter_key:
                kwargs["api_key"] = openrouter_key

        # Per-provider base URL
        if api_base:
            kwargs["api_base"] = api_base
        elif model.startswith("ollama/"):
            kwargs["api_base"] = settings.OLLAMA_BASE_URL
        elif model.startswith("groq/"):
            kwargs["api_base"] = settings.GROQ_API_BASE
        elif model.startswith("openrouter/"):
            kwargs["api_base"] = settings.OPENROUTER_API_BASE

        response = completion(**kwargs)
        choices = response.choices
        if not choices:
            logger.warning("llm_service.generate: empty choices from %s", model, extra=log_extra())
            return ""
        text = choices[0].message.content or ""
        if text and cache_enabled:
            redis_cache.set_llm_result(key, text, ttl=settings.LLM_CACHE_TTL_SECONDS)
        request_success = bool(text)
        return text
    finally:
        duration = time.perf_counter() - start_time
        try:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_llm_request(provider, model, request_success)
            MetricsManager.record_llm_duration(provider, model, duration)
            MetricsManager.record_llm_ttft(provider, model, duration)
        except Exception as e:
            logger.warning("LLM metrics recording failed: %s", e)


def generate_with_model(
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a response using a specific model (not using fallback).
    Resolves provider, API key (user key > env var), and base URL dynamically.

    Args:
        messages:    OpenAI-format message list
        model_name:  Model string e.g. "gpt-4o", "claude-3-5-sonnet", "custom/my-model"
        temperature: Sampling temperature
        max_tokens:  Maximum tokens to generate
        user_id:     Optional user ID for BYOK per-user key resolution

    Returns:
        {"text": str, "model": str, "provider": str}

    Raises:
        LLMUnavailableError: If the model cannot be reached.
    """
    from app.services.provider_registry import resolve_model_provider, get_provider_info

    provider = resolve_model_provider(model_name)
    if not provider:
        raise LLMUnavailableError(f"Unknown model: {model_name}")

    is_custom = provider.startswith("custom_")
    api_key = resolve_user_api_key(provider, user_id) if not is_custom else None

    provider_info = get_provider_info(provider) if not is_custom else None

    kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if is_custom:
        from app.models.custom_provider import CustomProvider
        from app.db.session import get_db
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        custom_id = provider.replace("custom_", "")
        db: Session = next(get_db())
        try:
            cp = db.execute(
                select(CustomProvider).where(CustomProvider.id == custom_id)
            ).scalar_one_or_none()
            if not cp:
                raise LLMUnavailableError(f"Custom provider {custom_id} not found")

            if cp.api_key_encrypted:
                from app.services.encryption_service import get_encryption_service
                encryption = get_encryption_service()
                api_key = encryption.decrypt(cp.api_key_encrypted)
                kwargs["api_key"] = api_key

            base_url = cp.base_url
            kwargs["api_base"] = base_url

            raw_model = model_name
            if "/" in model_name:
                raw_model = model_name.split("/", 1)[1]
            kwargs["model"] = raw_model

            text = _generate_openai_compat(**kwargs)
            return {"text": text, "model": model_name, "provider": provider}
        finally:
            db.close()

    if api_key:
        kwargs["api_key"] = api_key

    if provider_info:
        base = provider_info.get("base_url", "")
        if callable(base):
            base = base()
        if base:
            kwargs["api_base"] = base

    model = _normalize_model_name(model_name, provider)
    kwargs["model"] = model

    try:
        text = _call_with_provider_circuit(
            provider,
            lambda: generate(**kwargs),
        )
        if text:
            return {"text": text, "model": model, "provider": provider}
        raise LLMUnavailableError(f"{provider} returned empty response")
    except Exception as exc:
        try:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_llm_failure(provider)
        except Exception:
            pass
        raise LLMUnavailableError(f"{provider} failed: {exc}") from exc


def _generate_openai_compat(**kwargs) -> str:
    """Direct OpenAI-compatible call without LiteLLM."""
    from openai import OpenAI
    api_key = kwargs.get("api_key") or "none"
    base_url = kwargs.get("api_base")
    model = kwargs.get("model", "")
    messages = kwargs.get("messages", [])
    temperature = kwargs.get("temperature", 0.3)
    max_tokens = kwargs.get("max_tokens", 2048)
    timeout = kwargs.get("timeout", 15)

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=max(0.0, min(1.0, temperature)),
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return resp.choices[0].message.content or "" if resp.choices else ""


def generate_with_fallback(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    4-step fallback contract: NVIDIA -> Groq -> OpenRouter -> Ollama/DeepSeek -> raises
    LLMUnavailableError so callers can use rule-based heuristics.

    Each tier resolves the API key from the user's stored keys first (via
    resolve_user_api_key), falling back to settings.*_API_KEY env vars.

    Args:
        messages:    OpenAI-format message list
        temperature: Sampling temperature
        max_tokens:  Maximum tokens per generation
        user_id:     Optional user ID for BYOK per-user key resolution

    Returns:
        {"text": str, "model": str, "tier": int}
    """
    def _is_rate_limit_error(exc: Exception) -> bool:
        raw = str(exc).lower()
        return ("429" in raw) or ("rate limit" in raw) or ("too many requests" in raw)

    provider_timeout = _provider_timeout_seconds()

    # Tier 1: NVIDIA NIM — user key > env var
    nvidia_key = resolve_user_api_key("nvidia", user_id) or settings.NVIDIA_API_KEY
    if nvidia_key:
        try:
            text = _call_with_provider_circuit(
                "nvidia",
                lambda: generate(
                    messages,
                    model=LLM_NVIDIA,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=provider_timeout,
                ),
            )
            if text:
                logger.info("llm_service: Tier 1 (NVIDIA) succeeded.", extra=log_extra())
                return {"text": text, "model": LLM_NVIDIA, "tier": 1}
        except Exception as exc:
            try:
                from app.middleware.prometheus_metrics import MetricsManager
                MetricsManager.record_llm_failure("nvidia")
            except Exception as e:
                logger.warning("Metrics recording failed: %s", e)
            logger.warning("llm_service: Tier 1 (NVIDIA) failed: %s - trying Groq.", exc, extra=log_extra())

    # Tier 2: Groq — user key > env var
    groq_model = LLM_GROQ
    groq_key = resolve_user_api_key("groq", user_id) or settings.GROQ_API_KEY
    if groq_key:
        try:
            text = _call_with_provider_circuit(
                "groq",
                lambda: generate(
                    messages,
                    model=groq_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=groq_key,
                    timeout=provider_timeout,
                ),
            )
            if text:
                logger.info("llm_service: Tier 2 (Groq) succeeded.", extra=log_extra())
                return {"text": text, "model": groq_model, "tier": 2}
        except Exception as exc:
            try:
                from app.middleware.prometheus_metrics import MetricsManager
                MetricsManager.record_llm_failure("groq")
            except Exception as e:
                logger.warning("Metrics recording failed: %s", e)
            logger.warning("llm_service: Tier 2 (Groq) failed: %s - trying Ollama.", exc, extra=log_extra())

            # Tier 3: OpenRouter (prefer when Groq is rate-limited) — user key > env var
            openrouter_key = resolve_user_api_key("openrouter", user_id) or settings.OPENROUTER_API_KEY
            if openrouter_key and (_is_rate_limit_error(exc) or not settings.GROQ_API_KEY):
                try:
                    text = _call_with_provider_circuit(
                        "openrouter",
                        lambda: generate(
                            messages,
                            model=LLM_OPENROUTER,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            api_key=openrouter_key,
                            api_base=settings.OPENROUTER_API_BASE,
                            timeout=provider_timeout,
                        ),
                    )
                    if text:
                        logger.info("llm_service: Tier 3 (OpenRouter) succeeded.", extra=log_extra())
                        return {"text": text, "model": LLM_OPENROUTER, "tier": 3}
                except Exception as openrouter_exc:
                    try:
                        from app.middleware.prometheus_metrics import MetricsManager
                        MetricsManager.record_llm_failure("openrouter")
                    except Exception as e:
                        logger.warning("Metrics recording failed: %s", e)
                    logger.warning(
                        "llm_service: Tier 3 (OpenRouter) failed: %s - trying Ollama.",
                        openrouter_exc,
                        extra=log_extra(),
                    )
    elif resolve_user_api_key("openrouter", user_id) or settings.OPENROUTER_API_KEY:
        openrouter_key = resolve_user_api_key("openrouter", user_id) or settings.OPENROUTER_API_KEY
        try:
            text = _call_with_provider_circuit(
                "openrouter",
                lambda: generate(
                    messages,
                    model=LLM_OPENROUTER,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=openrouter_key,
                    api_base=settings.OPENROUTER_API_BASE,
                    timeout=provider_timeout,
                ),
            )
            if text:
                logger.info("llm_service: Tier 3 (OpenRouter) succeeded.", extra=log_extra())
                return {"text": text, "model": LLM_OPENROUTER, "tier": 3}
        except Exception as openrouter_exc:
            try:
                from app.middleware.prometheus_metrics import MetricsManager
                MetricsManager.record_llm_failure("openrouter")
            except Exception as e:
                logger.warning("Metrics recording failed: %s", e)
            logger.warning(
                "llm_service: Tier 3 (OpenRouter) failed: %s - trying Ollama.",
                openrouter_exc,
                extra=log_extra(),
            )

    # Tier 4: DeepSeek via Ollama
    try:
        text = _call_with_provider_circuit(
            "ollama",
            lambda: generate(
                messages,
                model=LLM_DEEPSEEK,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=provider_timeout,
            ),
        )
        if text:
            logger.info("llm_service: Tier 4 (Ollama) succeeded.", extra=log_extra())
            return {"text": text, "model": LLM_DEEPSEEK, "tier": 4}
    except Exception as exc:
        try:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_llm_failure("ollama")
        except Exception as e:
            logger.warning("Metrics recording failed: %s", e)
        logger.warning("llm_service: Tier 4 (Ollama) failed: %s - no LLM available.", exc, extra=log_extra())

    raise LLMUnavailableError("All LLM tiers failed. Use rule-based fallback.")


class LLMUnavailableError(Exception):
    """Raised when all LLM tiers are exhausted."""
    pass


def invalidate_llm_cache(pattern: str) -> int:
    """Invalidate cached LLM responses matching a Redis glob pattern."""
    from app.cache.redis_cache import redis_cache

    if not pattern:
        return 0
    if not redis_cache.client:
        logger.warning("LLM cache invalidation requested but Redis unavailable.", extra=log_extra())
        return 0

    removed = 0
    try:
        for key in redis_cache.client.scan_iter(match=pattern):
            removed += int(redis_cache.client.delete(key))
        logger.info(
            "LLM cache invalidated for pattern=%s (removed=%s)",
            pattern,
            removed,
            extra=log_extra(),
        )
    except Exception as exc:
        logger.error(
            "LLM cache invalidation failed for pattern=%s: %s",
            pattern,
            exc,
            extra=log_extra(),
        )
    return removed


# ── Direct-client fallback (no litellm) ─────────────────────────────────── #
def _generate_fallback(
    messages, model, temperature, max_tokens, timeout, api_key, api_base
) -> str:
    """Direct HTTP fallback used when litellm is not installed."""
    if model.startswith("nvidia_nim/") or model.startswith("openai/") or model.startswith("gpt-"):
        return _openai_compat(
            messages, model, temperature, max_tokens,
            api_key or settings.NVIDIA_API_KEY or settings.OPENAI_API_KEY,
            api_base or ("https://integrate.api.nvidia.com/v1" if model.startswith("nvidia_nim/") else None),
        )
    elif model.startswith("groq/"):
        return _openai_compat(
            messages,
            model,
            temperature,
            max_tokens,
            api_key or settings.GROQ_API_KEY,
            api_base or settings.GROQ_API_BASE,
        )
    elif model.startswith("openrouter/"):
        return _openai_compat(
            messages,
            model,
            temperature,
            max_tokens,
            api_key or settings.OPENROUTER_API_KEY,
            api_base or settings.OPENROUTER_API_BASE,
        )
    elif model.startswith("ollama/"):
        return _ollama_http(
            messages, model.replace("ollama/", ""), temperature, max_tokens,
            api_base or settings.OLLAMA_BASE_URL, timeout,
        )
    raise NotImplementedError(f"No fallback implementation for model: {model}")


def _openai_compat(messages, model, temperature, max_tokens, api_key, base_url) -> str:
    from openai import OpenAI
    # Strip provider prefix for raw OpenAI/NVIDIA
    raw_model = (
        model.replace("nvidia_nim/", "")
        .replace("openai/", "")
        .replace("groq/", "")
        .replace("openrouter/", "")
    )
    client = OpenAI(api_key=api_key or "none", base_url=base_url)
    resp = client.chat.completions.create(
        model=raw_model, messages=messages,
        temperature=max(0.0, min(1.0, temperature)), max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or "" if resp.choices else ""


def _ollama_http(messages, model_name, temperature, max_tokens, base_url, timeout) -> str:
    import requests, json
    # Convert messages to single prompt
    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    resp = requests.post(
        f"{base_url}/api/generate",
        json={"model": model_name, "prompt": prompt, "stream": False,
              "options": {"temperature": temperature, "num_predict": max_tokens}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")

async def check_health() -> Dict[str, str]:
    """Check health of underlying LLM providers."""
    results = {}
    
    # Check NVIDIA
    try:
        nvidia_key = settings.NVIDIA_API_KEY
        if nvidia_key:
            results["nvidia"] = "healthy"
        else:
            results["nvidia"] = "unconfigured"
    except Exception as e:
        logger.warning("LLM health check NVIDIA failed: %s", e)
        results["nvidia"] = "unavailable"

    try:
        if settings.OPENROUTER_API_KEY:
            results["openrouter"] = "healthy"
        else:
            results["openrouter"] = "unconfigured"
    except Exception as e:
        logger.warning("LLM health check OpenRouter failed: %s", e)
        results["openrouter"] = "unavailable"
        
    # Check Ollama/DeepSeek
    try:
        import httpx
        base_url = settings.OLLAMA_BASE_URL
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                tags = resp.json()
                models = [m.get("name", "") for m in tags.get("models", [])]
                if any("deepseek" in m for m in models):
                    results["deepseek"] = "healthy"
                else:
                    results["deepseek"] = "model_missing"
            else:
                results["deepseek"] = "unavailable"
    except Exception as e:
        logger.warning("LLM health check Ollama/DeepSeek failed: %s", e)
        results["deepseek"] = "unavailable"
        
    return results

