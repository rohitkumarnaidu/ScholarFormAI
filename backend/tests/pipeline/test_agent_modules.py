# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Focused enterprise tests for agent modules: document_agent, llm_factory."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest
pytestmark = [pytest.mark.pipeline]


# ==============================================================================
# DocumentAgent — constructor edge cases
# ==============================================================================

class TestDocumentAgentInit:
    """Constructor edge cases beyond what test_agents_gaps_2 covers."""

    @patch("app.pipeline.agents.document_agent.settings")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI")
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory.create_llm")
    @patch("app.pipeline.agents.document_agent.AgentMemory")
    @patch("app.pipeline.agents.document_agent.StreamingAgentCallback")
    def test_init_with_streaming_and_callback(
        self, mock_scb_cls, mock_mem_cls, mock_create_llm, mock_chat, mock_settings
    ):
        mock_chat.side_effect = Exception("no key")
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        mock_cb = MagicMock()
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent(
            enable_memory=False, enable_streaming=True, streaming_callback=mock_cb
        )
        assert agent.streaming_callback is not None
        mock_scb_cls.assert_called_once_with(callback_fn=mock_cb)

    @patch("app.pipeline.agents.document_agent.settings")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI")
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory.create_llm")
    @patch("app.pipeline.agents.document_agent.AgentMemory")
    def test_init_custom_grobid_url(
        self, mock_mem_cls, mock_create_llm, mock_chat, mock_settings
    ):
        mock_chat.side_effect = Exception("no key")
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent(grobid_url="http://custom:8070", enable_memory=False)
        tools = agent.tools
        assert len(tools) == 5

    @patch("app.pipeline.agents.document_agent.settings")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI")
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory.create_llm")
    @patch("app.pipeline.agents.document_agent.AgentMemory")
    def test_init_mock_call_count_path(
        self, mock_mem_cls, mock_create_llm, mock_chat, mock_settings
    ):
        mock_create_llm.return_value = MagicMock()
        mock_llm = MagicMock()
        mock_chat.return_value = mock_llm
        mock_chat.call_count = 0
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent(llm_provider="openai", enable_memory=False)
        assert agent.llm is not None

    @patch("app.pipeline.agents.document_agent.settings")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI")
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory.create_llm")
    def test_init_chatopenai_success(
        self, mock_create_llm, mock_chat, mock_settings
    ):
        mock_llm = MagicMock()
        mock_chat.return_value = mock_llm
        mock_settings.OPENAI_API_KEY = "sk-test"
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent(llm_provider="openai", enable_memory=False)
        assert agent.llm is mock_llm

    @patch("app.pipeline.agents.document_agent.settings")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI", None)
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory.create_llm")
    def test_init_chatopenai_none_factory_fallback(
        self, mock_create_llm, mock_settings
    ):
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent(llm_provider="openai", enable_memory=False)
        assert agent.llm is mock_llm
        mock_create_llm.assert_called_once_with(
            provider="openai", model="gpt-4", temperature=0.0
        )


# ==============================================================================
# DocumentAgent._initialize_executor
# ==============================================================================

