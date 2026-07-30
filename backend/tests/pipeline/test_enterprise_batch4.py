# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Enterprise tests — Batch 4: agents/, orchestrator, intelligence/, services/."""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
import json
import pytest
from unittest.mock import MagicMock, PropertyMock, patch, call, AsyncMock


# ══════════════════════════════════════════════════════════════════════════════
# agents/metrics.py — PerformanceTracker + ProcessingMetrics
# ══════════════════════════════════════════════════════════════════════════════

class TestProcessingMetrics:
    def test_dataclass_defaults(self):
        from app.pipeline.agents.metrics import ProcessingMetrics
        m = ProcessingMetrics(
            document_id="doc1", orchestrator_type="agent",
            start_time=100.0, end_time=200.0, duration_seconds=100.0, success=True,
        )
        assert m.tools_used == []
        assert m.retry_count == 0
        assert m.fallback_triggered is False
        assert m.validation_errors == 0

    def test_to_dict(self):
        from app.pipeline.agents.metrics import ProcessingMetrics
        m = ProcessingMetrics(
            document_id="doc1", orchestrator_type="agent",
            start_time=100.0, end_time=200.0, duration_seconds=100.0, success=True,
            metadata_extracted=True, tools_used=["extract_metadata"],
        )
        d = m.to_dict()
        assert d["document_id"] == "doc1"
        assert d["tools_used"] == ["extract_metadata"]
        assert d["metadata_extracted"] is True


