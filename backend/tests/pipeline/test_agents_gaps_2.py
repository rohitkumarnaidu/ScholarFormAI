# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch, Mock, PropertyMock

import pytest


# ==============================================================================
# _FallbackPromptTemplate
# ==============================================================================

class TestFallbackPromptTemplate:
    def test_from_template_and_format(self):
        from app.pipeline.agents.document_agent import _FallbackPromptTemplate
        pt = _FallbackPromptTemplate.from_template("Hello {name}")
        assert pt.format(name="World") == "Hello World"

    def test_init_with_template(self):
        from app.pipeline.agents.document_agent import _FallbackPromptTemplate
        pt = _FallbackPromptTemplate("template")
        assert pt.template == "template"


# ==============================================================================
# DocumentAgent._should_fallback
# ==============================================================================

class TestShouldFallback:
    def _make(self):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.tools = []
        agent.memory = None
        agent.streaming_callback = None
        return agent

    def test_no_intermediate_steps(self):
        agent = self._make()
        result = agent._should_fallback({"intermediate_steps": []})
        assert result is False

    def test_high_error_rate(self):
        agent = self._make()
        steps = [("tool1", "ERROR: something failed"), ("tool2", "ERROR: another fail"), ("tool3", "OK")]
        result = agent._should_fallback({"intermediate_steps": steps})
        assert result is True

    def test_low_error_rate(self):
        agent = self._make()
        steps = [("tool1", "ERROR: fail"), ("tool2", "OK"), ("tool3", "OK")]
        result = agent._should_fallback({"intermediate_steps": steps})
        assert result is False


# ==============================================================================
# DocumentAgent._run_direct_fallback
# ==============================================================================

class TestRunDirectFallback:
    def _make(self, tools):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.tools = tools
        agent.memory = None
        agent.streaming_callback = None
        agent._agent_import_error = None
        agent.max_retries = 3
        return agent

    def test_fallback_execution(self):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        classes = [MetadataExtractionTool, LayoutAnalysisTool, ReferenceExtractionTool, FigureAnalysisTool, ValidationTool]
        tools = []
        for cls in classes:
            t = MagicMock(spec=cls)
            t.name = cls.__name__
            t._run.return_value = f"result from {cls.__name__}"
            tools.append(t)
        agent = self._make(tools)
        result = agent._run_direct_fallback(None, "/path/doc.pdf")
        assert result["success"] is True
        assert "analysis" in result
        assert len(result["intermediate_steps"]) == 5

    def test_fallback_exception(self):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        failing = MagicMock(spec=MetadataExtractionTool)
        failing._run.side_effect = RuntimeError("boom")
        failing.name = "metadata"
        agent = self._make([failing])
        result = agent._run_direct_fallback(None, "/path/doc.pdf")
        assert result["success"] is False


# ==============================================================================
# DocumentAgent — __init__ with patched dependencies
# ==============================================================================

class TestDocumentAgentInit:
    @patch("app.pipeline.agents.document_agent.ChatOpenAI")
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory.create_llm")
    def test_init_basic(self, mock_create, mock_chat):
        mock_chat.side_effect = Exception("no key")
        mock_llm = MagicMock()
        mock_create.return_value = mock_llm
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent(llm_provider="openai", llm_model="gpt-4", enable_memory=False)
        assert agent.memory is None
        assert len(agent.tools) == 5

    @patch("app.pipeline.agents.document_agent.AgentMemory")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI")
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory.create_llm")
    def test_init_with_memory(self, mock_create, mock_chat, mock_memory_cls):
        mock_chat.side_effect = Exception("no key")
        mock_llm = MagicMock()
        mock_create.return_value = mock_llm
        mock_memory = MagicMock()
        mock_memory_cls.return_value = mock_memory
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent(enable_memory=True)
        assert agent.memory is not None


# ==============================================================================
# CustomLLMFactory — app.pipeline.agents.llm_factory
# ==============================================================================

class TestLiteLLMShim:
    def test_invoke_and_call(self):
        with patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen:
            mock_gen.return_value = "generated text"
            from app.pipeline.agents.llm_factory import _LiteLLMShim
            shim = _LiteLLMShim(model="gpt-4", temperature=0.0, api_key="key", api_base=None)
            response = shim.invoke("hello")
            assert response.content == "generated text"
            result = shim("hello")
            assert result == "generated text"


