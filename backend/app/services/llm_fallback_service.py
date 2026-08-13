# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
LLM fallback service — request dispatch, the 4-tier fallback chain, and
direct-client fallbacks (no LiteLLM).

Extracted from the fat `llm_service.py`. Depends on
:mod:`app.services.llm_provider_service` for model normalization, circuit
breakers, caching, and sanitization; and on
:mod:`app.services.llm_key_service` for BYOK key resolution.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

from app.services.llm_provider_service import (
    LITELLM_AVAILABLE,
    LLM_DEEPSEEK,
    LLM_GROQ,
    LLM_NVIDIA,
    LLM_OPENROUTER,
    _cache_key,
    _extract_prompts,
    _infer_provider,
    _normalize_model_name,
    _provider_timeout_seconds,
    _record_cache_hit,
    _record_cache_miss,
    _record_failure,
    _record_metrics,
)
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)


def _llm_service_module():
    """Return the facade module so runtime patches on ``app.services.llm_service.*`` apply.

    The original monolithic ``llm_service`` exposed ``resolve_user_api_key`` and
    ``_call_with_provider_circuit`` as module-level names. Existing tests patch
    those names on ``app.services.llm_service``; resolving them via the facade at
    call time keeps that backward compatibility after decomposition.
    """
    return sys.modules["app.services.llm_service"]


def _settings():
    """Resolve ``settings`` through the facade so ``patch('app.services.llm_service.settings')`` applies."""
    return _llm_service_module().settings


class LLMUnavailableError(Exception):
    """Raised when all LLM tiers are exhausted."""

    pass


from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def generate(
    messages: list[dict[str, str]],
    model: str = LLM_NVIDIA,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    timeout: int | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    stream: bool = False,
) -> str:
    """Send a chat completion request via LiteLLM (or direct HTTP fallback)."""
    # Resolve config through facade so test patches on llm_service take effect
    svc = _llm_service_module()
    litellm_available = getattr(svc, "LITELLM_AVAILABLE", LITELLM_AVAILABLE)

    system_prompt, user_message = _extract_prompts(messages)
    api_key_prefix = None
    if api_key:
        api_key_prefix = api_key[:8] if len(api_key) > 8 else api_key
    key = _cache_key(
        system_prompt,
        user_message,
        model,
        temperature,
        max_tokens=max_tokens,
        api_base=api_base,
        api_key_prefix=api_key_prefix,
    )
    from app.cache.redis_cache import redis_cache

    cache_enabled = not stream
    provider = _infer_provider(model)
    if cache_enabled:
        cached = redis_cache.get_llm_result(key)
        if cached:
            _record_cache_hit(provider, model)
            logger.info("LLM cache hit", extra=log_extra())
            return cached
        _record_cache_miss(provider, model)
    start_time = time.perf_counter()
    request_success = False
    effective_timeout = int(timeout) if timeout is not None else _provider_timeout_seconds()

    try:
        if not litellm_available:
            svc_fallback = getattr(svc, "_generate_fallback", _generate_fallback)
            result = svc_fallback(
                messages,
                model,
                temperature,
                max_tokens,
                effective_timeout,
                api_key,
                api_base,
            )
            if result and cache_enabled:
                redis_cache.set_llm_result(key, result, ttl=_settings().LLM_CACHE_TTL_SECONDS)
            request_success = bool(result)
            return result

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": max(0.0, min(1.0, temperature)),
            "max_tokens": max_tokens,
            "timeout": effective_timeout,
        }

        if api_key:
            kwargs["api_key"] = api_key
        elif model.startswith("nvidia_nim/"):
            nvidia_key = _settings().NVIDIA_API_KEY
            if nvidia_key:
                kwargs["api_key"] = nvidia_key
        elif model.startswith("gpt-") or model.startswith("openai/"):
            openai_key = _settings().OPENAI_API_KEY
            if openai_key:
                kwargs["api_key"] = openai_key
        elif model.startswith("claude") or model.startswith("anthropic/"):
            anthropic_key = _settings().ANTHROPIC_API_KEY
            if anthropic_key:
                kwargs["api_key"] = anthropic_key
        elif model.startswith("groq/"):
            groq_key = _settings().GROQ_API_KEY
            if groq_key:
                kwargs["api_key"] = groq_key
        elif model.startswith("openrouter/"):
            openrouter_key = _settings().OPENROUTER_API_KEY
            if openrouter_key:
                kwargs["api_key"] = openrouter_key

        if api_base:
            kwargs["api_base"] = api_base
        elif model.startswith("ollama/"):
            kwargs["api_base"] = _settings().OLLAMA_BASE_URL
        elif model.startswith("groq/"):
            kwargs["api_base"] = _settings().GROQ_API_BASE
        elif model.startswith("openrouter/"):
            kwargs["api_base"] = _settings().OPENROUTER_API_BASE

        from litellm import completion

        response = completion(**kwargs)
        choices = response.choices
        if not choices:
            logger.warning("llm_service.generate: empty choices from %s", model, extra=log_extra())
            return ""
        text = choices[0].message.content or ""
        if text and cache_enabled:
            redis_cache.set_llm_result(key, text, ttl=_settings().LLM_CACHE_TTL_SECONDS)
        request_success = bool(text)
        return text
    finally:
        duration = time.perf_counter() - start_time
        _record_metrics(provider, model, request_success, duration)


