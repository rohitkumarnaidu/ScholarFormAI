# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock


class TestCacheDiscoveredModels:
    def test_cache_models(self):
        from app.services.provider_registry import cache_discovered_models, _DISCOVERED_MODELS_CACHE
        _DISCOVERED_MODELS_CACHE.clear()
        cache_discovered_models("user-1", "ollama", ["model-a", "model-b", "model-a"])
        assert "user-1" in _DISCOVERED_MODELS_CACHE
        assert "ollama" in _DISCOVERED_MODELS_CACHE["user-1"]
        assert _DISCOVERED_MODELS_CACHE["user-1"]["ollama"]["models"] == ["model-a", "model-b"]


class TestGetCachedDiscoveredModels:
    def test_no_user(self):
        from app.services.provider_registry import _get_cached_discovered_models, _DISCOVERED_MODELS_CACHE
        _DISCOVERED_MODELS_CACHE.clear()
        result = _get_cached_discovered_models(None, "ollama")
        assert result == []

    def test_no_cache_entry(self):
        from app.services.provider_registry import _get_cached_discovered_models, _DISCOVERED_MODELS_CACHE
        _DISCOVERED_MODELS_CACHE.clear()
        result = _get_cached_discovered_models("user-1", "ollama")
        assert result == []

    def test_expired_entry(self):
        from app.services.provider_registry import _get_cached_discovered_models, _DISCOVERED_MODELS_CACHE
        _DISCOVERED_MODELS_CACHE.clear()
        _DISCOVERED_MODELS_CACHE["user-1"] = {
            "ollama": {"models": ["m1"], "timestamp": 0}
        }
        result = _get_cached_discovered_models("user-1", "ollama")
        assert result == []
        assert "ollama" not in _DISCOVERED_MODELS_CACHE["user-1"]

    def test_valid_entry(self):
        from app.services.provider_registry import _get_cached_discovered_models, _DISCOVERED_MODELS_CACHE
        _DISCOVERED_MODELS_CACHE.clear()
        _DISCOVERED_MODELS_CACHE["user-1"] = {
            "ollama": {"models": ["m1"], "timestamp": time.time()}
        }
        result = _get_cached_discovered_models("user-1", "ollama")
        assert result == ["m1"]


class TestGetProviderInfo:
    def test_known_provider(self):
        from app.services.provider_registry import get_provider_info
        info = get_provider_info("openai")
        assert info is not None
        assert info["name"] == "OpenAI"

    def test_unknown_provider(self):
        from app.services.provider_registry import get_provider_info
        info = get_provider_info("nonexistent")
        assert info is None

    def test_case_insensitive(self):
        from app.services.provider_registry import get_provider_info
        info = get_provider_info("OpenAI")
        assert info is not None


class TestGetBuiltinProviders:
    def test_returns_all_providers(self):
        from app.services.provider_registry import get_builtin_providers
        providers = get_builtin_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "groq" in providers
        assert "nvidia" in providers
        assert len(providers) >= 10

    def test_returns_copy(self):
        from app.services.provider_registry import get_builtin_providers
        providers = get_builtin_providers()
        providers["test"] = "value"
        providers2 = get_builtin_providers()
        assert "test" not in providers2


class TestListAvailableModels:
    def test_no_db_no_user(self):
        from app.services.provider_registry import list_available_models
        result = list_available_models(db=None, user_id=None)
        assert len(result) >= 10
        assert all(r.get("is_custom") is False for r in result)

    def test_with_user_providers(self):
        from app.services.provider_registry import list_available_models
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("openai",), ("anthropic",)]
        mock_db.execute.return_value = mock_result
        result = list_available_models(db=mock_db, user_id="user-1")
        openai_entry = next(r for r in result if r["provider_id"] == "openai")
        assert openai_entry["key_configured"] is True

    def test_with_custom_providers(self):
        from app.services.provider_registry import list_available_models
        mock_db = MagicMock()

        class MockRow:
            def __init__(self, provider):
                self.provider = provider
            def __getitem__(self, i):
                return self.provider if i == 0 else None
            def __iter__(self):
                return iter([self.provider])

        mock_user_result = MagicMock()
        mock_user_result.all.return_value = [MockRow("openai")]
        mock_user_query = MagicMock()
        mock_user_query.all.return_value = [MockRow("openai")]

        class MockCP:
            id = "cp-1"
            name = "My Custom"
            models = ["custom-model"]
            base_url = "http://custom"
            api_key_encrypted = "enc-key"
            is_local = False
            user_id = "user-1"

        mock_cp_scalars = MagicMock()
        mock_cp_scalars.all.return_value = [MockCP()]
        mock_cp_query = MagicMock()
        mock_cp_query.scalars.return_value = mock_cp_scalars

        results = [mock_user_result, mock_cp_query]

        def execute_side_effect(*args, **kw):
            if results:
                return results.pop(0)
            return MagicMock()

        mock_db.execute.side_effect = execute_side_effect
        result = list_available_models(db=mock_db, user_id="user-1")
        custom = [r for r in result if r.get("is_custom")]
        assert len(custom) == 1
        assert custom[0]["name"] == "My Custom"

    def test_custom_providers_exception(self):
        from app.services.provider_registry import list_available_models
        mock_db = MagicMock()
        mock_db.execute.side_effect = RuntimeError("db error")
        result = list_available_models(db=mock_db, user_id="user-1")
        assert len(result) >= 10

    def test_discovered_models_appended(self):
        from app.services.provider_registry import (
            list_available_models, cache_discovered_models, _DISCOVERED_MODELS_CACHE
        )
        _DISCOVERED_MODELS_CACHE.clear()
        cache_discovered_models("user-1", "ollama", ["discovered-model"])
        result = list_available_models(db=None, user_id="user-1")
        ollama = next(r for r in result if r["provider_id"] == "ollama")
        assert "discovered-model" in ollama["models"]

    def test_callable_base_url(self):
        from app.services.provider_registry import list_available_models
        with patch("app.services.provider_registry.settings") as mock_s:
            mock_s.OLLAMA_BASE_URL = "http://custom-ollama:11434"
            result = list_available_models(db=None, user_id=None)
            ollama = next(r for r in result if r["provider_id"] == "ollama")
            assert ollama["base_url"] == "http://custom-ollama:11434"


class TestResolveModelProvider:
    def test_none_model(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider(None) is None

    def test_empty_model(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("") is None

    def test_exact_match(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("gpt-4o") == "openai"

    def test_prefix_match(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("openai/gpt-4o") == "openai"

    def test_gpt_pattern(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("gpt-4-turbo") == "openai"

    def test_claude_pattern(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("claude-3-opus-20240229") == "anthropic"

    def test_nvidia_prefix(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("nvidia_nim/meta/llama") == "nvidia"

    def test_o1_pattern(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("o1-preview") == "openai"

    def test_o3_pattern(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("o3-mini") == "openai"

    def test_no_match(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("unknown-model-xyz") is None


class TestNormalizeModelName:
    def test_empty(self):
        from app.services.provider_registry import normalize_model_name
        assert normalize_model_name("", "openai") == ""

    def test_whitespace(self):
        from app.services.provider_registry import normalize_model_name
        assert normalize_model_name("  ", "openai") == ""

    def test_already_prefixed(self):
        from app.services.provider_registry import normalize_model_name
        assert normalize_model_name("openai/gpt-4", "openai") == "openai/gpt-4"

    def test_adds_prefix(self):
        from app.services.provider_registry import normalize_model_name
        assert normalize_model_name("gpt-4", "openai") == "openai/gpt-4"
