# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import types
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
pytestmark = [pytest.mark.pipeline]


# ==============================================================================
# StreamingAgentCallback — deep edge case tests
# ==============================================================================

class TestStreamingAgentCallbackDeep:
    """Additional edge-case tests for StreamingAgentCallback."""

    def test_truncated_tool_input_on_tool_start(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_start({"name": "t"}, "a" * 200)
        data = cb.call_args[0][1]
        assert len(data["input"]) == 100

    def test_truncated_output_on_tool_end(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_end("a" * 500)
        data = cb.call_args[0][1]
        assert len(data["output_preview"]) == 200

    def test_truncated_log_on_agent_action(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        action = MagicMock()
        action.tool = "t"
        action.tool_input = "in"
        action.log = "a" * 300
        handler.on_agent_action(action)
        data = cb.call_args[0][1]
        assert len(data["log"]) == 200

    def test_agent_finish_empty_return_values(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        finish = MagicMock()
        finish.return_values = {}
        handler.on_agent_finish(finish)
        data = cb.call_args[0][1]
        assert "{}" in data["output"]

    def test_llm_start_empty_prompts(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_llm_start({}, [])
        data = cb.call_args[0][1]
        assert data["prompt_count"] == 0

    def test_agent_action_none_log(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        action = MagicMock()
        action.tool = "t"
        action.tool_input = "in"
        action.log = None
        handler.on_agent_action(action)
        data = cb.call_args[0][1]
        assert data["log"] == ""

    def test_tool_start_no_name_key(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_start({"not_name": "val"}, "input")
        data = cb.call_args[0][1]
        assert data["tool"] == "unknown"

    def test_chain_start_no_name_key(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_chain_start({"not_name": "val"}, {})
        data = cb.call_args[0][1]
        assert data["chain"] == "unknown"

    def test_agent_finish_large_output_truncated(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        finish = MagicMock()
        finish.return_values = {"output": "b" * 500}
        handler.on_agent_finish(finish)
        data = cb.call_args[0][1]
        assert len(data["output"]) == 200

    def test_tool_end_empty_output(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_end("")
        data = cb.call_args[0][1]
        assert data["output_preview"] == ""


# ==============================================================================
# CustomLLMFactory — deep edge case tests
# ==============================================================================

class TestCustomLLMFactoryDeep:
    """Additional edge-case tests for CustomLLMFactory."""

    def _factory(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        return CustomLLMFactory

    def _mod(self):
        import app.pipeline.agents.llm_factory
        return app.pipeline.agents.llm_factory

    # -- _create_litellm paths --

    def test_litellm_with_api_key_and_base_from_kwargs(self):
        mod = self._mod()
        with patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.object(mod, "_llm_generate", MagicMock()) as mock_gen, \
             patch.object(mod, "_get_api_key", return_value="fallback_key"):
            mock_gen.return_value = "ok"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(
                provider="openai", model="gpt-4",
                api_key="kwarg_key", api_base="http://custom.base"
            )
            assert llm is not None
            Response = llm.invoke("hello")
            assert Response.content == "ok"
            _, kwargs = mock_gen.call_args
            assert kwargs["api_key"] == "kwarg_key"
            assert kwargs["api_base"] == "http://custom.base"

    def test_litellm_with_base_url_fallback(self):
        mod = self._mod()
        with patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.object(mod, "_llm_generate", MagicMock()) as mock_gen, \
             patch.object(mod, "_get_api_key", return_value="key"):
            mock_gen.return_value = "ok"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(
                provider="openai", model="gpt-4",
                base_url="http://fallback.base"
            )
            assert llm is not None
            Response = llm.invoke("hello")
            assert Response.content == "ok"
            _, kwargs = mock_gen.call_args
            assert kwargs["api_base"] == "http://fallback.base"

    def test_litellm_anthropic_provider(self):
        mod = self._mod()
        with patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.object(mod, "_llm_generate", MagicMock()) as mock_gen, \
             patch.object(mod, "_get_api_key", return_value="key"):
            mock_gen.return_value = "ok"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(provider="anthropic", model="claude-3-sonnet-20240229")
            result = llm.invoke("hello")
            assert result.content == "ok"
            _, kwargs = mock_gen.call_args
            assert kwargs["model"] == "claude-3-sonnet-20240229"

    def test_litellm_api_key_from_get_api_key_fallback(self):
        mod = self._mod()
        with patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.object(mod, "_llm_generate", MagicMock()) as mock_gen, \
             patch.object(mod, "_get_api_key", return_value="env_key"):
            mock_gen.return_value = "ok"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
            Response = llm.invoke("hello")
            assert Response.content == "ok"
            _, kwargs = mock_gen.call_args
            assert kwargs["api_key"] == "env_key"

    def test_litellm_unsupported_provider_with_litellm_available(self):
        mod = self._mod()
        with patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.object(mod, "_llm_generate", MagicMock()):
            CustomLLMFactory = self._factory()
            with pytest.raises(ValueError, match="Unsupported provider"):
                CustomLLMFactory.create_llm(provider="unknown_provider", model="x")

    # -- force_langchain paths --

    def test_force_langchain_openai_with_mocked_chat(self):
        mod = self._mod()
        with patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.object(mod, "ChatOpenAI", MagicMock()) as mock_chat, \
             patch.object(mod, "_llm_generate", MagicMock()), \
             patch.object(mod, "settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            fake_instance = MagicMock()
            mock_chat.return_value = fake_instance
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
            assert llm is fake_instance

    def test_force_langchain_ollama_with_mocked_ollama(self):
        mod = self._mod()
        with patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.object(mod, "Ollama", MagicMock()) as mock_ollama, \
             patch.object(mod, "_llm_generate", MagicMock()), \
             patch.object(mod, "settings") as mock_settings:
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            fake_instance = MagicMock()
            mock_ollama.return_value = fake_instance
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(provider="ollama", model="llama2")
            assert llm is fake_instance

    # -- _create_langchain openai with ChatOpenAI=None --

    def test_create_langchain_openai_llm_cls_none_below_314(self):
        """llm_cls is None in _create_langchain openai, Python < 3.14."""
        mod = self._mod()
        fake_chat_cls = MagicMock()
        fake_instance = MagicMock()
        fake_chat_cls.return_value = fake_instance
        fake_openai_mod = types.ModuleType("langchain_openai")
        fake_openai_mod.ChatOpenAI = fake_chat_cls

        with patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.object(mod, "ChatOpenAI", None), \
             patch.object(mod, "settings") as mock_settings, \
             patch.dict("sys.modules", {"langchain_openai": fake_openai_mod}):
            mock_settings.OPENAI_API_KEY = "test-key"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
            assert llm is fake_instance
            fake_chat_cls.assert_called_once()

    def test_create_langchain_openai_api_key_from_os_getenv(self):
        mod = self._mod()
        fake_chat_cls = MagicMock()
        fake_openai_mod = types.ModuleType("langchain_openai")
        fake_openai_mod.ChatOpenAI = fake_chat_cls

        with patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.object(mod, "ChatOpenAI", None), \
             patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "os") as mock_os, \
             patch.dict("sys.modules", {"langchain_openai": fake_openai_mod}):
            mock_settings.OPENAI_API_KEY = ""
            mock_os.getenv.return_value = "env-key"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
            assert llm is fake_chat_cls.return_value
            mock_os.getenv.assert_called_once_with("OPENAI_API_KEY")

    # -- _create_langchain anthropic --

    def test_create_langchain_anthropic_success(self):
        mod = self._mod()
        fake_chat = MagicMock()
        fake_instance = MagicMock()
        fake_chat.return_value = fake_instance
        fake_anthropic_mod = types.ModuleType("langchain_anthropic")
        fake_anthropic_mod.ChatAnthropic = fake_chat

        with patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.object(mod, "settings") as mock_settings, \
             patch.dict("sys.modules", {"langchain_anthropic": fake_anthropic_mod}):
            mock_settings.ANTHROPIC_API_KEY = "ant-key"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(
                provider="anthropic", model="claude-3-sonnet-20240229"
            )
            assert llm is fake_instance
            fake_chat.assert_called_once()

    def test_create_langchain_anthropic_no_key(self):
        mod = self._mod()
        fake_chat = MagicMock()
        fake_anthropic_mod = types.ModuleType("langchain_anthropic")
        fake_anthropic_mod.ChatAnthropic = fake_chat

        with patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.object(mod, "settings") as mock_settings, \
             patch.dict("sys.modules", {"langchain_anthropic": fake_anthropic_mod}):
            mock_settings.ANTHROPIC_API_KEY = ""
            CustomLLMFactory = self._factory()
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
                CustomLLMFactory.create_llm(
                    provider="anthropic", model="claude-3-sonnet-20240229"
                )

    # -- _create_langchain ollama with Ollama=None --

    def test_create_langchain_ollama_llm_cls_none_below_314(self):
        mod = self._mod()
        fake_ollama_cls = MagicMock()
        fake_instance = MagicMock()
        fake_ollama_cls.return_value = fake_instance
        fake_community_mod = types.ModuleType("langchain_community")
        fake_llms_mod = types.ModuleType("langchain_community.llms")
        fake_llms_mod.Ollama = fake_ollama_cls
        fake_community_mod.llms = fake_llms_mod

        with patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.object(mod, "Ollama", None), \
             patch.object(mod, "settings") as mock_settings, \
             patch.dict("sys.modules", {
                 "langchain_community": fake_community_mod,
                 "langchain_community.llms": fake_llms_mod,
             }):
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(provider="ollama", model="llama2")
            assert llm is fake_instance
            fake_ollama_cls.assert_called_once()

    # -- edge cases --

    def test_create_langchain_unsupported_provider(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            with pytest.raises(ValueError, match="Unsupported provider"):
                CustomLLMFactory.create_llm(provider="not_a_provider", model="x")

    def test_create_langchain_anthropic_import_error(self):
        """_create_langchain anthropic raises ImportError when langchain_anthropic not importable."""
        mod = self._mod()
        # Remove langchain_anthropic from sys.modules and prevent re-import
        with patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.object(mod, "settings") as mock_settings, \
             patch.dict("sys.modules", {"langchain_anthropic": None}):
            mock_settings.ANTHROPIC_API_KEY = "ant-key"
            CustomLLMFactory = self._factory()
            with pytest.raises(ImportError, match="langchain-anthropic not installed"):
                CustomLLMFactory.create_llm(provider="anthropic", model="claude-3-sonnet-20240229")

    def test_create_langchain_anthropic_from_kwargs_api_key(self):
        mod = self._mod()
        fake_chat = MagicMock()
        fake_anthropic_mod = types.ModuleType("langchain_anthropic")
        fake_anthropic_mod.ChatAnthropic = fake_chat

        with patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.object(mod, "settings") as mock_settings, \
             patch.dict("sys.modules", {"langchain_anthropic": fake_anthropic_mod}):
            mock_settings.ANTHROPIC_API_KEY = ""
            CustomLLMFactory = self._factory()
            llm = CustomLLMFactory.create_llm(
                provider="anthropic", model="claude-3-sonnet-20240229",
                api_key="kwarg-ant-key"
            )
            assert llm is fake_chat.return_value
            # verify the api_key in kwargs was passed correctly
            call_kwargs = fake_chat.call_args[1]
            assert call_kwargs["api_key"] == "kwarg-ant-key"


class TestGetAvailableProvidersDeep:
    """Extended tests for get_available_providers."""

    def _factory(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        return CustomLLMFactory

    def _make_anthropic_fake(self):
        mod = types.ModuleType("langchain_anthropic")
        mod.ChatAnthropic = MagicMock()
        return mod

    def test_all_providers_available(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        fake_anthropic = self._make_anthropic_fake()
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", True), \
             patch.dict("sys.modules", {"langchain_anthropic": fake_anthropic}), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = "nv-key"
            mock_settings.OPENAI_API_KEY = "sk-key"
            mock_settings.ANTHROPIC_API_KEY = "ant-key"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.return_value.status_code = 200

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert "nvidia" in providers
            assert "openai" in providers
            assert "anthropic" in providers
            assert "ollama" in providers
            assert "litellm" in providers

    def _mock_anthropic_fail(self):
        return patch.dict("sys.modules", {"langchain_anthropic": None})

    def test_no_providers_all_fail(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", False), \
             self._mock_anthropic_fail(), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.side_effect = Exception("timeout")

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert providers == []

    def test_ollama_exception_caught(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", False), \
             self._mock_anthropic_fail(), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.side_effect = ConnectionError("refused")

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert "ollama" not in providers

    def test_ollama_not_200(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", False), \
             self._mock_anthropic_fail(), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.return_value.status_code = 404

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert "ollama" not in providers

    def test_litellm_only(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", True), \
             self._mock_anthropic_fail(), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.side_effect = Exception("timeout")

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert providers == ["litellm"]

    def test_anthropic_import_error_caught(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.dict("sys.modules", {"langchain_anthropic": None}), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = "sk-key"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.side_effect = Exception("timeout")

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert "openai" in providers
            assert "anthropic" not in providers

    def test_anthropic_no_key_after_successful_import(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        fake_anthropic = self._make_anthropic_fake()
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", False), \
             patch.dict("sys.modules", {"langchain_anthropic": fake_anthropic}), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = "sk-key"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.side_effect = Exception("timeout")

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert "openai" in providers
            assert "anthropic" not in providers

    def test_providers_with_nvidia_and_openai(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "settings") as mock_settings, \
             patch.object(mod, "LITELLM_AVAILABLE", False), \
             self._mock_anthropic_fail(), \
             patch("requests.get") as mock_get:
            mock_settings.NVIDIA_API_KEY = "nv-key"
            mock_settings.OPENAI_API_KEY = "sk-key"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.side_effect = Exception("timeout")

            CustomLLMFactory = self._factory()
            providers = CustomLLMFactory.get_available_providers()
            assert "nvidia" in providers
            assert "openai" in providers
            assert "litellm" not in providers


class TestRecommendedModelsDeep:
    """Extended tests for get_recommended_models."""

    def test_all_providers(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        assert len(CustomLLMFactory.get_recommended_models("openai")) == 3
        assert len(CustomLLMFactory.get_recommended_models("anthropic")) == 3
        assert len(CustomLLMFactory.get_recommended_models("ollama")) == 4
        assert len(CustomLLMFactory.get_recommended_models("nvidia")) == 2
        assert len(CustomLLMFactory.get_recommended_models("litellm")) == 3
        assert CustomLLMFactory.get_recommended_models("not_real") == []


class TestGetApiKeyDeep:
    """Extended tests for _get_api_key."""

    def test_all_providers(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-key"
            mock_settings.ANTHROPIC_API_KEY = "ant-key"
            mock_settings.NVIDIA_API_KEY = "nv-key"
            assert mod._get_api_key("openai") == "sk-key"
            assert mod._get_api_key("anthropic") == "ant-key"
            assert mod._get_api_key("nvidia") == "nv-key"
            assert mod._get_api_key("ollama") is None


class TestIsMockedConstructorDeep:
    """Extended tests for _is_mocked_constructor."""

    def test_various_values(self):
        from app.pipeline.agents.llm_factory import _is_mocked_constructor
        assert _is_mocked_constructor(MagicMock()) is True
        assert _is_mocked_constructor(MagicMock(spec=int)) is True
        assert _is_mocked_constructor(None) is False
        assert _is_mocked_constructor(int) is False
        assert _is_mocked_constructor("str") is False


class TestLiteLLMShimDeep:
    """Extended tests for _LiteLLMShim."""

    def test_shim_invoke_and_call(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "_llm_generate") as mock_gen:
            mock_gen.return_value = "result text"
            shim = mod._LiteLLMShim(model="gpt-4", temperature=0.5)
            resp = shim.invoke("prompt")
            assert resp.content == "result text"
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["temperature"] == 0.5

            result = shim("direct")
            assert result == "result text"
            assert mock_gen.call_count == 2

    def test_shim_with_all_params(self):
        mod = __import__("app.pipeline.agents.llm_factory", fromlist=["_"])
        with patch.object(mod, "_llm_generate") as mock_gen:
            mock_gen.return_value = "ok"
            shim = mod._LiteLLMShim(
                model="claude-3", temperature=0.0,
                api_key="custom-key", api_base="https://custom.api"
            )
            shim.invoke("hello")
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["api_key"] == "custom-key"
            assert call_kwargs["api_base"] == "https://custom.api"