class TestInitializeExecutor:
    """Paths through _initialize_executor."""

    @patch("app.pipeline.agents.document_agent.settings")
    def test_init_with_mocked_constructor(self, mock_settings):
        from app.pipeline.agents.document_agent import (
            create_openai_functions_agent, AgentExecutor, DocumentAgent
        )
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.llm = MagicMock()
        agent.tools = [MagicMock() for _ in range(3)]
        agent.prompt = MagicMock()
        agent.streaming_callback = None
        agent._agent_import_error = None
        agent.tools = agent.tools
        with (
            patch("app.pipeline.agents.document_agent.create_openai_functions_agent", MagicMock()),
            patch("app.pipeline.agents.document_agent.AgentExecutor", MagicMock()),
        ):
            agent._initialize_executor()
            assert agent.agent is not None
            assert agent.executor is not None

    @patch("app.pipeline.agents.document_agent.settings")
    def test_init_python_314_path(self, mock_settings):
        with patch("app.pipeline.agents.document_agent.sys.version_info", (3, 14)):
            from app.pipeline.agents.document_agent import DocumentAgent
            agent = DocumentAgent.__new__(DocumentAgent)
            agent.llm = MagicMock()
            agent.tools = [MagicMock() for _ in range(5)]
            agent.prompt = MagicMock()
            agent.streaming_callback = None
            agent._agent_import_error = None
            agent.executor = None
            agent._initialize_executor()
            assert agent._agent_import_error is not None
            assert "Python 3.14" in agent._agent_import_error

    @patch("app.pipeline.agents.document_agent.settings")
    def test_init_react_import_error(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.llm = MagicMock()
        agent.tools = [MagicMock() for _ in range(5)]
        agent.prompt = MagicMock()
        agent.streaming_callback = None
        agent._agent_import_error = None
        agent.executor = None
        # Patch create_react_agent import to raise
        import builtins
        original_import = builtins.__import__
        error_msg = "No module named 'langchain.agents'"

        def mock_import(name, *args, **kwargs):
            if name == "langchain.agents":
                raise ImportError(error_msg)
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            agent._initialize_executor()
        assert agent._agent_import_error == error_msg
        assert agent.executor is None

    @patch("app.pipeline.agents.document_agent.settings")
    def test_init_react_with_streaming(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.llm = MagicMock()
        agent.tools = [MagicMock() for _ in range(5)]
        agent.prompt = MagicMock()
        agent._agent_import_error = None
        agent.executor = None
        streaming_cb = MagicMock()
        agent.streaming_callback = streaming_cb
        # This will fall through to the try/except import block
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langchain.agents":
                raise ImportError("No module named 'langchain.agents'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            agent._initialize_executor()
        assert agent.executor is None


# ==============================================================================
# DocumentAgent.process_document
# ==============================================================================

class TestProcessDocument:
    """Tests for the sync process_document method."""

    @patch("app.pipeline.agents.document_agent.settings")
    def test_process_document_success(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.memory = None
        agent.streaming_callback = None
        agent.max_retries = 3
        agent._agent_import_error = None
        agent.executor = None
        agent._execute_with_retry = MagicMock(
            return_value={"output": "analysis result", "intermediate_steps": []}
        )
        result = agent.process_document("/path/doc.pdf")
        assert result["success"] is True
        assert result["analysis"] == "analysis result"
        assert result["should_fallback"] is False

    @patch("app.pipeline.agents.document_agent.settings")
    def test_process_document_fallback(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.memory = None
        agent.streaming_callback = None
        agent.max_retries = 3
        agent._agent_import_error = None
        agent.executor = None
        agent._execute_with_retry = MagicMock(
            return_value={
                "output": "analysis",
                "intermediate_steps": [
                    ("tool1", "ERROR: fail"),
                    ("tool2", "ERROR: fail2"),
                    ("tool3", "OK"),
                ],
            }
        )
        result = agent.process_document("/path/doc.pdf")
        assert result["should_fallback"] is True


# ==============================================================================
# DocumentAgent.run (async)
# ==============================================================================

class TestRun:
    """Tests for the async run method."""

    @pytest.fixture
    def agent(self):
        from app.pipeline.agents.document_agent import DocumentAgent
        a = DocumentAgent.__new__(DocumentAgent)
        a.max_retries = 3
        a.memory = None
        a.streaming_callback = None
        a._agent_import_error = None
        a.executor = None
        a.tools = []
        return a

    @pytest.fixture
    def mock_doc(self):
        doc = MagicMock()
        doc.document_id = "doc_123"
        doc.filename = "/path/doc.pdf"
        return doc

    @pytest.mark.asyncio
    async def test_run_with_executor(self, agent, mock_doc):
        from app.pipeline.agents.document_agent import ValidationTool
        validation_tool = MagicMock(spec=ValidationTool)
        validation_tool.name = "validate_document"
        agent.tools = [validation_tool]
        agent.executor = MagicMock()
        agent._execute_with_retry = MagicMock(
            return_value={"output": "analysis", "intermediate_steps": []}
        )
        result = await agent.run(mock_doc, "job_001")
        assert result["success"] is True
        assert result["analysis"] == "analysis"

    @pytest.mark.asyncio
    async def test_run_without_executor_fallback(self, agent, mock_doc):
        agent.executor = None
        agent._agent_import_error = "import failed"
        agent._run_direct_fallback = MagicMock(
            return_value={"success": True, "analysis": "fallback analysis", "intermediate_steps": []}
        )
        result = await agent.run(mock_doc, "job_001")
        assert result is not None

    @pytest.mark.asyncio
    async def test_run_without_executor_mocked_retry(self, agent, mock_doc):
        agent.executor = None
        mock_retry = MagicMock()
        mock_retry.side_effect = RuntimeError("retry failed")
        agent._execute_with_retry = mock_retry
        agent._run_direct_fallback = MagicMock(
            return_value={"success": True, "analysis": "fb", "intermediate_steps": []}
        )
        result = await agent.run(mock_doc, "job_001")
        assert result is not None
        mock_retry.assert_called_once_with("executor-unavailable")

    @pytest.mark.asyncio
    async def test_run_with_memory(self, agent, mock_doc):
        agent.memory = MagicMock()
        agent.memory.get_best_pattern.return_value = {"pattern": "test"}
        agent.executor = MagicMock()
        agent._execute_with_retry = MagicMock(
            return_value={"output": "analysis", "intermediate_steps": []}
        )
        result = await agent.run(mock_doc, "job_001")
        assert result["success"] is True
        agent.memory.get_best_pattern.assert_called_once_with(
            "document_processing", {"document_type": "academic_paper"}
        )
        agent.memory.remember_pattern.assert_called_once_with(
            "document_processing", {"document_type": "academic_paper"}, success=True
        )

    @pytest.mark.asyncio
    async def test_run_exception(self, agent, mock_doc):
        agent.executor = MagicMock()
        agent._execute_with_retry = MagicMock(side_effect=RuntimeError("boom"))
        result = await agent.run(mock_doc, "job_001")
        assert result["success"] is False
        assert result["error"] == "boom"
        assert result["should_fallback"] is True

    @pytest.mark.asyncio
    async def test_run_exception_with_memory(self, agent, mock_doc):
        agent.memory = MagicMock()
        agent.executor = MagicMock()
        agent._execute_with_retry = MagicMock(side_effect=RuntimeError("fail"))
        result = await agent.run(mock_doc, "job_001")
        assert result["success"] is False
        agent.memory.remember_error.assert_called_once_with(
            "agent_processing", "fail"
        )

    @pytest.mark.asyncio
    async def test_run_with_streaming(self, agent, mock_doc):
        agent.executor = MagicMock()
        agent.streaming_callback = MagicMock()
        agent.streaming_callback.get_events.return_value = [{"type": "test"}]
        agent._execute_with_retry = MagicMock(
            return_value={"output": "analysis", "intermediate_steps": []}
        )
        result = await agent.run(mock_doc, "job_001")
        assert result["streaming_events"] == [{"type": "test"}]

    @pytest.mark.asyncio
    async def test_run_no_document(self, agent):
        from app.pipeline.agents.document_agent import ValidationTool
        vt = MagicMock(spec=ValidationTool)
        vt.name = "validate_document"
        agent.tools = [vt]
        agent.executor = MagicMock()
        agent._execute_with_retry = MagicMock(
            return_value={"output": "analysis", "intermediate_steps": []}
        )
        result = await agent.run(None, "job_001")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_validation_tool_set(self, agent, mock_doc):
        from app.pipeline.agents.document_agent import ValidationTool
        vt = MagicMock(spec=ValidationTool)
        vt.name = "validate_document"
        agent.tools = [vt]
        agent.executor = MagicMock()
        agent._execute_with_retry = MagicMock(
            return_value={"output": "analysis", "intermediate_steps": []}
        )
        result = await agent.run(mock_doc, "job_001")
        vt.set_document.assert_called_once_with("doc_123", mock_doc)


# ==============================================================================
# DocumentAgent._execute_with_retry
# ==============================================================================

class TestExecuteWithRetry:
    """Tests for _execute_with_retry method."""

    def _make(self):
        from app.pipeline.agents.document_agent import DocumentAgent
        a = DocumentAgent.__new__(DocumentAgent)
        a.max_retries = 3
        a.memory = None
        a.streaming_callback = None
        a._agent_import_error = None
        a.executor = None
        return a

    def test_execute_success_first_try(self):
        agent = self._make()
        agent.executor = MagicMock()
        agent.executor.invoke.return_value = {"output": "result"}
        result = agent._execute_with_retry("input message")
        assert result["output"] == "result"
        agent.executor.invoke.assert_called_once_with({"input": "input message"})

    def test_execute_retry_then_success(self):
        agent = self._make()
        agent.executor = MagicMock()
        agent.executor.invoke.side_effect = [
            Exception("first fail"),
            {"output": "result"},
        ]
        result = agent._execute_with_retry("input")
        assert result["output"] == "result"
        assert agent.executor.invoke.call_count == 2

    def test_execute_all_retries_exhausted(self):
        agent = self._make()
        agent.executor = MagicMock()
        agent.executor.invoke.side_effect = Exception("always fail")
        with pytest.raises(Exception, match="always fail"):
            agent._execute_with_retry("input")
        assert agent.executor.invoke.call_count == 3

    def test_executor_none_raises(self):
        agent = self._make()
        agent.executor = None
        agent._agent_import_error = "no langchain"
        with pytest.raises(RuntimeError, match="Agent executor unavailable"):
            agent._execute_with_retry("input")

    def test_execute_with_memory_solution(self):
        agent = self._make()
        agent.memory = MagicMock()
        agent.memory.get_error_solution.side_effect = [
            "Try restarting GROBID",
            None,
        ]
        agent.executor = MagicMock()
        agent.executor.invoke.side_effect = [
            Exception("first fail"),
            Exception("second fail"),
            {"output": "result"},
        ]
        result = agent._execute_with_retry("input")
        assert result["output"] == "result"
        assert agent.memory.get_error_solution.call_count == 2

    def test_execute_with_streaming_clears_events(self):
        agent = self._make()
        agent.streaming_callback = MagicMock()
        agent.executor = MagicMock()
        agent.executor.invoke.side_effect = [
            Exception("first"),
            {"output": "result"},
        ]
        result = agent._execute_with_retry("input")
        assert result["output"] == "result"
        assert agent.streaming_callback.clear_events.call_count == 2


# ==============================================================================
# DocumentAgent._run_direct_fallback — edge cases
# ==============================================================================

class TestRunDirectFallbackEdge:
    """Edge cases for _run_direct_fallback."""

    def _make(self, tools):
        from app.pipeline.agents.document_agent import DocumentAgent
        a = DocumentAgent.__new__(DocumentAgent)
        a.tools = tools
        a.memory = None
        a.streaming_callback = None
        a._agent_import_error = None
        a.executor = None
        a.max_retries = 3
        return a

    def test_fallback_with_validation_tool_and_document(self):
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        vt = MagicMock(spec=ValidationTool)
        vt.name = "validation"
        vt._run.return_value = "valid"
        lt = MagicMock(spec=LayoutAnalysisTool)
        lt.name = "layout"
        lt._run.return_value = "layout"
        agent = self._make([vt, lt])
        doc = MagicMock()
        doc.document_id = "doc_1"
        result = agent._run_direct_fallback(document=doc, doc_path="/p.pdf")
        assert result["success"] is True

    def test_fallback_no_validation_tool_without_document(self):
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        ft = MagicMock(spec=FigureAnalysisTool)
        ft.name = "figures"
        ft._run.return_value = "figs"
        agent = self._make([ft])
        result = agent._run_direct_fallback(document=None, doc_path="/p.pdf")
        assert result["success"] is True

    def test_fallback_missing_metadata_tool(self):
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        rt = MagicMock(spec=ReferenceExtractionTool)
        rt.name = "refs"
        rt._run.return_value = "refs"
        agent = self._make([rt])
        result = agent._run_direct_fallback(None, "/p.pdf")
        assert result["success"] is True


# ==============================================================================
# DocumentAgent._should_fallback — edge cases
# ==============================================================================

class TestShouldFallbackEdge:
    def _make(self):
        from app.pipeline.agents.document_agent import DocumentAgent
        a = DocumentAgent.__new__(DocumentAgent)
        a.tools = []
        a.memory = None
        a.streaming_callback = None
        a.executor = None
        a.max_retries = 3
        return a

    def test_non_string_tool_output_does_not_crash(self):
        agent = self._make()
        steps = [("t1", 42), ("t2", "OK")]
        result = agent._should_fallback({"intermediate_steps": steps})
        assert result is False

    def test_short_step_tuples(self):
        agent = self._make()
        steps = [("t1", "OK"), ("t2",)]
        result = agent._should_fallback({"intermediate_steps": steps})
        assert result is False

    def test_empty_tuples(self):
        agent = self._make()
        steps = [(), ()]
        result = agent._should_fallback({"intermediate_steps": steps})
        assert result is False

    def test_exactly_half_error_rate(self):
        agent = self._make()
        steps = [("t1", "ERROR: fail"), ("t2", "OK")]
        result = agent._should_fallback({"intermediate_steps": steps})
        # 1/2 = 0.5, not > 0.5
        assert result is False


# ==============================================================================
# CustomLLMFactory — edge cases
# ==============================================================================

class TestCreateLLMEdge:
    """Edge cases for CustomLLMFactory.create_llm."""

    def test_force_langchain_openai_when_chatopenai_mocked(self):
        mock_cls = MagicMock()
        mock_llm = MagicMock()
        mock_cls.return_value = mock_llm
        with (
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True),
            patch("app.pipeline.agents.llm_factory._llm_generate", MagicMock()),
            patch("app.pipeline.agents.llm_factory.ChatOpenAI", mock_cls),
            patch("app.pipeline.agents.llm_factory.settings") as mock_settings,
        ):
            mock_settings.OPENAI_API_KEY = "sk-key"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
            assert llm is mock_llm

    def test_force_langchain_ollama_when_ollama_mocked(self):
        mock_cls = MagicMock()
        mock_llm = MagicMock()
        mock_cls.return_value = mock_llm
        with (
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True),
            patch("app.pipeline.agents.llm_factory._llm_generate", MagicMock()),
            patch("app.pipeline.agents.llm_factory.Ollama", mock_cls),
            patch("app.pipeline.agents.llm_factory.settings") as mock_settings,
        ):
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="ollama", model="llama2")
            assert llm is mock_llm

    def test_create_litellm_anthropic(self):
        with (
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True),
            patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen,
            patch("app.pipeline.agents.llm_factory._get_api_key", return_value="ant-key"),
        ):
            mock_gen.return_value = "ok"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(provider="anthropic", model="claude-3-opus")
            result = llm.invoke("hello")
            assert result.content == "ok"

    def test_create_langchain_openai_with_kwargs(self):
        mock_llm = MagicMock()
        mock_cls = MagicMock(return_value=mock_llm)
        with (
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False),
            patch("app.pipeline.agents.llm_factory.ChatOpenAI", mock_cls),
            patch("app.pipeline.agents.llm_factory.settings") as mock_settings,
        ):
            mock_settings.OPENAI_API_KEY = "sk-key"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(
                provider="openai", model="gpt-4", temperature=0.5,
                api_key="override", base_url="http://proxy"
            )
            assert llm is mock_llm
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs["api_key"] == "override"

    def test_create_langchain_ollama_with_kwargs(self):
        mock_llm = MagicMock()
        mock_cls = MagicMock(return_value=mock_llm)
        with (
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False),
            patch("app.pipeline.agents.llm_factory.Ollama", mock_cls),
            patch("app.pipeline.agents.llm_factory.settings") as mock_settings,
        ):
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(
                provider="ollama", model="llama2", base_url="http://custom:11434"
            )
            assert llm is mock_llm
            call_kwargs = mock_cls.call_args.kwargs
            assert "base_url" in call_kwargs

    def test_create_litellm_with_api_base_from_kwargs(self):
        with (
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True),
            patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen,
            patch("app.pipeline.agents.llm_factory._get_api_key", return_value="key"),
        ):
            mock_gen.return_value = "ok"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(
                provider="openai", model="gpt-4", base_url="http://proxy"
            )
            result = llm("hello")
            assert result == "ok"

    def test_create_litellm_with_api_key_from_kwargs(self):
        with (
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True),
            patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen,
        ):
            mock_gen.return_value = "ok"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            llm = CustomLLMFactory.create_llm(
                provider="openai", model="gpt-4", api_key="direct-key"
            )
            result = llm("hello")
            assert result == "ok"


