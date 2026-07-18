# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
llm_service.py — Unified LLM access layer.

Thin facade that delegates to decomposed services:
- llm_provider_service: provider config, circuit breakers, sanitization, health
- llm_fallback_service: request dispatch, fallback chain, direct clients
- llm_key_service:      user API key resolution (BYOK)
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from app.config.settings import settings
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)

# ── Delegate to llm_key_service ─────────────────────────────────────────── #
from app.services.llm_key_service import (
    resolve_user_api_key,
)

# ── Delegate to llm_provider_service ─────────────────────────────────────── #
from app.services.llm_provider_service import (
    _provider_timeout_seconds,
    _breaker_enabled,
    _breaker_fail_max,
    _breaker_reset_seconds,
    _PROVIDER_BREAKERS,
    _provider_breaker,
    _call_with_provider_circuit,
    _normalize_model_name,
    _infer_provider,
    LITELLM_AVAILABLE,
    LLM_NVIDIA,
    LLM_GROQ,
    LLM_OPENROUTER,
    LLM_DEEPSEEK,
    LLM_GPT4,
    sanitize_for_llm,
    _INJECTION_PATTERNS,
    MAX_LLM_INPUT_LENGTH,
    _extract_prompts,
    _cache_key,
    check_health,
)

# ── Delegate to llm_fallback_service ─────────────────────────────────────── #
from app.services.llm_fallback_service import (
    LLMUnavailableError,
    generate,
    generate_with_model,
    _generate_openai_compat,
    generate_with_fallback,
    invalidate_llm_cache,
    _generate_fallback,
    _openai_compat,
    _ollama_http,
)
