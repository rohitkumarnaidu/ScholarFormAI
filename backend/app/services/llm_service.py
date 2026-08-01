# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
llm_service.py — Unified LLM access layer.

Provides a clean public API over the decomposed LLM services:

    generate()              — Single prompt completion
    generate_with_model()   — Specific model completion
    generate_with_fallback()— 4-tier fallback chain
    sanitize_for_llm()      — Prompt injection guard
    check_health()          — Provider health status
    resolve_user_api_key()  — BYOK key resolution
    invalidate_llm_cache()  — Cache invalidation

Internal implementation is distributed across:
    - llm_provider_service: provider config, circuit breakers, sanitization
    - llm_fallback_service: request dispatch, fallback chain, direct clients
    - llm_key_service:      user API key resolution (BYOK)

# Backward-compatible re-exports

Private names are re-exported here so that existing test patches on
``app.services.llm_service.*`` continue to work after decomposition.
"""

from __future__ import annotations

import logging

from app.config.settings import settings
from app.services.llm_fallback_service import (
    LLMUnavailableError,
    _generate_fallback,
    _generate_openai_compat,
    _ollama_http,
    _openai_compat,
    generate,
    generate_with_fallback,
    generate_with_model,
    invalidate_llm_cache,
)
from app.services.llm_key_service import resolve_user_api_key
from app.services.llm_provider_service import (
    _INJECTION_PATTERNS,
    _PROVIDER_BREAKERS,
    LITELLM_AVAILABLE,
    LLM_DEEPSEEK,
    LLM_GROQ,
    LLM_NVIDIA,
    LLM_OPENROUTER,
    MAX_LLM_INPUT_LENGTH,
    _breaker_enabled,
    _breaker_fail_max,
    _breaker_reset_seconds,
    _cache_key,
    _call_with_provider_circuit,
    _extract_prompts,
    _infer_provider,
    _normalize_model_name,
    _provider_breaker,
    _provider_timeout_seconds,
    _record_cache_hit,
    _record_cache_miss,
    _record_failure,
    _record_metrics,
    check_health,
    sanitize_for_llm,
)

logger = logging.getLogger(__name__)

try:
    import pybreaker  # noqa: F401
except ImportError:
    pybreaker = None

__all__ = [
    "generate",
    "generate_with_model",
    "generate_with_fallback",
    "sanitize_for_llm",
    "check_health",
    "resolve_user_api_key",
    "invalidate_llm_cache",
    "LLMUnavailableError",
    "LLM_NVIDIA",
    "LLM_GROQ",
    "LLM_OPENROUTER",
    "LLM_DEEPSEEK",
    "LITELLM_AVAILABLE",
    "MAX_LLM_INPUT_LENGTH",
    "settings",
    "pybreaker",
    "_call_with_provider_circuit",
    "_breaker_enabled",
    "_breaker_fail_max",
    "_breaker_reset_seconds",
    "_provider_breaker",
    "_provider_timeout_seconds",
    "_extract_prompts",
    "_generate_fallback",
    "_generate_openai_compat",
    "_cache_key",
    "_infer_provider",
    "_INJECTION_PATTERNS",
    "_normalize_model_name",
    "_PROVIDER_BREAKERS",
    "_record_cache_hit",
    "_record_cache_miss",
    "_record_failure",
    "_record_metrics",
    "_openai_compat",
    "_ollama_http",
    "resolve_user_api_key",
]
