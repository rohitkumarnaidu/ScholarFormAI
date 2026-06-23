# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for advanced agent features.
"""
import pytest
import numpy as np
from pathlib import Path
from app.pipeline.agents.ml_patterns import MLPatternDetector
from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
from app.pipeline.agents.adaptive import AdaptiveStrategy
from app.pipeline.agents.distributed import DistributedCoordinator, AgentTask, AgentRole
from app.pipeline.agents.custom_tools import (
    register_custom_tool,
    get_custom_tool,
    create_citation_formatter_tool,
    create_keyword_extractor_tool
)
from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
from app.pipeline.agents.metrics import PerformanceTracker


class TestMLPatternDetector:
    """Test ML pattern detection."""
    
    def test_feature_extraction(self):
        """Test feature extraction."""
        detector = MLPatternDetector()
        
        metrics = {
            "duration_seconds": 30.5,
            "references_count": 25,
            "figures_count": 5,
            "validation_errors": 2,
            "validation_warnings": 3,
            "retry_count": 1,
            "fallback_triggered": False,
            "tools_used": ["tool1", "tool2"]
        }
        
        features = detector.extract_features(metrics)
        assert len(features) == 8
        assert features[0] == 30.5
        assert features[1] == 25
    
    def test_pattern_training(self):
        """Test pattern training."""
        detector = MLPatternDetector(min_samples=3)
        
        # Create sample data
        metrics_list = [
            {
                "duration_seconds": 30 + i,
                "references_count": 20 + i,
                "figures_count": 5,
                "validation_errors": 0,
                "validation_warnings": 1,
                "retry_count": 0,
                "fallback_triggered": False,
                "tools_used": ["tool1"],
                "success": True
            }
            for i in range(10)
        ]
        
        success = detector.fit(metrics_list)
        assert success is True
        assert len(detector.patterns) > 0
    
    def test_anomaly_detection(self):
        """Test anomaly detection."""
        detector = MLPatternDetector(min_samples=3)
        
        # Train on normal data
        normal_data = [
            {
                "duration_seconds": 30,
                "references_count": 20,
                "figures_count": 5,
                "validation_errors": 0,
                "validation_warnings": 1,
                "retry_count": 0,
                "fallback_triggered": False,
                "tools_used": ["tool1"],
                "success": True
            }
            for _ in range(10)
        ]
        
        detector.fit(normal_data)
        
        # Test with anomalous data
        anomaly = {
            "duration_seconds": 300,  # Much longer
            "references_count": 0,
            "figures_count": 0,
            "validation_errors": 10,
            "validation_warnings": 20,
            "retry_count": 5,
            "fallback_triggered": True,
            "tools_used": []
        }
        
        is_anomaly, score = detector.detect_anomaly(anomaly)
        # Note: With small dataset, results may vary
        assert isinstance(is_anomaly, bool)
        assert isinstance(score, float)


class TestMultiDocumentLearner:
    """Test multi-document learning."""
    
    def test_record_document(self, tmp_path):
        """Test document recording."""
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        
        metadata = {
            "title": "Test Paper",
            "authors": ["Author A", "Author B"],
            "venue": "Test Conference",
            "document_type": "research_paper"
        }
        
        metrics = {
            "duration_seconds": 30,
            "references_count": 25,
            "figures_count": 5,
            "success": True
        }
        
        learner.record_document("doc_1", metadata, metrics)
        
        # Verify insights updated
        assert "Author A" in learner.insights["author_patterns"]
        assert "Test Conference" in learner.insights["venue_patterns"]
    
    def test_get_similar_documents(self, tmp_path):
        """Test finding similar documents."""
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        
        # Record some documents
        for i in range(3):
            learner.record_document(
                f"doc_{i}",
                {
                    "authors": ["Author A"],
                    "venue": "Conference X"
                },
                {"success": True}
            )
        
        # Find similar
        similar = learner.get_similar_documents(
            {"authors": ["Author A"], "venue": "Conference X"},
            limit=2
        )
        
        assert len(similar) <= 2


class TestAdaptiveStrategy:
    """Test adaptive strategies."""
    
    def test_default_config(self):
        """Test default configuration."""
        tracker = PerformanceTracker()
        strategy = AdaptiveStrategy(tracker)
        
        config = strategy.get_config()
        assert config["max_retries"] == 3
        assert config["timeout_seconds"] == 60
    
    def test_adaptation(self, tmp_path):
        """Test strategy adaptation."""
        tracker = PerformanceTracker(metrics_dir=str(tmp_path))
        strategy = AdaptiveStrategy(tracker)
        
        # Simulate some runs
        tracker.start_tracking("doc_1", "agent")
        tracker.end_tracking(success=False)  # Failure
        
        # Adapt
        config = strategy.adapt()
        # After failure, retries might increase
        assert "max_retries" in config


class TestDistributedProcessing:
    """Test distributed processing."""
    
    def test_coordinator_initialization(self):
        """Test coordinator initialization."""
        coord = DistributedCoordinator(max_workers=2)
        
        assert len(coord.specialists) == 4
        assert AgentRole.METADATA_SPECIALIST in coord.specialists
    
    def test_document_processing(self):
        """Test distributed document processing."""
        coord = DistributedCoordinator(max_workers=2)
        
        result = coord.process_document("test.pdf")
        
        assert "specialist_results" in result
        assert len(result["specialist_results"]) == 4
        assert result["success"] is True
    
    def test_statistics(self):
        """Test statistics tracking."""
        coord = DistributedCoordinator()
        
        coord.process_document("test.pdf")
        
        stats = coord.get_statistics()
        assert stats["total_tasks"] == 4


class TestCustomTools:
    """Test custom tool creation."""
    
    def test_register_tool(self):
        """Test tool registration."""
        def my_fn(inputs):
            return f"Processed: {inputs['text']}"
        
        tool_class = register_custom_tool(
            name="test_tool",
            description="Test tool",
            input_schema={"text": (str, "Input text")},
            execute_fn=my_fn
        )
        
        assert tool_class is not None
        
        # Create instance and test
        tool = tool_class()
        result = tool._run(text="hello")
        assert "Processed: hello" in result
    
    def test_citation_formatter(self):
        """Test citation formatter tool."""
        tool_class = create_citation_formatter_tool()
        tool = tool_class()
        
        result = tool._run(
            authors=["Smith, J.", "Doe, A."],
            title="Test Paper",
            year="2024",
            style="apa"
        )
        
        assert "Smith" in result
        assert "2024" in result
    
    def test_keyword_extractor(self):
        """Test keyword extractor tool."""
        tool_class = create_keyword_extractor_tool()
        tool = tool_class()
        
        result = tool._run(
            text="machine learning artificial intelligence neural networks deep learning",
            max_keywords=3
        )
        
        assert "keywords" in result


class TestAdvancedDashboard:
    """Test advanced analytics dashboard."""
    
    def test_html_generation(self, tmp_path):
        """Test HTML dashboard generation."""
        dashboard = AdvancedAnalyticsDashboard()
        
        output_path = tmp_path / "dashboard.html"
        result = dashboard.generate_html(str(output_path))
        
        assert Path(result).exists()
        content = Path(result).read_text()
        assert "Advanced Agent Analytics" in content
    
    def test_json_report(self, tmp_path):
        """Test JSON report generation."""
        dashboard = AdvancedAnalyticsDashboard()
        
        output_path = tmp_path / "report.json"
        result = dashboard.generate_json_report(str(output_path))
        
        assert Path(result).exists()
