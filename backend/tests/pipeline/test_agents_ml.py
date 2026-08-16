# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytestmark = [pytest.mark.pipeline]


# =============================================================================
# ProcessingMetrics (metrics.py)
# =============================================================================


class TestProcessingMetrics:
    def test_default_tools_used_is_empty_list(self):
        from app.pipeline.agents.metrics import ProcessingMetrics

        pm = ProcessingMetrics(
            document_id="doc1",
            orchestrator_type="agent",
            start_time=100.0,
            end_time=200.0,
            duration_seconds=100.0,
            success=True,
        )
        assert pm.tools_used == []

    def test_custom_tools_used(self):
        from app.pipeline.agents.metrics import ProcessingMetrics

        pm = ProcessingMetrics(
            document_id="doc1",
            orchestrator_type="agent",
            start_time=100.0,
            end_time=200.0,
            duration_seconds=100.0,
            success=True,
            tools_used=["tool1", "tool2"],
        )
        assert pm.tools_used == ["tool1", "tool2"]

    def test_to_dict(self):
        from app.pipeline.agents.metrics import ProcessingMetrics

        pm = ProcessingMetrics(
            document_id="doc1",
            orchestrator_type="agent",
            start_time=100.0,
            end_time=200.0,
            duration_seconds=100.0,
            success=True,
        )
        d = pm.to_dict()
        assert d["document_id"] == "doc1"
        assert d["orchestrator_type"] == "agent"
        assert d["duration_seconds"] == 100.0
        assert d["success"] is True
        assert d["tools_used"] == []


# =============================================================================
# PerformanceTracker (metrics.py)
# =============================================================================


