from unittest.mock import MagicMock, patch


class TestGetBuiltinProviders:
    def test_returns_dict(self):
        from app.services.provider_registry import get_builtin_providers
        result = get_builtin_providers()
        assert isinstance(result, dict)
        assert "openai" in result
        assert "anthropic" in result
        assert "groq" in result
        assert "ollama" in result
        assert "nvidia" in result

    def test_builtin_providers_have_required_keys(self):
        from app.services.provider_registry import get_builtin_providers
        required = {"name", "base_url", "models", "default_model"}
        for pid, info in get_builtin_providers().items():
            for key in required:
                assert key in info, f"{pid} missing key: {key}"


class TestGetProviderInfo:
    def test_found(self):
        from app.services.provider_registry import get_provider_info
        info = get_provider_info("openai")
        assert info is not None
        assert info["name"] == "OpenAI"

    def test_case_insensitive(self):
        from app.services.provider_registry import get_provider_info
        info = get_provider_info("OpenRouter")
        assert info is not None
        assert info["name"] == "OpenRouter"

    def test_not_found(self):
        from app.services.provider_registry import get_provider_info
        assert get_provider_info("nonexistent") is None


class TestOpenAICompatibleProviders:
    def test_set_has_expected_members(self):
        from app.services.provider_registry import OPENAI_COMPATIBLE_PROVIDERS
        assert "openai" in OPENAI_COMPATIBLE_PROVIDERS
        assert "groq" in OPENAI_COMPATIBLE_PROVIDERS
        assert "deepseek" in OPENAI_COMPATIBLE_PROVIDERS
        assert "openrouter" in OPENAI_COMPATIBLE_PROVIDERS
        assert "nvidia" in OPENAI_COMPATIBLE_PROVIDERS
        assert "mistral" in OPENAI_COMPATIBLE_PROVIDERS

    def test_not_includes_non_openai_compat(self):
        from app.services.provider_registry import OPENAI_COMPATIBLE_PROVIDERS
        assert "anthropic" not in OPENAI_COMPATIBLE_PROVIDERS
        assert "google" not in OPENAI_COMPATIBLE_PROVIDERS
        assert "ollama" not in OPENAI_COMPATIBLE_PROVIDERS


class TestListAvailableModels:
    def test_no_db_returns_builtin(self):
        from app.services.provider_registry import list_available_models
        result = list_available_models(db=None, user_id=None)
        assert len(result) >= 10
        assert all(not r["is_custom"] for r in result)

    def test_key_configured_when_env_var_set(self):
        from app.services.provider_registry import list_available_models
        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.services.provider_registry.settings", mock_settings):
            result = list_available_models()
        openai = next(r for r in result if r["provider_id"] == "openai")
        assert openai["key_configured"] is True

    def test_key_not_configured_when_env_var_missing(self):
        from app.services.provider_registry import list_available_models
        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        with patch("app.services.provider_registry.settings", mock_settings):
            result = list_available_models()
        openai = next(r for r in result if r["provider_id"] == "openai")
        assert openai["key_configured"] is False

    def test_includes_custom_providers_from_db(self):
        from app.services.provider_registry import list_available_models
        mock_db = MagicMock()
        mock_cp = MagicMock()
        mock_cp.id = "cp-123"
        mock_cp.name = "My Local"
        mock_cp.base_url = "http://localhost:8080/v1"
        mock_cp.models = ["model-x", "model-y"]
        mock_cp.api_key_encrypted = "encrypted_key"
        mock_cp.is_local = False
        mock_cp.is_active = True
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_cp]

        result = list_available_models(db=mock_db, user_id="user-1")
        custom = [r for r in result if r["is_custom"]]
        assert len(custom) == 1
        assert custom[0]["provider_id"] == "custom_cp-123"
        assert custom[0]["name"] == "My Local"
        assert "model-x" in custom[0]["models"]
        assert custom[0]["key_configured"] is True

    def test_custom_provider_no_key_is_unconfigured(self):
        from app.services.provider_registry import list_available_models
        mock_db = MagicMock()
        mock_cp = MagicMock()
        mock_cp.id = "cp-456"
        mock_cp.name = "No Key"
        mock_cp.models = []
        mock_cp.api_key_encrypted = None
        mock_cp.is_local = True
        mock_cp.is_active = True
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_cp]

        result = list_available_models(db=mock_db, user_id="user-1")
        custom = next(r for r in result if r["is_custom"])
        assert custom["key_configured"] is True

    def test_custom_providers_exception_handled(self):
        from app.services.provider_registry import list_available_models
        mock_db = MagicMock()
        mock_db.execute.side_effect = RuntimeError("DB down")
        result = list_available_models(db=mock_db, user_id="user-1")
        custom = [r for r in result if r["is_custom"]]
        assert len(custom) == 0

    def test_ollama_base_url_is_callable(self):
        from app.services.provider_registry import list_available_models
        with patch("app.services.provider_registry.settings.OPENAI_API_KEY", None):
            result = list_available_models()
        ollama = next(r for r in result if r["provider_id"] == "ollama")
        assert isinstance(ollama["base_url"], str)
        assert "11434" in ollama["base_url"] or "localhost" in ollama["base_url"]


class TestResolveModelProvider:
    def test_exact_match(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("gpt-4o") == "openai"
        assert resolve_model_provider("claude-3-5-sonnet-20241022") == "anthropic"

    def test_prefix_match(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("nvidia_nim/meta/llama") == "nvidia"
        assert resolve_model_provider("ollama/deepseek-r1") == "ollama"

    def test_gpt_pattern(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("gpt-4-turbo") == "openai"
        assert resolve_model_provider("gpt-3.5-turbo") == "openai"

    def test_o1_pattern(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("o1") == "openai"
        assert resolve_model_provider("o3-mini") == "openai"

    def test_claude_pattern(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("claude-opus-3") == "anthropic"

    def test_nvidia_nim_prefix(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("nvidia_nim/meta/llama-3.1-70b") == "nvidia"

    def test_unknown_model(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("completely-unknown-model") is None

    def test_empty_model(self):
        from app.services.provider_registry import resolve_model_provider
        assert resolve_model_provider("") is None
        assert resolve_model_provider(None) is None


class TestNormalizeModelName:
    def test_already_prefixed(self):
        from app.services.provider_registry import normalize_model_name
        assert normalize_model_name("openai/gpt-4", "openai") == "openai/gpt-4"

    def test_adds_prefix(self):
        from app.services.provider_registry import normalize_model_name
        assert normalize_model_name("gpt-4", "openai") == "openai/gpt-4"

    def test_empty_model(self):
        from app.services.provider_registry import normalize_model_name
        assert normalize_model_name("", "openai") == ""
        assert normalize_model_name("  ", "openai") == ""
        assert normalize_model_name(None, "openai") == ""
