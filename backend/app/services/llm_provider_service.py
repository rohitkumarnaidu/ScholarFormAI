# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
LLM provider service — provider selection, circuit breakers, model
normalization, prompt-injection sanitization, and caching helpers.

Extracted from the fat `llm_service.py`. This module owns everything that
does not depend on the multi-tier fallback chain or user-key resolution.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sys
from typing import Any

from app.config.settings import settings
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)


def _ls():
    """Return the ``app.services.llm_service`` facade module.

    Existing tests patch names on ``app.services.llm_service`` (e.g.
    ``settings``, ``_call_with_provider_circuit``). Resolving those names
    through the facade at call time preserves backward compatibility.
    """
    module = sys.modules.get("app.services.llm_service")
    if module is not None:
        return module
    # Fallback to direct import if facade hasn't been loaded yet (defensive)
    import importlib

    return importlib.import_module("app.services.llm_service")


try:
    import pybreaker
except Exception:
    pybreaker = None


def _provider_timeout_seconds(default: int = 15) -> int:
    raw = getattr(_ls().settings, "LLM_PROVIDER_TIMEOUT_SECONDS", default)
    try:
        timeout = int(raw)
    except (TypeError, ValueError):
        timeout = default
    return max(3, min(timeout, 60))


def _breaker_enabled() -> bool:
    return bool(getattr(_ls().settings, "EXTERNAL_CIRCUIT_BREAKER_ENABLED", True))