class TestCreateLLM:
    def test_create_litellm_openai(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True), \
             patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen, \
             patch("app.pipeline.agents.llm_factory._get_api_key", return_value="key"):
            mock_gen.return_value = "ok"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
            result = llm.invoke("hello")
            assert result.content == "ok"

    def test_create_litellm_ollama(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True), \
             patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen:
            mock_gen.return_value = "ok"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="ollama", model="deepseek-r1")
            result = llm.invoke("hello")
            assert result.content == "ok"

    def test_create_litellm_nvidia(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True), \
             patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen, \
             patch("app.pipeline.agents.llm_factory._get_api_key", return_value="key"):
            mock_gen.return_value = "ok"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="nvidia", model="meta/llama-3.3-70b-instruct")
            result = llm.invoke("hello")
            assert result.content == "ok"

    def test_create_litellm_unsupported_provider(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True), \
             patch("app.pipeline.agents.llm_factory._llm_generate"):
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            with pytest.raises(ValueError, match="Unsupported provider"):
                CustomLLMFactory.create_llm(provider="unknown", model="x")

    def test_create_langchain_openai(self):
        mock_llm = MagicMock()
        mock_cls = MagicMock(return_value=mock_llm)
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False), \
             patch("app.pipeline.agents.llm_factory.ChatOpenAI", mock_cls), \
             patch("app.pipeline.agents.llm_factory.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
            assert llm is mock_llm

    def test_create_langchain_openai_no_key(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False), \
             patch("app.pipeline.agents.llm_factory.ChatOpenAI", MagicMock()), \
             patch("app.pipeline.agents.llm_factory.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
                CustomLLMFactory.create_llm(provider="openai", model="gpt-4")

    def test_create_langchain_ollama(self):
        mock_llm = MagicMock()
        mock_cls = MagicMock(return_value=mock_llm)
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False), \
             patch("app.pipeline.agents.llm_factory.Ollama", mock_cls), \
             patch("app.pipeline.agents.llm_factory.settings") as mock_settings:
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="ollama", model="llama2")
            assert llm is mock_llm

    def test_create_langchain_anthropic(self):
        mock_llm = MagicMock()
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False), \
             patch("app.pipeline.agents.llm_factory.settings") as mock_settings, \
             patch("langchain_anthropic.ChatAnthropic", return_value=mock_llm):
            mock_settings.ANTHROPIC_API_KEY = "ant-key"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="anthropic", model="claude-3-sonnet")
            assert llm is mock_llm

    def test_create_langchain_custom_raises(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            with pytest.raises(NotImplementedError):
                CustomLLMFactory.create_llm(provider="custom", model="x")

    def test_create_langchain_unsupported(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            with pytest.raises(ValueError, match="Unsupported provider"):
                CustomLLMFactory.create_llm(provider="bad", model="x")


class TestGetAvailableProviders:
    def test_with_openai_key(self):
        with patch("app.pipeline.agents.llm_factory.settings") as mock_settings:
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = "sk-xxx"
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            providers = CustomLLMFactory.get_available_providers()
            assert "openai" in providers


class TestGetRecommendedModels:
    def test_openai(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        models = CustomLLMFactory.get_recommended_models("openai")
        assert "gpt-4" in models and "gpt-4-turbo" in models

    def test_unknown_provider(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        assert CustomLLMFactory.get_recommended_models("unknown") == []


class TestGetApiKey:
    def test_openai_key(self):
        with patch("app.pipeline.agents.llm_factory.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-key"
            from app.pipeline.agents.llm_factory import _get_api_key
            assert _get_api_key("openai") == "sk-key"

    def test_unknown_provider(self):
        with patch("app.pipeline.agents.llm_factory.settings") as mock_settings:
            from app.pipeline.agents.llm_factory import _get_api_key
            assert _get_api_key("unknown") is None


class TestIsMockedConstructor:
    def test_mock_is_true(self):
        from app.pipeline.agents.llm_factory import _is_mocked_constructor
        assert _is_mocked_constructor(MagicMock()) is True

    def test_real_class_is_false(self):
        from app.pipeline.agents.llm_factory import _is_mocked_constructor
        assert _is_mocked_constructor(str) is False
