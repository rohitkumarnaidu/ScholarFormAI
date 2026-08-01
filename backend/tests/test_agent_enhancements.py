# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for agent enhancements.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.pipeline.agents.dashboard import ComparisonDashboard
from app.pipeline.agents.llm_factory import CustomLLMFactory
from app.pipeline.agents.memory import AgentMemory
from app.pipeline.agents.metrics import PerformanceTracker
from app.pipeline.agents.streaming import StreamingAgentCallback


class TestAgentMemory:
    """Test agent memory system."""
    
    def test_remember_pattern(self, tmp_path):
        """Test pattern memory."""
        memory = AgentMemory(memory_dir=str(tmp_path))
        
        context = {"document_type": "research_paper"}
        memory.remember_pattern("extraction", context, success=True)
        
        # Verify pattern was saved
        assert "extraction" in memory.patterns
        assert len(memory.patterns["extraction"]["successful"]) == 1
    
    def test_remember_error(self, tmp_path):
        """Test error memory."""
        memory = AgentMemory(memory_dir=str(tmp_path))
        
        memory.remember_error("timeout", "Connection timeout", solution="Retry with backoff")
        
        # Verify error was saved
        assert len(memory.errors) == 1
        assert memory.errors[0]["solution"] == "Retry with backoff"
    
    def test_get_best_pattern(self, tmp_path):
        """Test retrieving best pattern."""
        memory = AgentMemory(memory_dir=str(tmp_path))
        
        context = {"document_type": "thesis"}
        memory.remember_pattern("processing", context, success=True)
        
        best = memory.get_best_pattern("processing", context)
        assert best is not None
        assert best["context"]["document_type"] == "thesis"
    
    def test_record_metric(self, tmp_path):
        """Test metric recording."""
        memory = AgentMemory(memory_dir=str(tmp_path))
        
        memory.record_metric("processing_time", 5.2, {"doc_type": "paper"})
        memory.record_metric("processing_time", 4.8, {"doc_type": "paper"})
        
        summary = memory.get_metric_summary("processing_time")
        assert summary is not None
        assert summary["count"] == 2
        assert 4.5 < summary["average"] < 5.5


class TestStreamingCallback:
    """Test streaming callback handler."""
    
    def test_callback_events(self):
        """Test event recording."""
        events = []
        
        def callback(event_type, data):
            events.append({"type": event_type, "data": data})
        
        handler = StreamingAgentCallback(callback_fn=callback)
        
        # Simulate events
        handler.on_llm_start({}, ["prompt"])
        handler.on_tool_start({"name": "test_tool"}, "input")
        handler.on_tool_end("output")
        
        assert len(events) == 3
        assert events[0]["type"] == "llm_start"
        assert events[1]["type"] == "tool_start"
        assert events[2]["type"] == "tool_end"
    
    def test_get_events(self):
        """Test event retrieval."""
        handler = StreamingAgentCallback()
        
        handler.on_llm_start({}, ["prompt"])
        handler.on_agent_finish(MagicMock(return_values={"output": "done"}))
        
        events = handler.get_events()
        assert len(events) == 2


class TestCustomLLMFactory:
    """Test custom LLM factory."""
    
    @patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"})
    @patch('app.pipeline.agents.llm_factory.ChatOpenAI')
    def test_create_openai_llm(self, mock_openai):
        """Test OpenAI LLM creation."""
        CustomLLMFactory.create_llm(provider="openai", model="gpt-4")
        
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
    
    @patch('app.pipeline.agents.llm_factory.Ollama')
    def test_create_ollama_llm(self, mock_ollama):
        """Test Ollama LLM creation."""
        CustomLLMFactory.create_llm(
            provider="ollama",
            model="llama2",
            base_url="http://localhost:11434"
        )
        
        mock_ollama.assert_called_once()
        call_kwargs = mock_ollama.call_args[1]
        assert call_kwargs["model"] == "llama2"
        assert call_kwargs["base_url"] == "http://localhost:11434"
    
    def test_get_recommended_models(self):
        """Test model recommendations."""
        models = CustomLLMFactory.get_recommended_models("openai")
        assert "gpt-4" in models
        
        ollama_models = CustomLLMFactory.get_recommended_models("ollama")
        assert "llama2" in ollama_models


class TestPerformanceTracker:
    """Test performance metrics tracking."""
    
    def test_start_end_tracking(self, tmp_path):
        """Test basic tracking flow."""
        tracker = PerformanceTracker(metrics_dir=str(tmp_path))
        
        # Start tracking
        run = tracker.start_tracking("doc_123", "agent")
        assert run["document_id"] == "doc_123"
        
        # End tracking
        metrics = tracker.end_tracking(success=True)
        assert metrics.success is True
        assert metrics.document_id == "doc_123"
    
    def test_record_tool_use(self, tmp_path):
        """Test tool usage recording."""
        tracker = PerformanceTracker(metrics_dir=str(tmp_path))
        
        tracker.start_tracking("doc_123", "agent")
        tracker.record_tool_use("metadata_tool")
        tracker.record_tool_use("layout_tool")
        
        metrics = tracker.end_tracking(success=True)
        assert len(metrics.tools_used) == 2
    
    def test_get_comparison(self, tmp_path):
        """Test agent vs legacy comparison."""
        tracker = PerformanceTracker(metrics_dir=str(tmp_path))
        
        # Simulate agent run
        tracker.start_tracking("doc_1", "agent")
        tracker.end_tracking(success=True)
        
        # Simulate legacy run
        tracker.start_tracking("doc_2", "legacy")
        tracker.end_tracking(success=True)
        
        comparison = tracker.get_comparison()
        assert "agent_vs_legacy" in comparison


class TestComparisonDashboard:
    """Test comparison dashboard generator."""
    
    def test_generate_html(self, tmp_path):
        """Test HTML dashboard generation."""
        tracker = PerformanceTracker(metrics_dir=str(tmp_path))
        
        # Add some data
        tracker.start_tracking("doc_1", "agent")
        tracker.end_tracking(success=True)
        
        dashboard = ComparisonDashboard(tracker)
        output_path = tmp_path / "dashboard.html"
        
        result = dashboard.generate_html(str(output_path))
        
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "Agent vs Legacy" in content
        assert "Performance Dashboard" in content
    
    def test_generate_json_report(self, tmp_path):
        """Test JSON report generation."""
        tracker = PerformanceTracker(metrics_dir=str(tmp_path))
        
        tracker.start_tracking("doc_1", "agent")
        tracker.end_tracking(success=True)
        
        dashboard = ComparisonDashboard(tracker)
        output_path = tmp_path / "report.json"
        
        result = dashboard.generate_json_report(str(output_path))
        
        assert Path(result).exists()
        data = json.loads(Path(result).read_text())
        assert "agent_vs_legacy" in data