class TestPerformanceTracker:
    def test_init_creates_dir(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        d = str(tmp_path / "my_metrics")
        t = PerformanceTracker(d)
        assert t.metrics_dir.exists()

    def test_start_tracking(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        ctx = t.start_tracking("doc_001", "agent")
        assert ctx["document_id"] == "doc_001"
        assert ctx["orchestrator_type"] == "agent"
        assert isinstance(ctx["start_time"], float)
        assert ctx["tools_used"] == []
        assert ctx["retry_count"] == 0

    def test_record_tool_use(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_001", "agent")
        t.record_tool_use("mock_tool")
        assert "mock_tool" in t.current_run["tools_used"]

    def test_record_tool_use_no_run(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.record_tool_use("tool")  # should not raise

    def test_record_retry(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_001", "agent")
        t.record_retry()
        assert t.current_run["retry_count"] == 1

    def test_record_retry_no_run(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.record_retry()  # should not raise

    def test_end_tracking_no_run(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        with pytest.raises(ValueError, match="No active tracking run"):
            t.end_tracking(success=True)

    def test_end_tracking_success(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_001", "agent")
        t.record_tool_use("extractor")
        t.record_retry()
        metrics = t.end_tracking(success=True)
        assert metrics.document_id == "doc_001"
        assert metrics.orchestrator_type == "agent"
        assert metrics.success is True
        assert metrics.tools_used == ["extractor"]
        assert metrics.retry_count == 1
        assert t.current_run is None

    def test_end_tracking_with_document(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_002", "agent")
        doc = MagicMock()
        doc.metadata.title = "Test Paper"
        doc.blocks = [MagicMock()]
        doc.references = [MagicMock(), MagicMock()]
        doc.figures = [MagicMock()]
        doc.validation_errors = [MagicMock()]
        doc.validation_warnings = [MagicMock(), MagicMock()]
        metrics = t.end_tracking(success=True, document=doc)
        assert metrics.metadata_extracted is True
        assert metrics.layout_analyzed is True
        assert metrics.references_count == 2
        assert metrics.figures_count == 1
        assert metrics.validation_errors == 1
        assert metrics.validation_warnings == 2

    def test_end_tracking_with_fallback(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_003", "agent")
        metrics = t.end_tracking(success=False, error_message="Failed", fallback_triggered=True)
        assert metrics.success is False
        assert metrics.error_message == "Failed"
        assert metrics.fallback_triggered is True

    def test_end_tracking_with_document_no_extras(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_004", "legacy")
        doc = MagicMock()
        doc.metadata.title = ""
        doc.blocks = []
        doc.references = []
        doc.figures = []
        doc.validation_errors = []
        doc.validation_warnings = []
        metrics = t.end_tracking(success=True, document=doc)
        assert metrics.metadata_extracted is False
        assert metrics.layout_analyzed is False

    def test_extract_quality_metrics_error(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        doc = MagicMock()
        doc.metadata = None  # will cause AttributeError
        result = t._extract_quality_metrics(doc)
        assert result == {}

    def test_load_all_metrics_no_file(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        assert t.load_all_metrics() == []

    def test_load_all_metrics_with_data(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_001", "agent")
        t.end_tracking(success=True)
        loaded = t.load_all_metrics()
        assert len(loaded) == 1
        assert loaded[0]["document_id"] == "doc_001"

    def test_load_all_metrics_skips_bad_lines(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        # Manually write a bad line
        t.metrics_file.write_text('not json\n{"valid": true}\n', encoding="utf-8")
        loaded = t.load_all_metrics()
        assert len(loaded) == 1
        assert loaded[0]["valid"] is True

    def test_get_summary_no_file(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        assert t.get_summary() == {}

    def test_get_summary_with_file(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_001", "agent")
        t.end_tracking(success=True)
        summary = t.get_summary()
        assert summary["total_runs"] == 1
        assert summary["agent"]["count"] == 1

    def test_get_comparison_no_summary(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        comp = t.get_comparison()
        assert "error" in comp

    def test_get_comparison_with_data(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_001", "agent")
        t.end_tracking(success=True)
        t.start_tracking("doc_002", "legacy")
        t.end_tracking(success=True)
        comp = t.get_comparison()
        assert "agent_vs_legacy" in comp

    def test_calculate_stats_empty(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        stats = t._calculate_stats([])
        assert stats == {"count": 0}

    def test_calculate_stats_with_data(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        data = [
            {
                "success": True,
                "duration_seconds": 10.0,
                "references_count": 5,
                "figures_count": 2,
                "validation_errors": 1,
                "fallback_triggered": False,
            },
            {
                "success": False,
                "duration_seconds": 20.0,
                "references_count": 0,
                "figures_count": 0,
                "validation_errors": 3,
                "fallback_triggered": True,
            },
        ]
        stats = t._calculate_stats(data)
        assert stats["count"] == 2
        assert stats["success_rate"] == 0.5
        assert stats["avg_duration"] == 15.0
        assert stats["avg_references"] == 5.0
        assert stats["avg_figures"] == 2.0
        assert stats["avg_validation_errors"] == 1.0
        assert stats["fallback_rate"] == 0.5

    def test_calculate_stats_no_successful(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        data = [{"success": False, "duration_seconds": 5.0, "fallback_triggered": False}]
        stats = t._calculate_stats(data)
        assert stats["avg_references"] == 0
        assert stats["avg_figures"] == 0

    def test_update_summary_empty(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t._update_summary()  # should not raise

    def test_update_summary_no_metrics_file(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t._update_summary()
        assert not t.summary_file.exists()

    def test_end_tracking_clears_current_run(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker(str(tmp_path))
        t.start_tracking("doc_001", "agent")
        t.end_tracking(success=True)
        assert t.current_run is None


# =============================================================================
# MLPatternDetector (ml_patterns.py)
# =============================================================================


class TestMLPatternDetector:
    def test_init_defaults(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        assert d.min_samples == 5
        assert d.patterns == []

    def test_init_custom_min_samples(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=10)
        assert d.min_samples == 10

    def test_extract_features(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        metrics = {
            "duration_seconds": 15.0,
            "references_count": 10,
            "figures_count": 3,
            "validation_errors": 2,
            "validation_warnings": 1,
            "retry_count": 0,
            "fallback_triggered": True,
            "tools_used": ["a", "b"],
        }
        features = d.extract_features(metrics)
        assert isinstance(features, np.ndarray)
        assert features.shape == (8,)
        assert features[0] == 15.0
        assert features[6] == 1
        assert features[7] == 2

    def test_extract_features_defaults(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        features = d.extract_features({})
        assert features[0] == 0
        assert features[6] == 0
        assert features[7] == 0

    def test_fit_insufficient_data(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=5)
        result = d.fit([{"duration_seconds": 1.0}] * 3)
        assert result is False
        assert d.patterns == []

    def test_fit_sufficient_data(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=2)
        metrics_list = [
            {
                "duration_seconds": 1.0,
                "references_count": 5,
                "figures_count": 1,
                "validation_errors": 0,
                "validation_warnings": 0,
                "retry_count": 0,
                "fallback_triggered": False,
                "tools_used": ["a"],
                "success": True,
            },
            {
                "duration_seconds": 1.1,
                "references_count": 5,
                "figures_count": 1,
                "validation_errors": 0,
                "validation_warnings": 0,
                "retry_count": 0,
                "fallback_triggered": False,
                "tools_used": ["a"],
                "success": True,
            },
            {
                "duration_seconds": 1.2,
                "references_count": 5,
                "figures_count": 1,
                "validation_errors": 0,
                "validation_warnings": 0,
                "retry_count": 0,
                "fallback_triggered": False,
                "tools_used": ["a"],
                "success": True,
            },
            {
                "duration_seconds": 20.0,
                "references_count": 50,
                "figures_count": 10,
                "validation_errors": 5,
                "validation_warnings": 3,
                "retry_count": 2,
                "fallback_triggered": True,
                "tools_used": ["b", "c"],
                "success": False,
            },
            {
                "duration_seconds": 21.0,
                "references_count": 55,
                "figures_count": 11,
                "validation_errors": 4,
                "validation_warnings": 2,
                "retry_count": 1,
                "fallback_triggered": True,
                "tools_used": ["b"],
                "success": False,
            },
        ]
        result = d.fit(metrics_list)
        assert result is True
        assert len(d.patterns) > 0
        assert d.clusterer is not None

    def test_fit_with_error(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=2)
        # Pass data that will cause clustering error (empty after transform)
        result = d.fit(
            [
                {
                    "duration_seconds": 0,
                    "references_count": 0,
                    "figures_count": 0,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": [],
                }
            ]
        )
        assert result is False

    def test_predict_pattern_no_patterns(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        result = d.predict_pattern({})
        assert result is None

    def test_predict_pattern_returns_first(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=2)
        d.fit(
            [
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 20,
                    "references_count": 50,
                    "figures_count": 10,
                    "validation_errors": 5,
                    "validation_warnings": 3,
                    "retry_count": 2,
                    "fallback_triggered": True,
                    "tools_used": ["b"],
                    "success": False,
                },
            ]
        )
        result = d.predict_pattern({"duration_seconds": 1.5})
        assert result is not None
        assert "cluster_id" in result

    def test_detect_anomaly_not_fitted(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        is_anom, score = d.detect_anomaly({})
        assert is_anom is False
        assert score == 0.0

    def test_detect_anomaly_fitted(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=2)
        d.fit(
            [
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 20,
                    "references_count": 50,
                    "figures_count": 10,
                    "validation_errors": 5,
                    "validation_warnings": 3,
                    "retry_count": 2,
                    "fallback_triggered": True,
                    "tools_used": ["b"],
                    "success": False,
                },
                {
                    "duration_seconds": 21,
                    "references_count": 55,
                    "figures_count": 11,
                    "validation_errors": 4,
                    "validation_warnings": 2,
                    "retry_count": 1,
                    "fallback_triggered": True,
                    "tools_used": ["b"],
                    "success": False,
                },
            ]
        )
        is_anom, score = d.detect_anomaly(
            {
                "duration_seconds": 1.0,
                "references_count": 5,
                "figures_count": 1,
                "validation_errors": 0,
                "validation_warnings": 0,
                "retry_count": 0,
                "fallback_triggered": False,
                "tools_used": ["a"],
                "success": True,
            }
        )
        assert isinstance(is_anom, bool)
        assert isinstance(score, float)

    def test_get_pattern_summary_no_training(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        summary = d.get_pattern_summary()
        assert summary["pattern_count"] == 0
        assert summary["patterns"] == []
        assert summary["trained"] is False

    def test_get_pattern_summary_trained(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=2)
        d.fit(
            [
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 20,
                    "references_count": 50,
                    "figures_count": 10,
                    "validation_errors": 5,
                    "validation_warnings": 3,
                    "retry_count": 2,
                    "fallback_triggered": True,
                    "tools_used": ["b"],
                    "success": False,
                },
                {
                    "duration_seconds": 21,
                    "references_count": 55,
                    "figures_count": 11,
                    "validation_errors": 4,
                    "validation_warnings": 2,
                    "retry_count": 1,
                    "fallback_triggered": True,
                    "tools_used": ["b"],
                    "success": False,
                },
            ]
        )
        summary = d.get_pattern_summary()
        assert summary["trained"] is True
        assert summary["pattern_count"] > 0

    def test_save_and_load(self, tmp_path):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector(min_samples=2)
        d.fit(
            [
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 1,
                    "references_count": 5,
                    "figures_count": 1,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": ["a"],
                    "success": True,
                },
                {
                    "duration_seconds": 20,
                    "references_count": 50,
                    "figures_count": 10,
                    "validation_errors": 5,
                    "validation_warnings": 3,
                    "retry_count": 2,
                    "fallback_triggered": True,
                    "tools_used": ["b"],
                    "success": False,
                },
                {
                    "duration_seconds": 21,
                    "references_count": 55,
                    "figures_count": 11,
                    "validation_errors": 4,
                    "validation_warnings": 2,
                    "retry_count": 1,
                    "fallback_triggered": True,
                    "tools_used": ["b"],
                    "success": False,
                },
            ]
        )
        filepath = str(tmp_path / "model.pkl")
        d.save(filepath)
        assert Path(filepath).exists()

        d2 = MLPatternDetector()
        d2.load(filepath)
        assert len(d2.patterns) > 0
        assert d2.clusterer is not None

    def test_most_common_tools(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        metrics_list = [
            {"tools_used": ["a", "b", "c"]},
            {"tools_used": ["a", "b"]},
            {"tools_used": ["c", "a"]},
        ]
        tools = d._most_common_tools(metrics_list)
        assert tools[0] == "a"
        assert len(tools) <= 3

    def test_most_common_tools_empty(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        tools = d._most_common_tools([{"tools_used": []}])
        assert tools == []

    def test_extract_patterns_noise_only(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector

        d = MLPatternDetector()
        metrics_list = [{"duration_seconds": 1.0, "success": True, "tools_used": []}]
        labels = np.array([-1, -1])
        patterns = d._extract_patterns(metrics_list * 2, labels)
        assert patterns == []


# =============================================================================
# TransformerPatternDetector (deep_learning.py)
# =============================================================================


class TestTransformerPatternDetector:
    def test_init_no_torch(self):
        with patch.dict("sys.modules", {"torch": None}):
            from app.pipeline.agents.deep_learning import TransformerPatternDetector

            d = TransformerPatternDetector()
            assert d.tokenizer is None
            assert d.model is None
            assert d.device == "cpu"
            assert d.model_name == "allenai/scibert_scivocab_uncased"

    def test_init_with_torch(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector, torch

        if torch is None:
            pytest.skip("torch not available")
        d = TransformerPatternDetector(model_name="test-model", device="cuda")
        assert d.model_name == "test-model"
        assert d.device == "cuda"

    def test_encode_document_no_model(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        d.tokenizer = None
        d.model = None
        emb = d.encode_document("some text")
        assert isinstance(emb, np.ndarray)
        assert emb.shape == (768,)
        assert np.all(emb == 0)

    def test_encode_document_cached(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        d._ensure_initialized()
        d.embeddings_cache["cached text"] = np.ones(768) * 0.5
        emb = d.encode_document("cached text")
        assert np.allclose(emb, 0.5)

    def test_encode_document_fallback_on_exception(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        d.tokenizer = MagicMock()
        d.tokenizer.side_effect = Exception("mock fail")
        emb = d.encode_document("text")
        assert isinstance(emb, np.ndarray)
        assert emb.shape == (768,)

    def test_encode_metadata_empty(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        emb = d.encode_metadata({})
        assert isinstance(emb, np.ndarray)
        assert emb.shape == (768,)

    def test_encode_metadata_with_fields(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        metadata = {
            "title": "Test Paper",
            "authors": ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"],
            "abstract": "This is a test abstract " * 50,
            "venue": "Test Conference",
        }
        emb = d.encode_metadata(metadata)
        assert isinstance(emb, np.ndarray)
        assert emb.shape == (768,)

    def test_fit_clusters_insufficient(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        result = d.fit_clusters([np.ones(768)] * 2, n_clusters=5)
        assert result is False

    def test_fit_clusters_success(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        np.random.seed(42)
        embeddings = [np.random.rand(768) for _ in range(10)]
        result = d.fit_clusters(embeddings, n_clusters=3)
        assert result is True
        assert d.clusters is not None
        assert d.cluster_centers is not None
        assert len(d.cluster_centers) == 3

    def test_fit_clusters_fallback_on_error(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        d.fit_clusters([np.ones(768)] * 3, n_clusters=2)
        # clustering succeeded
        assert d.clusters is not None

    def test_predict_cluster_no_model(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        cluster_id = d.predict_cluster(np.ones(768))
        assert cluster_id == -1

    def test_predict_cluster_with_model(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        np.random.seed(42)
        embeddings = [np.random.rand(768) for _ in range(10)]
        d.fit_clusters(embeddings, n_clusters=3)
        cluster_id = d.predict_cluster(np.ones(768))
        assert isinstance(cluster_id, int)
        assert 0 <= cluster_id < 3

    def test_compute_similarity(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        e1 = np.array([1.0, 0.0, 0.0])
        e2 = np.array([1.0, 0.0, 0.0])
        sim = d.compute_similarity(e1, e2)
        assert abs(sim - 1.0) < 1e-6

    def test_compute_similarity_orthogonal(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        e1 = np.array([1.0, 0.0])
        e2 = np.array([0.0, 1.0])
        sim = d.compute_similarity(e1, e2)
        assert abs(sim) < 1e-6

    def test_compute_similarity_opposite(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        e1 = np.array([1.0, 0.0])
        e2 = np.array([-1.0, 0.0])
        sim = d.compute_similarity(e1, e2)
        assert abs(sim - (-1.0)) < 1e-6

    def test_find_similar_documents(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        query = np.array([1.0, 0.0])
        docs = [("doc1", np.array([1.0, 0.0])), ("doc2", np.array([0.0, 1.0])), ("doc3", np.array([0.5, 0.5]))]
        results = d.find_similar_documents(query, docs, top_k=2)
        assert len(results) == 2
        assert results[0][0] == "doc1"
        assert abs(results[0][1] - 1.0) < 0.01

    def test_find_similar_documents_empty(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        results = d.find_similar_documents(np.ones(10), [])
        assert results == []

    def test_detect_anomaly_semantic_no_centers(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        is_anom, sim = d.detect_anomaly_semantic(np.ones(768))
        assert is_anom is False
        assert sim == 0.0

    def test_detect_anomaly_semantic_with_centers(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        np.random.seed(42)
        embeddings = [np.random.rand(768) for _ in range(10)]
        d.fit_clusters(embeddings, n_clusters=3)
        is_anom, sim = d.detect_anomaly_semantic(np.ones(768))
        assert isinstance(is_anom, bool)
        assert isinstance(sim, float)

    def test_save_model_no_cache(self, tmp_path):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        d.cluster_centers = None
        filepath = str(tmp_path / "model.json")
        d.save_model(filepath)
        assert Path(filepath).exists()

    def test_save_model_with_cache(self, tmp_path):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        d.cluster_centers = np.array([[1.0, 2.0], [3.0, 4.0]])
        d.embeddings_cache["doc1"] = np.array([5.0, 6.0])
        filepath = str(tmp_path / "model_w_cache.json")
        d.save_model(filepath)
        assert Path(filepath).exists()
        assert Path(filepath + ".embeddings.npy").exists()

    def test_get_summary(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        summary = d.get_summary()
        assert summary["model_name"] == "allenai/scibert_scivocab_uncased"
        assert summary["device"] == "cpu"
        assert summary["cached_embeddings"] == 0
        assert summary["clusters_trained"] is False
        assert summary["n_clusters"] == 0

    def test_get_summary_trained(self):
        import numpy as np

        from app.pipeline.agents.deep_learning import TransformerPatternDetector

        d = TransformerPatternDetector()
        d.fit_clusters([np.ones(768) for _ in range(10)], n_clusters=2)
        summary = d.get_summary()
        assert summary["clusters_trained"] is True
        assert summary["n_clusters"] == 2
