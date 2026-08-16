from unittest.mock import MagicMock, patch

import pytest


class TestGenerateWithModel:
    def test_unknown_model(self):
        from app.services.llm_service import LLMUnavailableError, generate_with_model

        with patch("app.services.provider_registry.resolve_model_provider", return_value=None):
            with pytest.raises(LLMUnavailableError, match="Unknown model"):
                generate_with_model([{"role": "user", "content": "Hi"}], "nonexistent-model")

    def test_custom_provider_flow(self):
        from app.services.llm_service import generate_with_model

        mock_db = MagicMock()
        mock_cp = MagicMock()
        mock_cp.id = "cp-1"
        mock_cp.base_url = "http://localhost:8080/v1"
        mock_cp.api_key_encrypted = "encrypted:key"
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cp

        mock_encryption = MagicMock()
        mock_encryption.decrypt.return_value = "decrypted-key"

        with patch("app.services.provider_registry.resolve_model_provider", return_value="custom_cp-1"):
            with patch("app.db.session.get_db", return_value=iter([mock_db])):
                with patch("app.services.encryption_service.get_encryption_service", return_value=mock_encryption):
                    with patch("app.services.llm_service._generate_openai_compat", return_value="custom response"):
                        result = generate_with_model(
                            [{"role": "user", "content": "Hi"}],
                            "custom_cp-1/my-model",
                        )

        assert result["text"] == "custom response"
        assert result["provider"] == "custom_cp-1"
        assert result["model"] == "custom_cp-1/my-model"

    def test_custom_provider_not_found(self):
        from app.services.llm_service import LLMUnavailableError, generate_with_model

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch("app.services.provider_registry.resolve_model_provider", return_value="custom_cp-1"):
            with patch("app.db.session.get_db", return_value=iter([mock_db])):
                with pytest.raises(LLMUnavailableError, match="not found"):
                    generate_with_model([{"role": "user", "content": "Hi"}], "custom_cp-1/my-model")

    def test_builtin_provider_success(self):
        from app.services.llm_service import generate_with_model

        mock_provider_info = {
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o"],
            "supports_custom_base_url": False,
        }

        with patch("app.services.provider_registry.resolve_model_provider", return_value="openai"):
            with patch("app.services.provider_registry.get_provider_info", return_value=mock_provider_info):
                with patch("app.services.llm_service.resolve_user_api_key", return_value="sk-test"):
                    with patch("app.services.llm_service._call_with_provider_circuit") as mock_call:
                        mock_call.return_value = "openai response"
                        result = generate_with_model(
                            [{"role": "user", "content": "Hi"}],
                            "gpt-4o",
                        )

        assert result["text"] == "openai response"
        assert result["provider"] == "openai"

    def test_builtin_returns_empty_raises(self):
        from app.services.llm_service import LLMUnavailableError, generate_with_model

        mock_provider_info = {"base_url": "https://api.openai.com/v1"}

        with patch("app.services.provider_registry.resolve_model_provider", return_value="openai"):
            with patch("app.services.provider_registry.get_provider_info", return_value=mock_provider_info):
                with patch("app.services.llm_service.resolve_user_api_key", return_value="sk-test"):
                    with patch("app.services.llm_service._call_with_provider_circuit") as mock_call:
                        mock_call.return_value = ""
                        with pytest.raises(LLMUnavailableError, match="returned empty"):
                            generate_with_model([{"role": "user", "content": "Hi"}], "gpt-4o")

    def test_builtin_exception_raises(self):
        from app.services.llm_service import LLMUnavailableError, generate_with_model

        mock_provider_info = {"base_url": "https://api.openai.com/v1"}

        with patch("app.services.provider_registry.resolve_model_provider", return_value="openai"):
            with patch("app.services.provider_registry.get_provider_info", return_value=mock_provider_info):
                with patch("app.services.llm_service.resolve_user_api_key", return_value="sk-test"):
                    with patch("app.services.llm_service._call_with_provider_circuit") as mock_call:
                        mock_call.side_effect = RuntimeError("API error")
                        with pytest.raises(LLMUnavailableError, match="API error"):
                            generate_with_model([{"role": "user", "content": "Hi"}], "gpt-4o")

    def test_callable_base_url(self):
        from app.services.llm_service import generate_with_model

        mock_provider_info = {"base_url": lambda: "http://dynamic-url/v1"}

        with patch("app.services.provider_registry.resolve_model_provider", return_value="ollama"):
            with patch("app.services.provider_registry.get_provider_info", return_value=mock_provider_info):
                with patch("app.services.llm_service.resolve_user_api_key", return_value=None):
                    with patch("app.services.llm_service._call_with_provider_circuit") as mock_call:
                        mock_call.return_value = "ollama response"
                        result = generate_with_model(
                            [{"role": "user", "content": "Hi"}],
                            "deepseek-r1",
                        )

        assert result["text"] == "ollama response"