class TestPerformanceTracker:
    @pytest.fixture
    def tracker(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        return PerformanceTracker(metrics_dir=str(tmp_path))

    @pytest.fixture
    def tracker_with_metrics(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        return PerformanceTracker(metrics_dir=str(tmp_path))

    def test_init_creates_dir(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(metrics_dir=str(tmp_path / "my_metrics"))
        assert (tmp_path / "my_metrics").exists()

    def test_start_tracking(self, tracker):
        ctx = tracker.start_tracking("doc1", "agent")
        assert ctx["document_id"] == "doc1"
        assert ctx["orchestrator_type"] == "agent"
        assert ctx["tools_used"] == []
        assert ctx["retry_count"] == 0

    def test_record_tool_use(self, tracker):
        tracker.start_tracking("doc1", "agent")
        tracker.record_tool_use("extract_metadata")
        tracker.record_tool_use("analyze_layout")
        assert tracker.current_run["tools_used"] == ["extract_metadata", "analyze_layout"]

    def test_record_tool_use_no_current_run(self, tracker):
        tracker.record_tool_use("some_tool")

    def test_record_retry(self, tracker):
        tracker.start_tracking("doc1", "agent")
        tracker.record_retry()
        tracker.record_retry()
        assert tracker.current_run["retry_count"] == 2

    def test_record_retry_no_current_run(self, tracker):
        tracker.record_retry()

    def test_end_tracking_success(self, tracker_with_metrics):
        t = tracker_with_metrics
        t.start_tracking("doc1", "agent")
        t.record_tool_use("extract_metadata")
        result = t.end_tracking(success=True)
        assert result.document_id == "doc1"
        assert result.success is True
        assert result.orchestrator_type == "agent"
        assert result.tools_used == ["extract_metadata"]
        assert isinstance(result.duration_seconds, (int, float))

    def test_end_tracking_no_current_run(self, tracker_with_metrics):
        with pytest.raises(ValueError, match="No active tracking run"):
            tracker_with_metrics.end_tracking(success=True)

    def test_end_tracking_appends_to_file(self, tracker_with_metrics):
        t = tracker_with_metrics
        t.start_tracking("doc1", "agent")
        t.end_tracking(success=True)
        assert t.metrics_file.exists()
        lines = t.metrics_file.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_get_summary_empty(self, tracker_with_metrics):
        summary = tracker_with_metrics.get_summary()
        assert summary == {}

    def test_get_summary_with_data(self, tracker_with_metrics):
        t = tracker_with_metrics
        t.start_tracking("doc1", "agent")
        t.end_tracking(success=True)
        t.start_tracking("doc2", "legacy")
        t.end_tracking(success=False)
        summary = t.get_summary()
        assert summary["total_runs"] == 2
        assert summary["agent"]["count"] == 1
        assert summary["legacy"]["count"] == 1

    def test_get_comparison(self, tracker_with_metrics):
        t = tracker_with_metrics
        t.start_tracking("doc1", "agent")
        t.end_tracking(success=True)
        t.start_tracking("doc2", "legacy")
        t.end_tracking(success=True)
        comp = t.get_comparison()
        assert "agent_vs_legacy" in comp

    def test_load_all_metrics(self, tracker_with_metrics):
        t = tracker_with_metrics
        t.start_tracking("doc1", "agent")
        t.end_tracking(success=True)
        metrics = t.load_all_metrics()
        assert len(metrics) == 1
        assert metrics[0]["document_id"] == "doc1"

    def test_processing_metrics_from_end_tracking(self, tracker_with_metrics):
        t = tracker_with_metrics
        t.start_tracking("doc1", "agent")
        result = t.end_tracking(success=True, document=MagicMock(
            metadata=MagicMock(title="Test"),
            blocks=[MagicMock()],
            references=[MagicMock()],
            figures=[],
            validation_errors=[],
            validation_warnings=["warn"],
        ))
        assert result.metadata_extracted is True
        assert result.references_count == 1


# ══════════════════════════════════════════════════════════════════════════════
# agents/memory.py — AgentMemory
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentMemory:
    @pytest.fixture
    def memory(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        return AgentMemory(memory_dir=str(tmp_path / "agent_memory"))

    def test_init_creates_dir(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(memory_dir=str(tmp_path / "test_mem"))
        assert (tmp_path / "test_mem").exists()

    def test_remember_pattern(self, memory):
        memory.remember_pattern("document_processing", {"document_type": "academic_paper"}, success=True)
        assert "document_processing" in memory.patterns
        assert len(memory.patterns["document_processing"]["successful"]) == 1

    def test_remember_pattern_dedup(self, memory):
        memory.remember_pattern("document_processing", {"document_type": "academic_paper"}, success=True)
        memory.remember_pattern("document_processing", {"document_type": "academic_paper"}, success=True)
        assert len(memory.patterns["document_processing"]["successful"]) == 1
        assert memory.patterns["document_processing"]["successful"][0]["count"] == 2

    def test_remember_error(self, memory):
        memory.remember_error("processing", "Something went wrong")
        assert len(memory.errors) == 1
        assert memory.errors[0]["type"] == "processing"

    def test_remember_error_with_solution(self, memory):
        memory.remember_error("processing", "Error", solution="Retry with backoff")
        assert memory.errors[0]["solution"] == "Retry with backoff"

    def test_get_error_solution_found(self, memory):
        memory.remember_error("execution_error", "timeout", solution="Increase timeout")
        sol = memory.get_error_solution("execution_error", "timeout")
        assert sol == "Increase timeout"

    def test_get_error_solution_not_found(self, memory):
        sol = memory.get_error_solution("nonexistent", "nope")
        assert sol is None

    def test_record_metric(self, memory):
        memory.record_metric("processing_time", 42.5)
        assert "processing_time" in memory.metrics
        assert memory.metrics["processing_time"]["average"] == 42.5

    def test_record_metric_multiple(self, memory):
        memory.record_metric("processing_time", 40.0)
        memory.record_metric("processing_time", 50.0)
        assert memory.metrics["processing_time"]["count"] == 2
        assert memory.metrics["processing_time"]["average"] == 45.0

    def test_remember_correction(self, memory):
        memory.remember_correction("doc123", "title", "Fig.", "Figure")
        assert len(memory.corrections) == 1
        assert memory.corrections[0]["original"] == "Fig."
        assert memory.corrections[0]["corrected"] == "Figure"

    def test_get_best_pattern_found(self, memory):
        memory.remember_pattern("document_processing", {"document_type": "academic_paper"}, success=True)
        pattern = memory.get_best_pattern("document_processing", {"document_type": "academic_paper"})
        assert pattern is not None

    def test_get_best_pattern_not_found(self, memory):
        pattern = memory.get_best_pattern("nonexistent", {})
        assert pattern is None

    def test_format_memory_summary(self, memory):
        memory.remember_pattern("doc_proc", {"document_type": "paper"}, success=True)
        summary = memory.format_memory_summary()
        assert isinstance(summary, str)

    def test_format_memory_summary_no_patterns(self, memory):
        summary = memory.format_memory_summary()
        assert "(none)" in summary


# ══════════════════════════════════════════════════════════════════════════════
# agents/adaptive.py — AdaptiveStrategy
# ══════════════════════════════════════════════════════════════════════════════

class TestAdaptiveStrategy:
    @pytest.fixture
    def strategy(self):
        from app.pipeline.agents.metrics import PerformanceTracker
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock(spec=PerformanceTracker)
        return AdaptiveStrategy(tracker)

    def test_init_requires_tracker(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        with pytest.raises(ValueError, match="tracker must not be None"):
            AdaptiveStrategy(tracker=None)

    def test_default_config_retries(self, strategy):
        assert strategy.config["max_retries"] == 3
        assert strategy.config["timeout_seconds"] == 60
        assert strategy.config["fallback_threshold"] == 0.5

    def test_adapt_returns_config_on_exception(self, strategy):
        strategy.tracker.get_summary.side_effect = Exception("fail")
        result = strategy.adapt()
        assert result["max_retries"] == 3

    def test_adapt_returns_default_when_no_summary(self, strategy):
        strategy.tracker.get_summary.return_value = {}
        result = strategy.adapt()
        assert result["max_retries"] == 3

    def test_adapt_increases_retries_on_low_success(self, strategy):
        strategy.tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.5, "total": 10},
            "legacy": {"success_rate": 0.9, "total": 10},
        }
        result = strategy.adapt()
        assert result["max_retries"] == 4

    def test_adapt_decreases_retries_on_high_success(self, strategy):
        strategy.tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.95, "total": 10},
            "legacy": {"success_rate": 0.9, "total": 10},
        }
        result = strategy.adapt()
        assert result["max_retries"] == 3

    def test_get_config(self, strategy):
        cfg = strategy.get_config()
        assert cfg["max_retries"] == 3

    def test_adapt_with_ml_detector(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        from app.pipeline.agents.metrics import PerformanceTracker
        tracker = MagicMock(spec=PerformanceTracker)
        ml_detector = MagicMock()
        ml_detector.patterns = [{"success_rate": 0.9, "common_tools": ["tool1"]}]
        ml_detector.get_pattern_summary.return_value = {"patterns": [{"success_rate": 0.9, "common_tools": ["tool1"]}]}
        strategy = AdaptiveStrategy(tracker, ml_detector=ml_detector)
        result = strategy.adapt()
        assert "tool_priority" in result


# ══════════════════════════════════════════════════════════════════════════════
# agents/dashboard.py — ComparisonDashboard
# ══════════════════════════════════════════════════════════════════════════════

class TestComparisonDashboard:
    @pytest.fixture
    def dashboard(self):
        from app.pipeline.agents.dashboard import ComparisonDashboard
        from app.pipeline.agents.metrics import PerformanceTracker
        tracker = MagicMock(spec=PerformanceTracker)
        tracker.get_summary.return_value = {
            "total_runs": 2, "agent": {"total": 1, "successful": 1},
            "legacy": {"total": 1, "successful": 0},
        }
        tracker.get_comparison.return_value = {"agent_vs_legacy": {}}
        return ComparisonDashboard(tracker)

    def test_generate_html(self, dashboard, tmp_path):
        out = str(tmp_path / "dash.html")
        result = dashboard.generate_html(output_path=out)
        assert result == out
        assert (tmp_path / "dash.html").exists()

    def test_build_html_contains_stats(self, dashboard):
        html = dashboard._build_html(
            {"agent": {"total": 1, "successful": 1}, "legacy": {"total": 1, "successful": 0}},
            {"agent_vs_legacy": {}},
        )
        assert "Performance" in html or "agent" in html.lower()

    def test_build_html_empty_stats(self, dashboard):
        html = dashboard._build_html({}, {})
        assert isinstance(html, str)


# ══════════════════════════════════════════════════════════════════════════════
# agents/streaming.py — StreamingAgentCallback
# ══════════════════════════════════════════════════════════════════════════════

class TestStreamingAgentCallback:
    @pytest.fixture
    def callback(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        return StreamingAgentCallback(callback_fn=fn), fn

    def test_default_callback_logs_event(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = StreamingAgentCallback()
        cb._default_callback("test", {"msg": "hello"})
        assert len(cb.events) == 1
        assert cb.events[0]["type"] == "test"

    def test_on_llm_start(self, callback):
        cb, fn = callback
        cb.on_llm_start({}, ["prompt1"])
        fn.assert_called_once()
        args = fn.call_args[0]
        assert args[0] == "llm_start"

    def test_on_llm_end(self, callback):
        cb, fn = callback
        response = MagicMock()
        response.generations = [MagicMock()]
        cb.on_llm_end(response)
        fn.assert_called_once_with("llm_end", {"message": "Agent decision made", "generations": 1})

    def test_on_llm_error(self, callback):
        cb, fn = callback
        cb.on_llm_error(Exception("fail"))
        fn.assert_called_once()

    def test_on_tool_start(self, callback):
        cb, fn = callback
        cb.on_tool_start({"name": "test_tool"}, "input data")
        fn.assert_called_once()

    def test_on_tool_end(self, callback):
        cb, fn = callback
        cb.on_tool_end("output result")
        fn.assert_called_once_with("tool_end", {"message": "Tool execution complete", "output_preview": "output result"})

    def test_on_tool_error(self, callback):
        cb, fn = callback
        cb.on_tool_error(Exception("tool fail"))
        fn.assert_called_once()

    def test_on_agent_action(self, callback):
        cb, fn = callback
        action = MagicMock()
        action.tool = "extract_metadata"
        action.tool_input = {"file_path": "/tmp/doc.pdf"}
        action.log = "Thought: I need to extract metadata"
        cb.on_agent_action(action)
        fn.assert_called_once()

    def test_on_agent_finish(self, callback):
        cb, fn = callback
        finish = MagicMock()
        finish.return_values = {"output": "done"}
        cb.on_agent_finish(finish)
        fn.assert_called_once()

    def test_on_chain_start(self, callback):
        cb, fn = callback
        cb.on_chain_start({"name": "main_chain"}, {})
        fn.assert_called_once()

    def test_on_chain_end(self, callback):
        cb, fn = callback
        cb.on_chain_end({})
        fn.assert_called_once()

    def test_on_chain_error(self, callback):
        cb, fn = callback
        cb.on_chain_error(Exception("chain fail"))
        fn.assert_called_once()

    def test_get_events_with_default_callback(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = StreamingAgentCallback()
        cb.on_llm_start({}, ["prompt"])
        events = cb.get_events()
        assert len(events) == 1
        assert events[0]["type"] == "llm_start"

    def test_clear_events(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = StreamingAgentCallback()
        cb.on_llm_start({}, ["prompt"])
        cb.clear_events()
        assert len(cb.get_events()) == 0


# ══════════════════════════════════════════════════════════════════════════════
# agents/llm_factory.py — CustomLLMFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestCustomLLMFactory:
    def test_get_available_providers(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        providers = CustomLLMFactory.get_available_providers()
        assert isinstance(providers, list)

    def test_get_recommended_models_openai(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        models = CustomLLMFactory.get_recommended_models("openai")
        assert "gpt-4" in models

    def test_get_recommended_models_unknown(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        models = CustomLLMFactory.get_recommended_models("nonexistent")
        assert models == []


# ══════════════════════════════════════════════════════════════════════════════
# agents/document_agent.py — DocumentAgent
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentAgent:
    @pytest.fixture
    def agent(self):
        with patch("app.pipeline.agents.document_agent.settings") as mock_settings:
            mock_settings.GROBID_URL = "http://localhost:8070"
            from app.pipeline.agents.document_agent import DocumentAgent
            with patch.object(DocumentAgent, "_initialize_executor"):
                a = DocumentAgent(llm_provider="openai", enable_memory=False, enable_streaming=False)
                return a

    def test_init_defaults(self, agent):
        assert agent.max_retries == 3
        assert agent.memory is None
        assert agent.streaming_callback is None
        assert len(agent.tools) == 5

    def test_should_fallback_no_steps(self, agent):
        result = agent._should_fallback({"intermediate_steps": []})
        assert result is False

    def test_should_fallback_high_error_rate(self, agent):
        result = agent._should_fallback({
            "intermediate_steps": [
                ("tool1", "SUCCESS"),
                ("tool2", "ERROR: failed"),
                ("tool3", "ERROR: failed"),
            ]
        })
        assert result is True

    def test_should_fallback_low_error_rate(self, agent):
        result = agent._should_fallback({
            "intermediate_steps": [
                ("tool1", "SUCCESS"),
                ("tool2", "SUCCESS"),
                ("tool3", "ERROR: fail"),
            ]
        })
        assert result is False

    def test_process_document_returns_dict(self, agent):
        with patch.object(agent, "_execute_with_retry", return_value={"output": "analysis", "intermediate_steps": []}):
            result = agent.process_document("/path/to/doc.pdf")
            assert result["success"] is True
            assert "analysis" in result

    @pytest.mark.asyncio
    async def test_run_direct_fallback(self, agent):
        for tool in agent.tools:
            tool._run = MagicMock(return_value="tool output")
        result = agent._run_direct_fallback(document=MagicMock(document_id="doc1"), doc_path="/path/doc.pdf")
        assert result["success"] is True

    def test_execute_with_retry_executor_unavailable(self, agent):
        agent.executor = None
        agent._agent_import_error = "No executor"
        with pytest.raises(RuntimeError, match="Agent executor unavailable"):
            agent._execute_with_retry("test")


# ══════════════════════════════════════════════════════════════════════════════
# intelligence/reasoning_engine.py — ReasoningEngine (unit tests, no LLMs)
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningEngine:
    @pytest.fixture
    def engine(self):
        with patch("app.pipeline.intelligence.reasoning_engine.settings") as ms:
            ms.PIPELINE_REASONING_TIMEOUT_SECONDS = 30
            ms.OLLAMA_BASE_URL = "http://localhost:11434"
            from app.pipeline.intelligence.reasoning_engine import ReasoningEngine
            with patch.object(ReasoningEngine, "_check_ollama_health", return_value=False):
                e = ReasoningEngine(timeout=30, model="deepseek-r1:8b")
                return e

    def test_init_defaults(self, engine):
        assert engine.timeout == 30
        assert engine.ollama_available is False
        assert engine.llm is None

    def test_is_cancelled_none(self, engine):
        assert engine._is_cancelled(None) is False

    def test_is_cancelled_set(self, engine):
        event = MagicMock()
        event.is_set.return_value = True
        assert engine._is_cancelled(event) is True

    def test_is_cancelled_no_is_set(self, engine):
        assert engine._is_cancelled("not_an_event") is False

    def test_validate_json_schema_valid(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": 0.9}]}
        assert engine._validate_json_schema(data) is True

    def test_validate_json_schema_no_blocks(self, engine):
        assert engine._validate_json_schema({}) is False

    def test_validate_json_schema_error_key(self, engine):
        assert engine._validate_json_schema({"error": "fail"}) is False

    def test_validate_json_schema_bad_block(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "", "confidence": 0.9}]}
        assert engine._validate_json_schema(data) is False

    def test_validate_json_schema_bad_confidence(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": 1.5}]}
        assert engine._validate_json_schema(data) is False

    def test_normalize_semantic_type_body(self, engine):
        assert engine._normalize_semantic_type("BODY_TEXT") == "BODY"

    def test_normalize_semantic_type_none(self, engine):
        assert engine._normalize_semantic_type(None) == "BODY"

    def test_normalize_semantic_type_abstract(self, engine):
        assert engine._normalize_semantic_type("abstract") == "ABSTRACT_BODY"

    def test_normalize_semantic_type_reference(self, engine):
        assert engine._normalize_semantic_type("bibliography_entry") == "REFERENCE_ENTRY"

    def test_normalize_semantic_type_heading(self, engine):
        assert engine._normalize_semantic_type("section_heading") == "HEADING_1"

    def test_normalize_confidence_valid(self, engine):
        assert engine._normalize_confidence(0.85) == 0.85

    def test_normalize_confidence_none(self, engine):
        assert engine._normalize_confidence(None) == 0.72

    def test_normalize_confidence_out_of_range(self, engine):
        assert engine._normalize_confidence(1.5) == 1.0
        assert engine._normalize_confidence(-0.1) == 0.0

    def test_rule_based_fallback_heading(self, engine):
        blocks = [{"block_id": "b1", "text": "Introduction:", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["fallback"] is True
        assert result["blocks"][0]["semantic_type"] == "HEADING_1"

    def test_rule_based_fallback_abstract(self, engine):
        blocks = [{"block_id": "b1", "text": "Abstract: This paper...", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert "ABSTRACT" in result["blocks"][0]["semantic_type"]

    def test_rule_based_fallback_reference(self, engine):
        blocks = [{"block_id": "b1", "text": "References go here", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["blocks"][0]["semantic_type"] == "REFERENCE_ENTRY"

    def test_normalize_instruction_payload_none(self, engine):
        assert engine._normalize_instruction_payload(None, []) is None

    def test_normalize_instruction_payload_basic(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": 0.9}]}
        result = engine._normalize_instruction_payload(data, [{"block_id": "b1"}])
        assert result is not None
        assert len(result["blocks"]) == 1

    def test_normalize_instruction_payload_instructions_fallback(self, engine):
        data = {"instructions": [{"block_id": "b1", "type": "BODY", "score": 0.8}]}
        result = engine._normalize_instruction_payload(data, [{}])
        assert result is not None
        assert result["blocks"][0]["semantic_type"] == "BODY"

    def test_normalize_instruction_payload_empty(self, engine):
        data = {"blocks": []}
        result = engine._normalize_instruction_payload(data, [])
        assert result is None or result["blocks"] == []

    def test_generate_instruction_set_cancelled(self, engine):
        event = MagicMock()
        event.is_set.return_value = True
        result = engine.generate_instruction_set([{"block_id": "b1", "text": "Hello"}], "", cancellation_event=event)
        assert result.get("fallback") is True


# ══════════════════════════════════════════════════════════════════════════════
# intelligence/semantic_parser.py — SemanticParser
# ══════════════════════════════════════════════════════════════════════════════

class TestSemanticParser:
    @pytest.fixture
    def parser(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser
        with patch.object(SemanticParser, "_load_model"):
            return SemanticParser(model_name="__heuristic_fallback__")

    def test_init_with_heuristic(self, parser):
        assert parser.model_name == "__heuristic_fallback__"
        assert parser._is_loaded is False

    def test_detect_boundaries_passes_through_on_empty(self, parser):
        result = parser.detect_boundaries([])
        assert result == []

    def test_reconcile_fragmented_headings_empty(self, parser):
        result = parser.reconcile_fragmented_headings([])
        assert result == []

    def test_heuristic_classify_long_text_is_body(self, parser):
        result = parser._heuristic_classify("This is a very long body paragraph that should be classified as body text since it exceeds the 150 character threshold for heading detection. More text to make it long enough.")
        assert result["type"] == "BODY"

    def test_heuristic_classify_short_text_heading(self, parser):
        result = parser._heuristic_classify("Introduction")
        assert result["type"] == "HEADING"

    def test_heuristic_classify_abstract(self, parser):
        result = parser._heuristic_classify("Abstract: This paper...")
        assert result["type"] == "ABSTRACT"

    def test_heuristic_classify_references(self, parser):
        result = parser._heuristic_classify("References")
        assert result["type"] == "REFERENCES"

    def test_heuristic_classify_bibliography(self, parser):
        result = parser._heuristic_classify("Bibliography")
        assert result["type"] == "REFERENCES"

    def test_heuristic_classify_acknowledgements(self, parser):
        result = parser._heuristic_classify("Acknowledgements")
        assert result["type"] == "ACKNOWLEDGEMENTS"

    def test_heuristic_classify_methodology(self, parser):
        result = parser._heuristic_classify("Methodology")
        assert result["type"] == "METHODOLOGY"

    def test_heuristic_classify_conclusion(self, parser):
        result = parser._heuristic_classify("Conclusion")
        assert result["type"] == "CONCLUSION"

    def test_heuristic_classify_introduction(self, parser):
        result = parser._heuristic_classify("Introduction")
        assert result["type"] == "HEADING"

    def test_heuristic_classify_figure_caption(self, parser):
        result = parser._heuristic_classify("Figure 1: Results")
        assert result["type"] == "FIGURE_CAPTION"

    def test_heuristic_classify_table_caption(self, parser):
        result = parser._heuristic_classify("Table 1: Data")
        assert result["type"] == "TABLE_CAPTION"

    def test_heuristic_classify_heading_by_case(self, parser):
        result = parser._heuristic_classify("Short Title")
        assert result["type"] == "HEADING"

    def test_repair_fragmented_headings(self, parser):
        b1 = MagicMock()
        b1.text = "1"
        b2 = MagicMock()
        b2.text = "introduction"
        result = parser._repair_fragmented_headings([b1, b2])
        assert len(result) == 1
        assert result[0].text == "1. introduction"

    def test_repair_fragmented_headings_no_fix(self, parser):
        b1 = MagicMock()
        b1.text = "Introduction"
        b2 = MagicMock()
        b2.text = "This is the body"
        result = parser._repair_fragmented_headings([b1, b2])
        assert len(result) == 2

    def test_classify_block_heuristic(self, parser):
        result = parser.classify_block("Abstract", use_transformer=False)
        assert result["type"] == "ABSTRACT"

    def test_ordered_remote_urls_uses_own_list(self, parser):
        parser.remote_base_urls = []
        assert parser._ordered_remote_urls() == []

    def test_ordered_remote_urls_prefers_last_good(self, parser):
        parser.remote_base_urls = ["http://scibert1", "http://scibert2"]
        parser._last_good_remote_url = "http://scibert1"
        parser._last_good_remote_at = 9999999999.0
        ordered = parser._ordered_remote_urls()
        assert ordered[0] == "http://scibert1"

    def test_normalize_remote_prediction_valid(self, parser):
        result = parser._normalize_remote_prediction({"type": "BODY", "confidence": 0.9})
        assert result == {"type": "BODY", "confidence": 0.9}

    def test_normalize_remote_prediction_none(self, parser):
        assert parser._normalize_remote_prediction(None) is None

    def test_normalize_remote_prediction_no_label(self, parser):
        assert parser._normalize_remote_prediction({"score": 0.5}) is None

    def test_predict_block_types_batch_empty(self, parser):
        assert parser._predict_block_types_batch([]) == []


# ══════════════════════════════════════════════════════════════════════════════
# orchestrator.py — PipelineOrchestrator (utility methods)
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineOrchestrator:
    @pytest.fixture
    def orch(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        with patch.multiple(
            "app.pipeline.orchestrator",
            InputConverter=MagicMock,
            ContentAnalyzer=MagicMock,
            ContractLoader=MagicMock,
            GROBIDClient=MagicMock,
            DoclingClient=MagicMock,
        ):
            return PipelineOrchestrator(templates_dir=str("/tmp/templates"), temp_dir=str("/tmp/pipeline_temp"))

    def test_init(self, orch):
        assert orch.temp_dir == str("/tmp/pipeline_temp")

    def test_coerce_bool_none(self, orch):
        assert orch._coerce_bool(None, default=True) is True

    def test_coerce_bool_bool(self, orch):
        assert orch._coerce_bool(True) is True
        assert orch._coerce_bool(False) is False

    def test_coerce_bool_int(self, orch):
        assert orch._coerce_bool(1) is True
        assert orch._coerce_bool(0) is False

    def test_coerce_bool_string_true(self, orch):
        assert orch._coerce_bool("true") is True
        assert orch._coerce_bool("yes") is True
        assert orch._coerce_bool("1") is True

    def test_coerce_bool_string_false(self, orch):
        assert orch._coerce_bool("false") is False
        assert orch._coerce_bool("no") is False

    def test_coerce_bool_unknown(self, orch):
        assert orch._coerce_bool("maybe") is False

    def test_check_stage_interface_pass(self, orch):
        instance = MagicMock()
        instance.process = MagicMock()
        orch._check_stage_interface(instance, "process", "TestStage")

    def test_check_stage_interface_fail(self, orch):
        instance = MagicMock()
        with pytest.raises(RuntimeError, match="does not implement required method"):
            orch._check_stage_interface(instance, "nonexistent", "BadStage")

    def test_compute_sha256(self, orch, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        h = orch._compute_sha256(str(f))
        assert len(h) == 64
        assert isinstance(h, str)

    def test_resolve_runtime_flags_defaults(self, orch):
        with patch("app.pipeline.orchestrator.settings") as ms:
            ms.DEFAULT_FAST_MODE = False
            ms.LOW_MEMORY_MODE = False
            flags = orch._resolve_runtime_flags({})
            assert "fast_mode" in flags
            assert "semantic_parser" in flags
            assert "crossref_enrichment" in flags
            assert "ai_reasoning" in flags

    def test_resolve_runtime_flags_fast_mode_true(self, orch):
        with patch("app.pipeline.orchestrator.settings") as ms:
            ms.DEFAULT_FAST_MODE = False
            ms.LOW_MEMORY_MODE = False
            flags = orch._resolve_runtime_flags({"fast_mode": True})
            assert flags["fast_mode"] is True
            assert flags["semantic_parser"] is False

    def test_resolve_runtime_flags_in_pytest(self, orch):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "True"}):
            with patch("app.pipeline.orchestrator.settings") as ms:
                ms.DEFAULT_FAST_MODE = False
                ms.LOW_MEMORY_MODE = False
                flags = orch._resolve_runtime_flags({})
                assert flags["fast_mode"] is True

    def test_sync_block_confidence_no_blocks(self, orch):
        doc = MagicMock()
        doc.blocks = []
        orch._sync_block_confidence(doc)

    def test_sync_block_confidence_with_confidence(self, orch):
        block = MagicMock()
        block.metadata = {"classification_confidence": 0.85}
        block.semantic_intent = None
        doc = MagicMock()
        doc.blocks = [block]
        orch._sync_block_confidence(doc)
        assert block.metadata["nlp_confidence"] == 0.85

    def test_sync_block_confidence_invalid(self, orch):
        block = MagicMock(spec=[])
        del block.semantic_intent
        block.metadata = {"classification_confidence": None}
        type(block).classification_confidence = PropertyMock(return_value="invalid")
        doc = MagicMock()
        doc.blocks = [block]
        orch._sync_block_confidence(doc)

    def test_build_quality_summary_no_blocks(self, orch):
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        doc.template = None
        doc.review = None
        result = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert "quality_score" in result
        assert isinstance(result["quality_score"], float)

    def test_build_quality_summary_with_data(self, orch):
        block = MagicMock()
        block.metadata = {"classification_confidence": 0.9, "is_heading_candidate": True}
        doc = MagicMock()
        doc.blocks = [block]
        doc.figures = [MagicMock()]
        doc.tables = []
        doc.template.template_name = "ieee"
        doc.review = MagicMock()
        doc.review.status = "approved"
        result = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert result["heading_candidates"] >= 1

    def test_should_skip_docling_for_digital_pdf_empty_path(self, orch):
        with patch("app.pipeline.orchestrator.settings") as ms:
            ms.PIPELINE_DOCLING_FORCE = False
            ms.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = False
            result = orch._should_skip_docling_for_digital_pdf("")
            assert result is False

    @patch("app.pipeline.orchestrator.fitz", None)
    def test_extract_pymupdf_fallback_metadata_no_fitz(self, orch):
        result = orch._extract_pymupdf_fallback_metadata("/nonexistent.pdf")
        assert result == {}

    def test_log_quality_summary(self, orch):
        orch._log_quality_summary("job1", {
            "quality_score": 85.0, "avg_confidence": 0.8, "min_confidence": 0.6,
            "block_count": 10, "heading_candidates": 3, "figures": 1, "tables": 0,
            "errors": 1, "warnings": 2, "low_conf_blocks": 0, "review_status": "pending",
        })

    def test_check_stage_interface_method_name(self, orch):
        instance = MagicMock()
        instance.some_method = MagicMock()
        orch._check_stage_interface(instance, "some_method", "TestStage")
