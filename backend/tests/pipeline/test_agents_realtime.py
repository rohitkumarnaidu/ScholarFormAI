# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations

from unittest.mock import MagicMock, patch
import time
import pytest

pytestmark = [pytest.mark.pipeline]


class TestRealTimeAdaptiveAgentInit:
    def test_init_defaults(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        assert agent.base_timeout == 60.0
        assert agent.adaptation_callback is None
        assert agent.params["timeout"] == 60.0
        assert agent.params["retry_enabled"] is True
        assert agent.params["aggressive_mode"] is False
        assert agent.current_metrics["current_strategy"] == "default"

    def test_init_custom_timeout(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent(base_timeout=120.0)
        assert agent.base_timeout == 120.0
        assert agent.params["timeout"] == 120.0

    def test_init_with_callback(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        cb = MagicMock()
        agent = RealTimeAdaptiveAgent(adaptation_callback=cb)
        assert agent.adaptation_callback is cb

    def test_init_timeout_clamped_min(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent(base_timeout=1.0)
        assert agent.base_timeout == 10.0  # clamped to _MIN_TIMEOUT

    def test_init_timeout_clamped_max(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent(base_timeout=5000.0)
        assert agent.base_timeout == 1800.0  # clamped to _MAX_TIMEOUT

    def test_init_negative_timeout_raises(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        try:
            RealTimeAdaptiveAgent(base_timeout=-10.0)
            assert False
        except ValueError as e:
            assert "base_timeout" in str(e)

    def test_init_zero_timeout_raises(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        try:
            RealTimeAdaptiveAgent(base_timeout=0)
            assert False
        except ValueError as e:
            assert "base_timeout" in str(e)


class TestRealTimeAdaptiveAgentStartProcessing:
    def test_start_processing_valid(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_123")
        assert agent.current_metrics["document_id"] == "doc_123"
        assert agent.current_metrics["current_strategy"] == "default"
        assert agent.current_metrics["tools_executed"] == []
        assert agent.params["timeout"] == 60.0
        assert agent.params["retry_enabled"] is True

    def test_start_processing_empty_id(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("")
        assert agent.current_metrics["document_id"] == ""

    def test_start_processing_resets_metrics(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["tools_executed"].append("tool1")
        agent.params["aggressive_mode"] = True
        agent.start_processing("doc_2")
        assert agent.current_metrics["tools_executed"] == []
        assert agent.params["aggressive_mode"] is False


class TestRealTimeAdaptiveAgentRecordToolExecution:
    def test_record_successful_execution(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.record_tool_execution("extract", 5.0, True)
        assert len(agent.current_metrics["tools_executed"]) == 1
        assert len(agent.current_metrics["errors_encountered"]) == 0
        assert agent.current_metrics["tools_executed"][0]["tool"] == "extract"

    def test_record_failed_execution(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.record_tool_execution("extract", 5.0, False)
        assert len(agent.current_metrics["errors_encountered"]) == 1
        assert agent.current_metrics["errors_encountered"][0]["tool"] == "extract"

    def test_record_empty_tool_name(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.record_tool_execution("", 5.0, True)
        assert len(agent.current_metrics["tools_executed"]) == 0

    def test_record_updates_elapsed_time(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        with patch("app.pipeline.agents.realtime_adaptation.time.time", return_value=100.0):
            agent.start_processing("doc_1")
        with patch("app.pipeline.agents.realtime_adaptation.time.time", return_value=150.0):
            agent.record_tool_execution("tool1", 0.1, True)
        assert agent.current_metrics["elapsed_time"] == 50.0

    def test_record_exception_safe(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent._adapt_realtime = MagicMock(side_effect=RuntimeError("adapt fail"))
        agent.record_tool_execution("tool1", 0.1, True)


class TestRealTimeAdaptiveAgentAdaptRealtime:
    def test_adapt_timeout_when_elapsed_high(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent(base_timeout=60.0)
        agent.start_processing("doc_1")
        agent.current_metrics["elapsed_time"] = 50.0  # > 60 * 0.7 = 42
        agent._adapt_realtime()
        assert agent.params["aggressive_mode"] is True
        assert agent.params["timeout"] == 90.0  # 60 * 1.5

    def test_adapt_timeout_clamped(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent(base_timeout=1500.0)
        agent.start_processing("doc_1")
        agent.current_metrics["elapsed_time"] = 1400.0
        agent._adapt_realtime()
        assert agent.params["timeout"] <= 1800.0

    def test_adapt_strategy_on_multiple_errors(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["errors_encountered"] = [{"tool": "t1"}, {"tool": "t2"}]
        agent._adapt_realtime()
        assert agent.current_metrics["current_strategy"] == "fallback"
        assert agent.params["retry_enabled"] is False

    def test_adapt_strategy_only_once(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["current_strategy"] = "fallback"
        agent.current_metrics["errors_encountered"] = [{"tool": "t1"}, {"tool": "t2"}, {"tool": "t3"}]
        agent._adapt_realtime()
        assert agent.current_metrics["current_strategy"] == "fallback"

    def test_adapt_tool_priority(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["tools_executed"] = [
            {"tool": "tool_a", "success": True},
            {"tool": "tool_b", "success": False},
        ]
        agent._adapt_realtime()
        assert agent.params["tool_priority"] == ["tool_a"]

    def test_adapt_tool_priority_already_set(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.params["tool_priority"] = ["existing"]
        agent.current_metrics["tools_executed"] = [{"tool": "t1", "success": True}]
        agent._adapt_realtime()
        assert agent.params["tool_priority"] == ["existing"]

    def test_adapt_exception_safe(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.current_metrics = None
        agent._adapt_realtime()


class TestRealTimeAdaptiveAgentNotifyAdaptation:
    def test_notify_with_callback(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        cb = MagicMock()
        agent = RealTimeAdaptiveAgent(adaptation_callback=cb)
        agent._notify_adaptation("test_event", {"key": "value"})
        cb.assert_called_once_with("test_event", {"key": "value"})

    def test_notify_without_callback(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent._notify_adaptation("test_event", {"key": "value"})

    def test_notify_callback_exception(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        cb = MagicMock(side_effect=RuntimeError("callback fail"))
        agent = RealTimeAdaptiveAgent(adaptation_callback=cb)
        agent._notify_adaptation("test_event", {"key": "value"})

    def test_notify_non_callable_callback(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent(adaptation_callback="not_callable")
        agent._notify_adaptation("test_event", {"key": "value"})


class TestRealTimeAdaptiveAgentShouldContinue:
    def test_should_continue_normal(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        assert agent.should_continue() is True

    def test_should_continue_timeout_exceeded(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent(base_timeout=10.0)
        agent.start_processing("doc_1")
        agent.current_metrics["elapsed_time"] = 15.0
        assert agent.should_continue() is False

    def test_should_continue_too_many_errors(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["errors_encountered"] = [{"e": i} for i in range(6)]
        assert agent.should_continue() is False

    def test_should_continue_exception_safe(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.current_metrics = None
        assert agent.should_continue() is False


class TestRealTimeAdaptiveAgentGetCurrentParams:
    def test_get_current_params(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        params = agent.get_current_params()
        assert params["timeout"] == 60.0
        assert params["retry_enabled"] is True

    def test_get_current_params_returns_copy(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        params = agent.get_current_params()
        params["timeout"] = 999.0
        assert agent.params["timeout"] == 60.0

    def test_get_current_params_exception_safe(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.params = None
        assert agent.get_current_params() == {}


class TestRealTimeAdaptiveAgentGetMetrics:
    def test_get_metrics(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        metrics = agent.get_metrics()
        assert metrics["document_id"] == "doc_1"

    def test_get_metrics_returns_copy(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        metrics = agent.get_metrics()
        metrics["document_id"] = "changed"
        assert agent.current_metrics["document_id"] == "doc_1"

    def test_get_metrics_exception_safe(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.current_metrics = None
        assert agent.get_metrics() == {}


class TestRealTimeAdaptiveAgentRecommendNextTool:
    def test_recommend_with_priority(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.params["tool_priority"] = ["tool_a", "tool_b"]
        result = agent.recommend_next_tool(["tool_c", "tool_a", "tool_b"])
        assert result == "tool_a"

    def test_recommend_without_priority(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        result = agent.recommend_next_tool(["tool_x", "tool_y"])
        assert result == "tool_x"

    def test_recommend_empty_tools(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        result = agent.recommend_next_tool([])
        assert result is None

    def test_recommend_priority_not_in_available(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.params["tool_priority"] = ["tool_a", "tool_b"]
        result = agent.recommend_next_tool(["tool_c", "tool_d"])
        assert result == "tool_c"

    def test_recommend_exception_safe(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.params = None
        result = agent.recommend_next_tool(["tool_a"])
        assert result == "tool_a"

    def test_recommend_empty_tools_exception(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        agent = RealTimeAdaptiveAgent()
        agent.params = None
        result = agent.recommend_next_tool([])
        assert result is None