class TestGenerateOpenaiCompat:
    def test_returns_content(self):
        from app.services.llm_service import _generate_openai_compat

        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "response text"
        mock_resp.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("openai.OpenAI", return_value=mock_client):
            result = _generate_openai_compat(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o",
                api_key="sk-test",
                api_base="https://api.openai.com/v1",
            )
        assert result == "response text"

    def test_returns_empty_on_no_choices(self):
        from app.services.llm_service import _generate_openai_compat

        mock_resp = MagicMock()
        mock_resp.choices = []
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("openai.OpenAI", return_value=mock_client):
            result = _generate_openai_compat(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o",
                api_key="sk-test",
                api_base="https://api.openai.com/v1",
            )
        assert result == ""

    def test_default_api_key_if_missing(self):
        from app.services.llm_service import _generate_openai_compat

        with patch("openai.OpenAI") as mock_openai:
            _generate_openai_compat(
                messages=[{"role": "user", "content": "Hi"}],
                model="llama-3",
                api_base="http://localhost:8080/v1",
            )
        mock_openai.assert_called_once()
        _, kwargs = mock_openai.call_args
        assert kwargs["api_key"] == "none"

    def test_passes_correct_params(self):
        from app.services.llm_service import _generate_openai_compat

        mock_client = MagicMock()
        with patch("openai.OpenAI", return_value=mock_client):
            _generate_openai_compat(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini",
                api_key="sk-test",
                api_base="https://api.openai.com/v1",
                temperature=0.7,
                max_tokens=4096,
                timeout=30,
            )
        _, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 4096
        assert kwargs["timeout"] == 30

    def test_clamps_temperature(self):
        from app.services.llm_service import _generate_openai_compat

        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_resp.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("openai.OpenAI", return_value=mock_client):
            _generate_openai_compat(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o",
                api_key="sk-test",
                api_base="https://api.openai.com/v1",
                temperature=2.5,
            )
        _, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["temperature"] == 1.0

        with patch("openai.OpenAI", return_value=mock_client):
            _generate_openai_compat(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o",
                api_key="sk-test",
                api_base="https://api.openai.com/v1",
                temperature=-1.0,
            )
        _, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["temperature"] == 0.0


class TestResolveUserApiKey:
    def test_uses_env_var_when_no_user_id(self):
        from app.services.llm_service import resolve_user_api_key

        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = "sk-env-key"
        with patch("app.services.llm_service.settings", mock_settings):
            result = resolve_user_api_key("openai")
        assert result == "sk-env-key"

    def test_returns_none_when_no_key(self):
        from app.services.llm_service import resolve_user_api_key

        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = None
        with patch("app.services.llm_service.settings", mock_settings):
            result = resolve_user_api_key("openai")
        assert result is None

    def test_unknown_provider_returns_none(self):
        from app.services.llm_service import resolve_user_api_key

        result = resolve_user_api_key("unknown_provider")
        assert result is None

    def test_user_key_priority(self):
        from app.services.llm_service import resolve_user_api_key

        mock_db_session = MagicMock()
        mock_key_service = MagicMock()
        mock_key = MagicMock()
        mock_key_service.get_active_key.return_value = mock_key
        mock_key_service.decrypt_key.return_value = "sk-user-key"

        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = "sk-env-fallback"

        with patch("app.services.llm_service.settings", mock_settings):
            with patch("app.db.session.get_db", return_value=iter([mock_db_session])):
                with patch("app.services.api_key_service.ApiKeyService", return_value=mock_key_service):
                    result = resolve_user_api_key("openai", user_id="user-1")

        assert result == "sk-user-key"

    def test_user_key_exception_falls_back_to_env(self):
        from app.services.llm_service import resolve_user_api_key

        mock_db_session = MagicMock()
        mock_db_session.close.side_effect = RuntimeError("close error")

        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = "sk-env-fallback"

        with patch("app.services.llm_service.settings", mock_settings):
            with patch("app.db.session.get_db", return_value=iter([mock_db_session])):
                result = resolve_user_api_key("openai", user_id="user-1")

        assert result == "sk-env-fallback"

    def test_deepseek_key_resolved(self):
        from app.services.llm_service import resolve_user_api_key

        mock_settings = MagicMock()
        mock_settings.DEEPSEEK_API_KEY = "sk-deepseek"
        with patch("app.services.llm_service.settings", mock_settings):
            result = resolve_user_api_key("deepseek")
        assert result == "sk-deepseek"

    def test_google_key_resolved(self):
        from app.services.llm_service import resolve_user_api_key

        mock_settings = MagicMock()
        mock_settings.GOOGLE_API_KEY = "google-key"
        with patch("app.services.llm_service.settings", mock_settings):
            result = resolve_user_api_key("google")
        assert result == "google-key"

    def test_cohere_key_resolved(self):
        from app.services.llm_service import resolve_user_api_key

        mock_settings = MagicMock()
        mock_settings.COHERE_API_KEY = "cohere-key"
        with patch("app.services.llm_service.settings", mock_settings):
            result = resolve_user_api_key("cohere")
        assert result == "cohere-key"

    def test_mistral_key_resolved(self):
        from app.services.llm_service import resolve_user_api_key

        mock_settings = MagicMock()
        mock_settings.MISTRAL_API_KEY = "mistral-key"
        with patch("app.services.llm_service.settings", mock_settings):
            result = resolve_user_api_key("mistral")
        assert result == "mistral-key"