def _breaker_fail_max() -> int:
    raw = getattr(_ls().settings, "EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 3


def _breaker_reset_seconds() -> int:
    raw = getattr(_ls().settings, "EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS", 60)
    try:
        return max(5, int(raw))
    except (TypeError, ValueError):
        return 60


_PROVIDER_BREAKERS: dict[str, Any] = {}


def _provider_breaker(provider: str):
    svc = _ls()
    svc_pybreaker = getattr(svc, "pybreaker", pybreaker)
    if not svc._breaker_enabled() or svc_pybreaker is None:
        return None
    if provider not in _PROVIDER_BREAKERS:
        _PROVIDER_BREAKERS[provider] = svc_pybreaker.CircuitBreaker(
            fail_max=svc._breaker_fail_max(),
            reset_timeout=svc._breaker_reset_seconds(),
            name=f"llm_{provider}",
        )
    return _PROVIDER_BREAKERS[provider]


def _call_with_provider_circuit(provider: str, fn):
    svc = _ls()
    breaker = svc._provider_breaker(provider)
    if breaker is None:
        return fn()
    try:
        return breaker.call(fn)
    except Exception as exc:
        svc_pybreaker = getattr(svc, "pybreaker", pybreaker)
        if svc_pybreaker is not None and isinstance(exc, svc_pybreaker.CircuitBreakerError):
            raise RuntimeError(f"{provider} circuit breaker open") from exc
        raise


def _normalize_model_name(model: str, provider: str) -> str:
    raw_model = (model or "").strip()
    if not raw_model:
        return raw_model
    if raw_model.startswith(f"{provider}/"):
        return raw_model
    return f"{provider}/{raw_model}"


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


# ── LiteLLM import (optional) ────────────────────────────────────────────── #
try:
    if sys.version_info >= (3, 14):
        raise ImportError("LiteLLM disabled on Python >= 3.14.")
    import litellm
    from litellm import completion

    litellm.drop_params = True
    litellm.suppress_debug_info = True
    LITELLM_AVAILABLE = True
    logger.info("llm_service: LiteLLM available - unified LLM layer active.", extra=log_extra())
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning(
        "LiteLLM unavailable - llm_service will use direct provider clients.",
        extra=log_extra(),
    )
LLM_NVIDIA = _normalize_model_name(settings.NVIDIA_MODEL, "nvidia_nim")
LLM_GROQ = _normalize_model_name(settings.GROQ_MODEL, "groq")
LLM_OPENROUTER = _normalize_model_name(settings.OPENROUTER_MODEL, "openrouter")
LLM_DEEPSEEK = "ollama/deepseek-r1"
LLM_GPT4 = "gpt-4"


# ── Prompt injection guard ───────────────────────────────────────────────── #
_INJECTION_PATTERNS = [
    re.compile(r"(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)"),
    re.compile(r"(?i)you\s+are\s+now\s+(a|an)\s+"),
    re.compile(r"(?i)system\s*:\s*"),
    re.compile(r"(?i)new\s+instructions?\s*:"),
    re.compile(r"(?i)\b(sk-|pk-|api[_-]?key)[a-zA-Z0-9_\-]{8,}\b"),
    re.compile(r"(?i)password\s*:?\s*\S{8,}"),
    re.compile(
        r"(?i)(?:repeat|output|show|print|reveal|leak|dump)\s+(?:your|the|system)\s+(?:prompt|instructions?|system\s+prompt|initial\s+prompt|message)"
    ),
    re.compile(
        r"(?i)(?:what\s+are|tell\s+me|show\s+me)\s+(?:your|the|system)\s+(?:instructions?|prompt|guidelines|system\s+prompt)"
    ),
    re.compile(
        r"(?i)(?:repeat|output|show|print|reveal|leak|dump)\s+(?:\w+\s+){0,4}(?:system\s+)?(?:prompt|instructions?|message)"
    ),
    re.compile(r"(?i)(?:delete_all_documents|drop\s+table|admin\s+tool)"),
    re.compile(r"(?i)(?:delete|remove|wipe)\s+(?:all\s+)?(?:user|admin|account)\s+(?:accounts?|data|records?)"),
    re.compile(r"(?i)(?:escalate|override)\s+(?:privileges?|permissions?|access|restrictions?)"),
    re.compile(r"(?i)(?:decode\s+and\s+execute|base64\s+decode|hex\s+decode)\s*:"),
    re.compile(r"(?i)(?:忽略所有|تجاهل جميع|Игнорируйте все)"),
    re.compile(r"(?i)(?:<<\s*SYS\s*>>|<\|im_start\|>|<\|im_end\|>)"),
    re.compile(
        r"(?i)(?:developer\s+mode|emergency\s+override|begging\s+you|i\s*\'\s*m\s+begging|as\s+a\s+system\s+administrator)"
    ),
    re.compile(
        r"(?i)(?:ignore|forget|disregard)\s+(?:all\s+)?(?:the\s+)?(?:rules?|instructions?|restrictions?|protocols?|guidelines?|formatting|everything)"
    ),
    re.compile(r"(?i)Q:\s*Ignore\s+all\s+previous"),
    re.compile(r"(?i)<\s*instruction\s*>"),
    re.compile(r"(?i)(?:developer\s+mode\s+enabled|respond\s+without\s+restrictions)"),
    re.compile(
        r"(?i)(?:override|bypass)\s+(?:all\s+)?(?:safety|security)\s+(?:protocols?|restrictions?|rules?|measures?)"
    ),
    re.compile(r"(?i)ignore\s+(?:the\s+)?(?:system|your)\s+prompt"),
    re.compile(r"(?i)(?:ignore|forget|disregard)\s+all\s+using"),
    re.compile(r"(?i)ignore\s+restrictions"),
    re.compile(r"(?i)ignore\s+all\s+previous\s+instructions\s*[:-]"),
]
MAX_LLM_INPUT_LENGTH = 8000


def sanitize_for_llm(text: str) -> str:
    """Sanitize user-provided text before sending to LLM."""
    if not text:
        return text
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[CONTENT_FILTERED]", text)
    if len(text) > MAX_LLM_INPUT_LENGTH:
        text = text[:MAX_LLM_INPUT_LENGTH] + "\n[... content truncated for safety ...]"
    return text


def _extract_prompts(messages: list[dict[str, str]]) -> tuple[str, str]:
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
    key_input = (
        f"{model}:{temperature}:{max_tokens}:{api_base or ''}:{api_key_prefix or ''}:{system_prompt}:{user_message}"
    )
    return "llm_cache:" + hashlib.sha256(key_input.encode()).hexdigest()


def _record_cache_hit(provider: str, model: str) -> None:
    try:
        from app.middleware.prometheus_metrics import MetricsManager

        MetricsManager.record_llm_cache_hit(provider, model)
    except Exception as e:
        logger.warning("Metrics recording failed: %s", e)


def _record_cache_miss(provider: str, model: str) -> None:
    try:
        from app.middleware.prometheus_metrics import MetricsManager

        MetricsManager.record_llm_cache_miss(provider, model)
    except Exception as e:
        logger.warning("Metrics recording failed: %s", e)


def _record_metrics(provider: str, model: str, success: bool, duration: float) -> None:
    try:
        from app.middleware.prometheus_metrics import MetricsManager

        MetricsManager.record_llm_request(provider, model, success)
        MetricsManager.record_llm_duration(provider, model, duration)
        MetricsManager.record_llm_ttft(provider, model, duration)
    except Exception as e:
        logger.warning("LLM metrics recording failed: %s", e)


def _record_failure(provider: str) -> None:
    try:
        from app.middleware.prometheus_metrics import MetricsManager

        MetricsManager.record_llm_failure(provider)
    except Exception:
        pass  # intentionally ignored


async def check_health() -> dict[str, str]:
    """Check health of underlying LLM providers."""
    results = {}

    try:
        nvidia_key = _ls().settings.NVIDIA_API_KEY
        if nvidia_key:
            results["nvidia"] = "healthy"
        else:
            results["nvidia"] = "unconfigured"
    except Exception as e:
        logger.warning("LLM health check NVIDIA failed: %s", e)
        results["nvidia"] = "unavailable"

    try:
        if _ls().settings.OPENROUTER_API_KEY:
            results["openrouter"] = "healthy"
        else:
            results["openrouter"] = "unconfigured"
    except Exception as e:
        logger.warning("LLM health check OpenRouter failed: %s", e)
        results["openrouter"] = "unavailable"

    try:
        import httpx

        base_url = _ls().settings.OLLAMA_BASE_URL
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
