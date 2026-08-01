from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ── Discovered models cache (per-user, in-memory with TTL) ──────────────── #

_DISCOVERED_MODELS_CACHE: dict[str, dict[str, dict]] = {}
_DISCOVERED_MODELS_TTL = 3600  # 1 hour


def cache_discovered_models(user_id: str, provider_id: str, models: list[str]) -> None:
    """Store discovered models for a user+provider so they appear in list_available_models()."""
    if user_id not in _DISCOVERED_MODELS_CACHE:
        _DISCOVERED_MODELS_CACHE[user_id] = {}
    _DISCOVERED_MODELS_CACHE[user_id][provider_id] = {
        "models": list(dict.fromkeys(models)),  # deduplicate preserving order
        "timestamp": time.time(),
    }


def _get_cached_discovered_models(user_id: str | None, provider_id: str) -> list[str]:
    if not user_id:
        return []
    user_cache = _DISCOVERED_MODELS_CACHE.get(user_id, {})
    entry = user_cache.get(provider_id)
    if not entry:
        return []
    if time.time() - entry["timestamp"] > _DISCOVERED_MODELS_TTL:
        user_cache.pop(provider_id, None)
        return []
    return entry["models"]


# ── Built-in provider definitions ──────────────────────────────────────── #

BUILTIN_PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "docs_url": "https://platform.openai.com/api-keys",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1",
            "o1-mini",
            "o3-mini",
        ],
        "env_key": "OPENAI_API_KEY",
        "env_key_actual": lambda: settings.OPENAI_API_KEY,
        "default_model": "gpt-4o-mini",
        "supports_custom_base_url": False,
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "docs_url": "https://console.anthropic.com/settings/keys",
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
        ],
        "env_key": "ANTHROPIC_API_KEY",
        "env_key_actual": lambda: settings.ANTHROPIC_API_KEY,
        "default_model": "claude-3-5-sonnet-20241022",
        "supports_custom_base_url": False,
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "docs_url": "https://console.groq.com/keys",
        "models": [
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        "env_key": "GROQ_API_KEY",
        "env_key_actual": lambda: settings.GROQ_API_KEY,
        "default_model": settings.GROQ_MODEL or "llama3-8b-8192",
        "supports_custom_base_url": False,
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "docs_url": "https://platform.deepseek.com/api_keys",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "env_key": "DEEPSEEK_API_KEY",
        "env_key_actual": lambda: getattr(settings, "DEEPSEEK_API_KEY", None),
        "default_model": "deepseek-chat",
        "supports_custom_base_url": False,
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "docs_url": "https://openrouter.ai/keys",
        "models": [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-pro",
            "meta-llama/llama-3.1-70b-instruct",
        ],
        "env_key": "OPENROUTER_API_KEY",
        "env_key_actual": lambda: settings.OPENROUTER_API_KEY,
        "default_model": settings.OPENROUTER_MODEL or "openai/gpt-4o-mini",
        "supports_custom_base_url": True,
    },
    "google": {
        "name": "Google AI",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "docs_url": "https://aistudio.google.com/app/apikey",
        "models": [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "env_key": "GOOGLE_API_KEY",
        "env_key_actual": lambda: getattr(settings, "GOOGLE_API_KEY", None),
        "default_model": "gemini-2.0-flash",
        "supports_custom_base_url": False,
    },
    "cohere": {
        "name": "Cohere",
        "base_url": "https://api.cohere.com/v1",
        "docs_url": "https://dashboard.cohere.com/api-keys",
        "models": ["command-r-plus", "command-r", "command-light"],
        "env_key": "COHERE_API_KEY",
        "env_key_actual": lambda: getattr(settings, "COHERE_API_KEY", None),
        "default_model": "command-r-plus",
        "supports_custom_base_url": False,
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "docs_url": "https://console.mistral.ai/api-keys/",
        "models": [
            "mistral-large-latest",
            "mistral-small-latest",
            "open-mistral-7b",
            "codestral-latest",
        ],
        "env_key": "MISTRAL_API_KEY",
        "env_key_actual": lambda: getattr(settings, "MISTRAL_API_KEY", None),
        "default_model": "mistral-small-latest",
        "supports_custom_base_url": False,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": lambda: settings.OLLAMA_BASE_URL or "http://localhost:11434",
        "docs_url": "https://ollama.ai/download",
        "models": [],  # Dynamically discovered
        "env_key": None,
        "env_key_actual": lambda: None,
        "default_model": "deepseek-r1",
        "supports_custom_base_url": True,
        "is_local": True,
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "docs_url": "https://build.nvidia.com/",
        "models": [settings.NVIDIA_MODEL.replace("nvidia_nim/", "")] if settings.NVIDIA_MODEL else [],
        "env_key": "NVIDIA_API_KEY",
        "env_key_actual": lambda: settings.NVIDIA_API_KEY,
        "default_model": settings.NVIDIA_MODEL.replace("nvidia_nim/", "") if settings.NVIDIA_MODEL else "",
        "supports_custom_base_url": False,
    },
}

OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "groq",
    "deepseek",
    "openrouter",
    "nvidia",
    "mistral",
}


def get_provider_info(provider_id: str) -> dict[str, Any] | None:
    return BUILTIN_PROVIDERS.get(provider_id.lower())


def get_builtin_providers() -> dict[str, dict[str, Any]]:
    return dict(BUILTIN_PROVIDERS)


def _get_user_configured_providers(db: Session, user_id: str) -> set[str]:
    """Return set of provider names for which the user has stored an active API key."""
    try:
        from sqlalchemy import select

        from app.models.api_key import UserApiKey

        rows = db.execute(
            select(UserApiKey.provider).where(
                UserApiKey.user_id == user_id,
                UserApiKey.is_active.is_(True),
            )
        ).all()
        return {row[0] for row in rows}
    except Exception:
        return set()


def list_available_models(
    db: Session | None = None,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return all available models grouped by provider.
    Includes built-in providers and user's custom providers.
    key_configured is True if: env var is set, OR user has an active stored key.
    """
    user_providers: set[str] = set()
    if db and user_id:
        user_providers = _get_user_configured_providers(db, user_id)

    result = []

    for provider_id, info in BUILTIN_PROVIDERS.items():
        env_configured = bool(info.get("env_key_actual", lambda: None)())
        key_configured = env_configured or (provider_id in user_providers)
        base_url = info.get("base_url", "")
        if callable(base_url):
            base_url = base_url()
        result.append(
            {
                "provider_id": provider_id,
                "name": info["name"],
                "models": info.get("models", []),
                "default_model": info.get("default_model", ""),
                "base_url": base_url,
                "docs_url": info.get("docs_url"),
                "key_configured": key_configured,
                "is_local": info.get("is_local", False),
                "is_custom": False,
            }
        )

    # Add user's custom providers from DB
    if db and user_id:
        try:
            from sqlalchemy import select

            from app.models.custom_provider import CustomProvider

            query = select(CustomProvider).where(
                CustomProvider.user_id == user_id,
                CustomProvider.is_active.is_(True),
            )
            rows = db.execute(query).scalars().all()
            for cp in rows:
                result.append(
                    {
                        "provider_id": f"custom_{cp.id}",
                        "name": cp.name,
                        "models": cp.models or [],
                        "default_model": (cp.models or [None])[0] or "",
                        "base_url": cp.base_url,
                        "docs_url": None,
                        "key_configured": bool(cp.api_key_encrypted) or cp.is_local,
                        "is_local": cp.is_local,
                        "is_custom": True,
                        "custom_provider_id": str(cp.id),
                    }
                )
        except Exception as exc:
            logger.warning("Failed to load custom providers: %s", exc)

    # Enrich built-in providers with user's cached discovered models
    if user_id:
        for item in result:
            if item.get("is_custom"):
                continue
            pid = item["provider_id"]
            discovered = _get_cached_discovered_models(user_id, pid)
            if discovered:
                existing = set(item.get("models", []))
                for m in discovered:
                    if m not in existing:
                        item["models"].append(m)

    return result


def resolve_model_provider(model_name: str) -> str | None:
    """
    Given a full model string (e.g. 'gpt-4o' or 'nvidia_nim/meta/llama'),
    resolve which provider it belongs to.
    """
    if not model_name:
        return None
    model_lower = model_name.lower()

    for provider_id, info in BUILTIN_PROVIDERS.items():
        prefix = f"{provider_id}/"
        if model_lower.startswith(prefix):
            return provider_id
        for m in info.get("models", []):
            if model_lower == m.lower():
                return provider_id

    if model_lower.startswith("gpt-") or model_lower.startswith("o1") or model_lower.startswith("o3"):
        return "openai"
    if model_lower.startswith("claude"):
        return "anthropic"
    if model_lower.startswith("nvidia_nim/"):
        return "nvidia"

    return None


def normalize_model_name(model: str, provider: str) -> str:
    raw = (model or "").strip()
    if not raw:
        return raw
    if "/" in raw:
        return raw
    return f"{provider}/{raw}"
