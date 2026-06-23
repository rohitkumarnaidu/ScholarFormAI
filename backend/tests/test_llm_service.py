# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from app.services import llm_service


def test_generate_with_fallback_uses_groq_when_nvidia_unset(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "NVIDIA_API_KEY", None, raising=False)
    monkeypatch.setattr(llm_service.settings, "GROQ_API_KEY", "groq-test-key", raising=False)
    monkeypatch.setattr(llm_service, "LLM_GROQ", "groq/llama3-8b-8192")

    calls: list[tuple[str, str | None]] = []

    def fake_generate(*args, **kwargs):
        calls.append((kwargs.get("model"), kwargs.get("api_key")))
        return "groq-answer"

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    result = llm_service.generate_with_fallback(
        [{"role": "user", "content": "Summarize this document"}]
    )

    assert result == {
        "text": "groq-answer",
        "model": "groq/llama3-8b-8192",
        "tier": 2,
    }
    assert calls == [("groq/llama3-8b-8192", "groq-test-key")]


def test_generate_caches_groq_responses(monkeypatch):
    from unittest.mock import patch
    from app.cache.redis_cache import redis_cache

    cache_store: dict[str, str] = {}
    call_count = 0

    def fake_get(cache_key: str):
        return cache_store.get(cache_key)

    def fake_set(cache_key: str, text: str, ttl: int = 3600):
        cache_store[cache_key] = text

    def fake_fallback(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return "cached-groq-answer"

    monkeypatch.setattr(llm_service, "LITELLM_AVAILABLE", False)
    monkeypatch.setattr(llm_service.settings, "LLM_CACHE_TTL_SECONDS", 3600, raising=False)
    monkeypatch.setattr(llm_service, "_generate_fallback", fake_fallback)

    messages = [{"role": "user", "content": "Explain Groq caching"}]
    with patch.object(redis_cache, "get_llm_result", fake_get):
        with patch.object(redis_cache, "set_llm_result", fake_set):
            first = llm_service.generate(messages, model="groq/llama3-8b-8192", api_key="groq-test-key")
            second = llm_service.generate(messages, model="groq/llama3-8b-8192", api_key="groq-test-key")

    assert first == "cached-groq-answer"
    assert second == "cached-groq-answer"
    assert call_count == 1


def test_generate_with_fallback_uses_openrouter_when_groq_rate_limited(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "NVIDIA_API_KEY", None, raising=False)
    monkeypatch.setattr(llm_service.settings, "GROQ_API_KEY", "groq-test-key", raising=False)
    monkeypatch.setattr(llm_service.settings, "OPENROUTER_API_KEY", "openrouter-test-key", raising=False)
    monkeypatch.setattr(llm_service.settings, "OPENROUTER_API_BASE", "https://openrouter.ai/api/v1", raising=False)
    monkeypatch.setattr(llm_service, "LLM_GROQ", "groq/llama3-8b-8192")
    monkeypatch.setattr(llm_service, "LLM_OPENROUTER", "openrouter/meta-llama/llama-3.1-8b-instruct")

    calls: list[str] = []

    def fake_generate(*args, **kwargs):
        model = kwargs.get("model")
        calls.append(str(model))
        if model == "groq/llama3-8b-8192":
            raise RuntimeError("429 rate limit exceeded")
        return "openrouter-answer"

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    result = llm_service.generate_with_fallback(
        [{"role": "user", "content": "Summarize this document"}]
    )

    assert result == {
        "text": "openrouter-answer",
        "model": "openrouter/meta-llama/llama-3.1-8b-instruct",
        "tier": 3,
    }
    assert calls == [
        "groq/llama3-8b-8192",
        "openrouter/meta-llama/llama-3.1-8b-instruct",
    ]


def test_generate_with_fallback_uses_configured_provider_timeout(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "NVIDIA_API_KEY", "nvidia-test-key", raising=False)
    monkeypatch.setattr(llm_service.settings, "LLM_PROVIDER_TIMEOUT_SECONDS", 7, raising=False)
    monkeypatch.setattr(llm_service, "LLM_NVIDIA", "nvidia_nim/meta/llama-3.3-70b-instruct")

    captured = {}

    def fake_generate(*args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return "nvidia-answer"

    monkeypatch.setattr(llm_service, "generate", fake_generate)

    result = llm_service.generate_with_fallback(
        [{"role": "user", "content": "Summarize this document"}]
    )

    assert result["tier"] == 1
    assert captured["timeout"] == 7