# ==============================================================================
# CustomLLMFactory.get_available_providers
# ==============================================================================

class TestGetAvailableProvidersExtended:
    """Extended paths for get_available_providers."""

    def test_with_nvidia_key(self):
        with patch("app.pipeline.agents.llm_factory.settings") as mock_settings:
            mock_settings.NVIDIA_API_KEY = "nv-key"
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            providers = CustomLLMFactory.get_available_providers()
            assert "nvidia" in providers

    def test_anthropic_import_fails(self):
        with (
            patch("app.pipeline.agents.llm_factory.settings") as mock_settings,
            patch("app.pipeline.agents.llm_factory.sys.version_info", (3, 11)),
        ):
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = "ant-key"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "langchain_anthropic" in name:
                    raise ImportError("not installed")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                from app.pipeline.agents.llm_factory import CustomLLMFactory
                providers = CustomLLMFactory.get_available_providers()
            assert "anthropic" not in providers

    def test_ollama_connectivity_check_fails(self):
        with (
            patch("app.pipeline.agents.llm_factory.settings") as mock_settings,
            patch("requests.get") as mock_get,
        ):
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_get.side_effect = ConnectionError("refused")
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            providers = CustomLLMFactory.get_available_providers()
            assert "ollama" not in providers

    def test_litellm_available_added(self):
        with (
            patch("app.pipeline.agents.llm_factory.settings") as mock_settings,
            patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True),
        ):
            mock_settings.NVIDIA_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            providers = CustomLLMFactory.get_available_providers()
            assert "litellm" in providers


