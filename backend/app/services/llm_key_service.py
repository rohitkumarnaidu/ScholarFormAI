# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
LLM key service — user API key resolution (BYOK).

Extracted from the fat `llm_service.py`. Resolves a provider API key from
the user's stored encrypted keys first, then falls back to the environment
configured in :data:`app.config.settings`.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)


def _ls():
    """Return the ``app.services.llm_service`` facade module.

    Existing tests patch ``app.services.llm_service.settings``; reading the
    settings through the facade keeps ``resolve_user_api_key`` honouring that
    patch after the service was decomposed into ``llm_key_service``.
    """
    return sys.modules["app.services.llm_service"]


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
    settings = _ls().settings
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