def generate_with_model(
    messages: list[dict[str, str]],
    model_name: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Generate a response using a specific model (not using fallback)."""
    _ls = _llm_service_module()
    _resolve_key = _ls.resolve_user_api_key
    _circuit = _ls._call_with_provider_circuit
    _generate = _ls.generate

    from app.services.provider_registry import get_provider_info, resolve_model_provider

    provider = resolve_model_provider(model_name)
    if not provider:
        raise LLMUnavailableError(f"Unknown model: {model_name}")

    is_custom = provider.startswith("custom_")
    api_key = _resolve_key(provider, user_id) if not is_custom else None

    provider_info = get_provider_info(provider) if not is_custom else None

    kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if is_custom:
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.custom_provider import CustomProvider

        custom_id = provider.replace("custom_", "")
        with SessionLocal() as db:
            cp = db.execute(select(CustomProvider).where(CustomProvider.id == custom_id)).scalar_one_or_none()
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

        text = _ls._generate_openai_compat(**kwargs)
        return {"text": text, "model": model_name, "provider": provider}

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
        text = _circuit(
            provider,
            lambda: _generate(**kwargs),
        )
        if text:
            return {"text": text, "model": model, "provider": provider}
        raise LLMUnavailableError(f"{provider} returned empty response")
    except Exception as exc:
        _record_failure(provider)
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
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    user_id: str | None = None,
) -> dict[str, Any]:
    """4-step fallback contract: NVIDIA -> Groq -> OpenRouter -> Ollama/DeepSeek."""
    _lsm = _llm_service_module()
    _resolve_key = _lsm.resolve_user_api_key
    _circuit = _lsm._call_with_provider_circuit
    _generate = _lsm.generate

    def _is_rate_limit_error(exc: Exception) -> bool:
        raw = str(exc).lower()
        return ("429" in raw) or ("rate limit" in raw) or ("too many requests" in raw)

    provider_timeout = _provider_timeout_seconds()

    nvidia_key = _resolve_key("nvidia", user_id) or _settings().NVIDIA_API_KEY
    if nvidia_key:
        try:
            text = _circuit(
                "nvidia",
                lambda: _generate(
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
            _record_failure("nvidia")
            logger.warning("llm_service: Tier 1 (NVIDIA) failed: %s - trying Groq.", exc, extra=log_extra())

    groq_model = LLM_GROQ
    groq_key = _resolve_key("groq", user_id) or _settings().GROQ_API_KEY
    if groq_key:
        try:
            text = _circuit(
                "groq",
                lambda: _generate(
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
            _record_failure("groq")
            logger.warning("llm_service: Tier 2 (Groq) failed: %s - trying Ollama.", exc, extra=log_extra())

            openrouter_key = _resolve_key("openrouter", user_id) or _settings().OPENROUTER_API_KEY
            if openrouter_key and (_is_rate_limit_error(exc) or not _settings().GROQ_API_KEY):
                try:
                    text = _circuit(
                        "openrouter",
                        lambda: _generate(
                            messages,
                            model=LLM_OPENROUTER,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            api_key=openrouter_key,
                            api_base=_settings().OPENROUTER_API_BASE,
                            timeout=provider_timeout,
                        ),
                    )
                    if text:
                        logger.info("llm_service: Tier 3 (OpenRouter) succeeded.", extra=log_extra())
                        return {"text": text, "model": LLM_OPENROUTER, "tier": 3}
                except Exception as openrouter_exc:
                    _record_failure("openrouter")
                    logger.warning(
                        "llm_service: Tier 3 (OpenRouter) failed: %s - trying Ollama.",
                        openrouter_exc,
                        extra=log_extra(),
                    )
    elif _resolve_key("openrouter", user_id) or _settings().OPENROUTER_API_KEY:
        openrouter_key = _resolve_key("openrouter", user_id) or _settings().OPENROUTER_API_KEY
        try:
            text = _circuit(
                "openrouter",
                lambda: _generate(
                    messages,
                    model=LLM_OPENROUTER,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=openrouter_key,
                    api_base=_settings().OPENROUTER_API_BASE,
                    timeout=provider_timeout,
                ),
            )
            if text:
                logger.info("llm_service: Tier 3 (OpenRouter) succeeded.", extra=log_extra())
                return {"text": text, "model": LLM_OPENROUTER, "tier": 3}
        except Exception as openrouter_exc:
            _record_failure("openrouter")
            logger.warning(
                "llm_service: Tier 3 (OpenRouter) failed: %s - trying Ollama.", openrouter_exc, extra=log_extra()
            )

    try:
        text = _circuit(
            "ollama",
            lambda: _generate(
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
        _record_failure("ollama")
        logger.warning("llm_service: Tier 4 (Ollama) failed: %s - no LLM available.", exc, extra=log_extra())

    raise LLMUnavailableError("All LLM tiers failed. Use rule-based fallback.")


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
        logger.info("LLM cache invalidated for pattern=%s (removed=%s)", pattern, removed, extra=log_extra())
    except Exception as exc:
        logger.error("LLM cache invalidation failed for pattern=%s: %s", pattern, exc, extra=log_extra())
    return removed


# ── Direct-client fallback (no litellm) ─────────────────────────────────── #
def _generate_fallback(messages, model, temperature, max_tokens, timeout, api_key, api_base) -> str:
    # Resolve through facade so test patches on llm_service._openai_compat apply
    svc = _llm_service_module()
    compat = getattr(svc, "_openai_compat", _openai_compat)
    ollama_http_fn = getattr(svc, "_ollama_http", _ollama_http)

    if model.startswith("nvidia_nim/") or model.startswith("openai/") or model.startswith("gpt-"):
        return compat(
            messages,
            model,
            temperature,
            max_tokens,
            api_key or _settings().NVIDIA_API_KEY or _settings().OPENAI_API_KEY,
            api_base or ("https://integrate.api.nvidia.com/v1" if model.startswith("nvidia_nim/") else None),
        )
    elif model.startswith("groq/"):
        return compat(
            messages,
            model,
            temperature,
            max_tokens,
            api_key or _settings().GROQ_API_KEY,
            api_base or _settings().GROQ_API_BASE,
        )
    elif model.startswith("openrouter/"):
        return compat(
            messages,
            model,
            temperature,
            max_tokens,
            api_key or _settings().OPENROUTER_API_KEY,
            api_base or _settings().OPENROUTER_API_BASE,
        )
    elif model.startswith("ollama/"):
        return ollama_http_fn(
            messages,
            model.replace("ollama/", ""),
            temperature,
            max_tokens,
            api_base or _settings().OLLAMA_BASE_URL,
            timeout,
        )
    raise NotImplementedError(f"No fallback implementation for model: {model}")


def _openai_compat(messages, model, temperature, max_tokens, api_key, base_url) -> str:
    from openai import OpenAI

    raw_model = model.replace("nvidia_nim/", "").replace("openai/", "").replace("groq/", "").replace("openrouter/", "")
    client = OpenAI(api_key=api_key or "none", base_url=base_url)
    resp = client.chat.completions.create(
        model=raw_model,
        messages=messages,
        temperature=max(0.0, min(1.0, temperature)),
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or "" if resp.choices else ""


def _ollama_http(messages, model_name, temperature, max_tokens, base_url, timeout) -> str:
    import requests

    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    resp = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")