# ==============================================================================
# _LiteLLMShim — edge cases
# ==============================================================================

class TestLiteLLMShimEdge:
    """Edge cases for _LiteLLMShim."""

    def test_init_with_all_params(self):
        from app.pipeline.agents.llm_factory import _LiteLLMShim
        shim = _LiteLLMShim(
            model="gpt-4", temperature=0.5, api_key="key", api_base="http://base"
        )
        assert shim.model == "gpt-4"
        assert shim.temperature == 0.5
        assert shim.api_key == "key"
        assert shim.api_base == "http://base"

    def test_call_method(self):
        with patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen:
            mock_gen.return_value = "result"
            from app.pipeline.agents.llm_factory import _LiteLLMShim
            shim = _LiteLLMShim(model="m", temperature=0.0)
            output = shim("hello")
            assert output == "result"

    def test_invoke_passes_params_to_generate(self):
        with patch("app.pipeline.agents.llm_factory._llm_generate") as mock_gen:
            mock_gen.return_value = "text"
            from app.pipeline.agents.llm_factory import _LiteLLMShim
            shim = _LiteLLMShim(
                model="gpt-4", temperature=0.7, api_key="k", api_base="b"
            )
            shim.invoke("prompt")
            mock_gen.assert_called_once()
            kwargs = mock_gen.call_args.kwargs
            assert kwargs["model"] == "gpt-4"
            assert kwargs["temperature"] == 0.7
            assert kwargs["api_key"] == "k"
            assert kwargs["api_base"] == "b"

    def test_response_content(self):
        from app.pipeline.agents.llm_factory import _LiteLLMShim
        response = _LiteLLMShim._Response("hello")
        assert response.content == "hello"


# ==============================================================================
# _FallbackPromptTemplate — edge cases
# ==============================================================================

class TestFallbackPromptTemplateEdge:
    """Edge case: _FallbackPromptTemplate direct tests."""

    def test_fallback_format_handles_missing_key(self):
        from app.pipeline.agents.document_agent import _FallbackPromptTemplate
        pt = _FallbackPromptTemplate("Hello {name}")
        with pytest.raises(KeyError):
            pt.format(wrong="World")


# ==============================================================================
# AgentMemory — remaining edge cases
# ==============================================================================

class TestAgentMemoryEdge:
    """Edge cases to boost memory.py from 97% to ~100%."""

    def test_load_json_invalid_returns_default(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        d = tmp_path / "mem"
        d.mkdir()
        f = d / "patterns.json"
        f.write_text("invalid json")
        mem = AgentMemory(str(d))
        assert mem.patterns == {}

    def test_remember_error_updates_solution_on_duplicate(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_error("err", "msg")
        mem.remember_error("err", "msg", solution="new_sol")
        assert mem.errors[0]["solution"] == "new_sol"

    def test_get_error_solution_substring_match(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_error("parse", "failed_to_parse", solution="retry")
        result = mem.get_error_solution("parse", "Document failed_to_parse PDF")
        assert result == "retry"


# ==============================================================================
# StreamingAgentCallback — remaining edge cases
# ==============================================================================

class TestStreamingAgentCallbackEdge:
    """Edge cases to boost streaming.py beyond 81%."""

    def test_on_llm_error_with_exception(self):
        cb = MagicMock()
        from app.pipeline.agents.streaming import StreamingAgentCallback
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_llm_error(ValueError("test error"))
        cb.assert_called_once()
        assert cb.call_args[0][0] == "llm_error"

    def test_on_tool_error_with_runtime_error(self):
        cb = MagicMock()
        from app.pipeline.agents.streaming import StreamingAgentCallback
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_error(RuntimeError("tool crash"))
        cb.assert_called_once()
        assert "tool crash" in cb.call_args[0][1]["error"]

    def test_on_chain_error_with_exception(self):
        cb = MagicMock()
        from app.pipeline.agents.streaming import StreamingAgentCallback
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_chain_error(RuntimeError("chain fail"))
        cb.assert_called_once()
        assert "chain fail" in cb.call_args[0][1]["error"]
