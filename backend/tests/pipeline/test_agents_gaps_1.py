# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ═══════════════════════════════════════════════════════════════════════════
# AgentMemory — app.pipeline.agents.memory
# ═══════════════════════════════════════════════════════════════════════════

class TestAgentMemoryInit:
    def test_default_dir(self):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory()
        assert mem.memory_dir.name == ".agent_memory"
        assert mem.patterns == {}
        assert mem.errors == []
        assert mem.metrics == {}
        assert mem.corrections == []

    def test_custom_dir(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        d = str(tmp_path / "my_mem")
        mem = AgentMemory(d)
        assert mem.patterns_file.parent.name == "my_mem"

    def test_loads_existing_data(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        d = tmp_path / "mem"
        d.mkdir()
        pat_file = d / "patterns.json"
        pat_file.write_text(json.dumps({"fmt": {"successful": [], "failed": []}}))
        mem = AgentMemory(str(d))
        assert "fmt" in mem.patterns


class TestAgentMemoryRememberPattern:
    def test_new_pattern_type(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("metadata_extraction", {"document_type": "article"}, True)
        assert "metadata_extraction" in mem.patterns
        assert len(mem.patterns["metadata_extraction"]["successful"]) == 1
        assert len(mem.patterns["metadata_extraction"]["failed"]) == 0

    def test_failed_pattern(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("layout", {"document_type": "book"}, False)
        assert len(mem.patterns["layout"]["failed"]) == 1
        assert len(mem.patterns["layout"]["successful"]) == 0

    def test_dedup_same_doc_type(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("extract", {"document_type": "article"}, True)
        mem.remember_pattern("extract", {"document_type": "article"}, True)
        assert len(mem.patterns["extract"]["successful"]) == 1
        assert mem.patterns["extract"]["successful"][0]["count"] == 2

    def test_different_doc_type_adds_new(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("extract", {"document_type": "article"}, True)
        mem.remember_pattern("extract", {"document_type": "book"}, True)
        assert len(mem.patterns["extract"]["successful"]) == 2


class TestAgentMemoryRememberError:
    def test_new_error(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_error("parse_error", "Failed to parse PDF", "Use GROBID")
        assert len(mem.errors) == 1
        assert mem.errors[0]["type"] == "parse_error"
        assert mem.errors[0]["solution"] == "Use GROBID"
        assert mem.errors[0]["occurrences"] == 1

    def test_duplicate_error_increments(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_error("parse_error", "Failed to parse PDF")
        mem.remember_error("parse_error", "Failed to parse PDF")
        assert len(mem.errors) == 1
        assert mem.errors[0]["occurrences"] == 2

    def test_duplicate_with_solution_update(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_error("err", "msg")
        mem.remember_error("err", "msg", solution="new_sol")
        assert mem.errors[0]["solution"] == "new_sol"


class TestAgentMemoryRecordMetric:
    def test_new_metric(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.record_metric("accuracy", 0.95)
        assert "accuracy" in mem.metrics
        assert mem.metrics["accuracy"]["count"] == 1
        assert mem.metrics["accuracy"]["average"] == 0.95

    def test_existing_metric_average(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.record_metric("accuracy", 0.90)
        mem.record_metric("accuracy", 1.00)
        assert mem.metrics["accuracy"]["count"] == 2
        assert mem.metrics["accuracy"]["average"] == 0.95

    def test_truncation(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        for i in range(105):
            mem.record_metric("m1", float(i))
        assert len(mem.metrics["m1"]["values"]) == 100

    def test_with_metadata(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.record_metric("latency", 1.2, {"unit": "s"})
        assert mem.metrics["latency"]["values"][0]["metadata"] == {"unit": "s"}


class TestAgentMemoryGetBestPattern:
    def test_nonexistent_type(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        assert mem.get_best_pattern("missing", {}) is None

    def test_no_successful(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("t", {"document_type": "x"}, False)
        assert mem.get_best_pattern("t", {"document_type": "x"}) is None

    def test_exact_doc_type_match(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("t", {"document_type": "article"}, True)
        mem.remember_pattern("t", {"document_type": "book"}, True)
        result = mem.get_best_pattern("t", {"document_type": "article"})
        assert result is not None
        assert result["context"]["document_type"] == "article"

    def test_most_common_fallback(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("t", {"document_type": "article"}, True)
        mem.remember_pattern("t", {"document_type": "article"}, True)
        mem.remember_pattern("t", {"document_type": "book"}, True)
        result = mem.get_best_pattern("t", {"document_type": "thesis"})
        assert result is not None
        assert result["context"]["document_type"] == "article"


class TestAgentMemoryGetErrorSolution:
    def test_exact_match(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_error("type_a", "error msg", "fix")
        assert mem.get_error_solution("type_a", "error msg") == "fix"

    def test_substring_message(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_error("type_a", "parse_error", "retry")
        assert mem.get_error_solution("type_a", "Found parse_error in document") == "retry"

    def test_not_found(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        assert mem.get_error_solution("missing", "msg") is None


class TestAgentMemoryGetMetricSummary:
    def test_exists(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.record_metric("speed", 10.0)
        summary = mem.get_metric_summary("speed")
        assert summary is not None
        assert summary["average"] == 10.0

    def test_missing(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        assert mem.get_metric_summary("nonexistent") is None


class TestAgentMemoryCorrections:
    def test_remember_correction(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_correction("doc1", "title", "Old", "New")
        assert len(mem.corrections) == 1
        assert mem.corrections[0]["field"] == "title"
        assert mem.corrections[0]["original"] == "Old"
        assert mem.corrections[0]["corrected"] == "New"


class TestAgentMemorySummary:
    def test_get_memory_summary(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("t1", {"document_type": "a"}, True)
        mem.remember_error("e1", "msg", "fix")
        mem.record_metric("m1", 0.5)
        mem.remember_correction("d1", "author", "X", "Y")
        summary = mem.get_memory_summary()
        assert summary["patterns"]["t1"]["successful_count"] == 1
        assert summary["errors"]["total_errors"] == 1
        assert summary["metrics"]["m1"]["average"] == 0.5
        assert summary["corrections"]["total_corrections"] == 1

    def test_format_memory_summary(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        text = mem.format_memory_summary()
        assert "Patterns:" in text
        assert "Errors:" in text
        assert "Metrics tracked:" in text
        assert "Corrections:" in text

    def test_format_memory_summary_with_data(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        mem = AgentMemory(str(tmp_path))
        mem.remember_pattern("t1", {"document_type": "a"}, True)
        mem.remember_error("e1", "msg")
        mem.record_metric("m1", 0.5)
        text = mem.format_memory_summary()
        assert "t1" in text
        assert "1 successful" in text
        assert "1 total" in text


# ═══════════════════════════════════════════════════════════════════════════
# MultiDocumentLearner — app.pipeline.agents.multi_doc_learning
# ═══════════════════════════════════════════════════════════════════════════

class TestMultiDocumentLearnerInit:
    def test_default_dir(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.insights["author_patterns"] == {}
        assert l.insights["venue_patterns"] == {}
        assert l.insights["document_types"] == {}
        assert l.insights["quality_trends"] == []

    def test_loads_existing_insights(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        d = tmp_path / "mdl"
        d.mkdir()
        (d / "insights.json").write_text(json.dumps({"author_patterns": {"Dr A": {"document_count": 1, "avg_references": 10.0, "avg_quality": 1.0}}}))
        l = MultiDocumentLearner(str(d))
        assert l.insights["author_patterns"]["Dr A"]["document_count"] == 1


class TestMultiDocumentLearnerRecord:
    def test_empty_document_id_skips(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("", {"title": "Test"}, {})
        assert l.insights["author_patterns"] == {}

    def test_non_dict_metadata_coerced(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", "not_a_dict", {})
        assert l.insights["document_types"].get("unknown") is not None

    def test_non_dict_metrics_coerced(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"document_type": "paper"}, "not_a_dict")
        tp = l.insights["document_types"]["paper"]
        assert tp["count"] == 1

    def test_record_updates_author_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"authors": ["Alice"]}, {"references_count": 5, "success": True})
        ai = l.get_author_insights("Alice")
        assert ai is not None
        assert ai["document_count"] == 1
        assert ai["avg_references"] == 5.0
        assert ai["avg_quality"] == 1.0

    def test_record_updates_venue_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"venue": "NeurIPS"}, {"references_count": 10, "figures_count": 3})
        vi = l.get_venue_insights("NeurIPS")
        assert vi is not None
        assert vi["document_count"] == 1
        assert vi["avg_references"] == 10.0
        assert vi["avg_figures"] == 3.0

    def test_record_updates_doc_type_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"document_type": "thesis"}, {"duration_seconds": 120})
        tp = l.insights["document_types"]["thesis"]
        assert tp["count"] == 1
        assert tp["avg_duration"] == 120.0

    def test_record_updates_quality_trends(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {}, {"success": True, "validation_errors": 2})
        assert len(l.insights["quality_trends"]) == 1
        assert l.insights["quality_trends"][0]["success"] is True
        assert l.insights["quality_trends"][0]["errors"] == 2

    def test_multiple_documents_average(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"authors": ["Bob"], "venue": "ICML"}, {"references_count": 10, "success": True, "figures_count": 2, "duration_seconds": 100})
        l.record_document("d2", {"authors": ["Bob"], "venue": "ICML"}, {"references_count": 20, "success": False, "figures_count": 4, "duration_seconds": 200})
        ai = l.get_author_insights("Bob")
        assert ai["document_count"] == 2
        assert ai["avg_references"] == 15.0
        assert ai["avg_quality"] == 0.5
        vi = l.get_venue_insights("ICML")
        assert vi["avg_references"] == 15.0
        assert vi["avg_figures"] == 3.0


class TestMultiDocumentLearnerGetInsights:
    def test_get_author_insights_nonexistent(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.get_author_insights("Unknown") is None

    def test_get_author_insights_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.get_author_insights("") is None

    def test_get_venue_insights_nonexistent(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.get_venue_insights("Unknown") is None

    def test_get_venue_insights_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.get_venue_insights("") is None


class TestMultiDocumentLearnerSimilar:
    def test_non_dict_metadata_returns_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.get_similar_documents("bad") == []

    def test_no_db_file_returns_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.get_similar_documents({"authors": ["A"]}) == []

    def test_finds_similar_by_author(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"authors": ["Alice"]}, {})
        l.record_document("d2", {"authors": ["Bob"]}, {})
        result = l.get_similar_documents({"authors": ["Alice"]}, limit=10)
        ids = [r["document_id"] for r in result]
        assert "d1" in ids
        assert "d2" not in ids

    def test_finds_similar_by_venue(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"authors": ["A"], "venue": "NeurIPS"}, {})
        l.record_document("d2", {"authors": ["B"], "venue": "ICML"}, {})
        result = l.get_similar_documents({"authors": ["C"], "venue": "NeurIPS"}, limit=10)
        ids = [r["document_id"] for r in result]
        assert "d1" in ids

    def test_limit_clamping(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        assert l.get_similar_documents({"authors": ["A"]}, limit=0) == []


class TestMultiDocumentLearnerSummary:
    def test_get_insights_summary(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        l.record_document("d1", {"authors": ["Alice"], "venue": "NeurIPS", "document_type": "paper"}, {"success": True})
        summary = l.get_insights_summary()
        assert summary["total_authors"] == 1
        assert summary["total_venues"] == 1
        assert summary["document_types"] == 1
        assert summary["quality_trend_count"] == 1

    def test_get_insights_summary_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path))
        summary = l.get_insights_summary()
        assert summary["total_authors"] == 0
        assert summary["top_authors"] == []
        assert summary["top_venues"] == []


# ═══════════════════════════════════════════════════════════════════════════
# FederatedLearningNode — app.pipeline.agents.federated_learning
# ═══════════════════════════════════════════════════════════════════════════

class TestFederatedLearningNodeInit:
    def test_valid_node_id(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node-1", str(tmp_path))
        assert node.node_id == "node-1"
        assert node.global_model["version"] == 0

    def test_empty_node_id_raises(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        with pytest.raises(ValueError, match="node_id must be a non-empty string"):
            FederatedLearningNode("", str(tmp_path))

    def test_whitespace_node_id_raises(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        with pytest.raises(ValueError, match="node_id must be a non-empty string"):
            FederatedLearningNode("   ", str(tmp_path))

    def test_with_coordinator_url(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        assert node.coordinator_url == "http://coord"


class TestFederatedLearningNodeRecord:
    def test_record_local_update(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        node.record_local_update("pattern", {"key": "val"})
        assert len(node.local_updates) == 1
        assert node.local_updates[0]["update_type"] == "pattern"
        assert node.local_updates[0]["data"]["key"] == "val"

    def test_empty_update_type_skipped(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        node.record_local_update("", {"key": "val"})
        assert len(node.local_updates) == 0

    def test_non_dict_data_skipped(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        node.record_local_update("pattern", "not_a_dict")
        assert len(node.local_updates) == 0


class TestFederatedLearningNodeGetUpdates:
    def test_get_all_updates(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        node.record_local_update("a", {"v": 1})
        node.record_local_update("b", {"v": 2})
        assert len(node.get_local_updates()) == 2

    def test_get_updates_since_version(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        node.record_local_update("a", {"v": 1})
        node.global_model["version"] = 5
        node.record_local_update("b", {"v": 2})
        updates = node.get_local_updates(since_version=5)
        assert len(updates) == 1
        assert updates[0]["data"]["v"] == 2


class TestFederatedLearningNodePushPull:
    def test_push_no_url(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        assert node.push_updates_to_coordinator() is False

    def test_pull_no_url(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        assert node.pull_global_model() is False

    def test_push_success(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        node.record_local_update("pattern", {"k": "v"})
        with patch("app.pipeline.agents.federated_learning._requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            assert node.push_updates_to_coordinator() is True
            mock_post.assert_called_once()
            url = mock_post.call_args[0][0]
            assert "federated/updates" in url

    def test_push_http_error(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._requests.post") as mock_post:
            mock_post.return_value.status_code = 500
            assert node.push_updates_to_coordinator() is False

    def test_push_exception(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._requests.post") as mock_post:
            mock_post.side_effect = RuntimeError("timeout")
            assert node.push_updates_to_coordinator() is False

    def test_pull_success_new_version(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._requests.get") as mock_get:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"version": 1, "patterns": [], "statistics": {}, "last_updated": None}
            mock_get.return_value = response
            assert node.pull_global_model() is True
            assert node.global_model["version"] == 1

    def test_pull_same_version(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._requests.get") as mock_get:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"version": 0, "patterns": [], "statistics": {}, "last_updated": None}
            mock_get.return_value = response
            assert node.pull_global_model() is True

    def test_pull_http_error(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._requests.get") as mock_get:
            mock_get.return_value.status_code = 404
            assert node.pull_global_model() is False

    def test_pull_bad_response_format(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = "not_a_dict"
            assert node.pull_global_model() is False

    def test_sync(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with (
            patch("app.pipeline.agents.federated_learning._requests.post") as mock_post,
            patch("app.pipeline.agents.federated_learning._requests.get") as mock_get,
        ):
            mock_post.return_value.status_code = 200
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"version": 2, "patterns": [], "statistics": {}, "last_updated": None}
            mock_get.return_value = response
            assert node.sync() is True

    def test_sync_push_fails(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with (
            patch("app.pipeline.agents.federated_learning._requests.post") as mock_post,
            patch("app.pipeline.agents.federated_learning._requests.get") as mock_get,
        ):
            mock_post.return_value.status_code = 500
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"version": 1, "patterns": [], "statistics": {}, "last_updated": None}
            assert node.sync() is False

    def test_push_requests_unavailable(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", False):
            assert node.push_updates_to_coordinator() is False

    def test_pull_requests_unavailable(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path), coordinator_url="http://coord")
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", False):
            assert node.pull_global_model() is False


class TestFederatedLearningNodeAggregate:
    def test_aggregate_with_patterns(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        updates = [
            {"node_id": "n1", "update_type": "pattern", "data": {"p1": "v1"}},
            {"node_id": "n2", "update_type": "pattern", "data": {"p2": "v2"}},
        ]
        result = node.aggregate_updates(updates)
        assert result["version"] == 1
        assert len(result["patterns"]) == 2
        assert result["contributing_nodes"] == 2

    def test_aggregate_with_metrics(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        updates = [
            {"node_id": "n1", "update_type": "metric", "data": {"document_count": 10, "avg_duration": 5.0, "success_rate": 0.9}},
            {"node_id": "n2", "update_type": "metric", "data": {"document_count": 20, "avg_duration": 15.0, "success_rate": 0.8}},
        ]
        result = node.aggregate_updates(updates)
        assert result["statistics"]["total_documents"] == 30
        assert result["statistics"]["avg_duration"] == 10.0

    def test_aggregate_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        result = node.aggregate_updates([])
        assert result["patterns"] == []
        assert result["statistics"] == {}
        assert result["contributing_nodes"] == 0

    def test_aggregate_non_list(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        result = node.aggregate_updates("bad")
        assert result["patterns"] == []


class TestFederatedLearningNodeStatus:
    def test_get_status(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("n1", str(tmp_path))
        status = node.get_status()
        assert status["node_id"] == "n1"
        assert status["local_updates"] == 0
        assert status["global_model_version"] == 0
        assert status["coordinator_connected"] is False


# ═══════════════════════════════════════════════════════════════════════════
# FederatedCoordinator — app.pipeline.agents.federated_learning
# ═══════════════════════════════════════════════════════════════════════════

class TestFederatedCoordinator:
    def test_init(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        assert c.global_model["version"] == 0
        assert c.registered_nodes == set()

    def test_receive_updates(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        updates = [{"node_id": "n1", "update_type": "pattern", "data": {"k": "v"}}]
        assert c.receive_updates("n1", updates) is True
        assert "n1" in c.registered_nodes
        assert len(c.all_updates) == 1

    def test_receive_updates_empty_node_id(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        assert c.receive_updates("", []) is False

    def test_receive_updates_non_list(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        assert c.receive_updates("n1", "bad") is False

    def test_aggregate_and_update(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        c.receive_updates("n1", [{"node_id": "n1", "update_type": "pattern", "data": {"p": 1}}])
        result = c.aggregate_and_update()
        assert result["version"] == 1
        assert c.global_model["version"] == 1

    def test_get_global_model(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        c.global_model["version"] = 3
        assert c.get_global_model()["version"] == 3

    def test_get_statistics(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        c.receive_updates("n1", [{"k": "v"}])
        stats = c.get_statistics()
        assert stats["registered_nodes"] == 1
        assert stats["total_updates"] == 1

    def test_get_statistics_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path))
        stats = c.get_statistics()
        assert stats["registered_nodes"] == 0
        assert stats["total_updates"] == 0
        assert stats["global_model_version"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# MLPatternDetector — app.pipeline.agents.ml_patterns
# ═══════════════════════════════════════════════════════════════════════════

class TestMLPatternDetector:
    def test_init_defaults(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        assert d.min_samples == 5
        assert d.clusterer is None
        assert d.patterns == []

    def test_init_custom_min_samples(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        assert d.min_samples == 3

    def test_extract_features(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        metrics = {
            "duration_seconds": 10.0,
            "references_count": 20,
            "figures_count": 3,
            "validation_errors": 1,
            "validation_warnings": 2,
            "retry_count": 0,
            "fallback_triggered": True,
            "tools_used": ["grobid", "pymupdf"],
        }
        features = d.extract_features(metrics)
        assert isinstance(features, np.ndarray)
        assert features.shape == (8,)
        assert features[0] == 10.0
        assert features[6] == 1
        assert features[7] == 2

    def test_fit_insufficient_data(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=5)
        metrics_list = [{"duration_seconds": 1.0}] * 3
        assert d.fit(metrics_list) is False

    @staticmethod
    def _identical_metrics_list(n=3):
        return [
            {"duration_seconds": 1.0, "references_count": 5, "figures_count": 1, "validation_errors": 0, "validation_warnings": 0, "retry_count": 0, "fallback_triggered": False, "tools_used": ["a"], "success": True}
            for _ in range(n)
        ]

    def test_fit_sufficient_data(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        assert d.fit(self._identical_metrics_list()) is True
        assert d.clusterer is not None

    def test_predict_pattern_untrained(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        assert d.predict_pattern({}) is None

    def test_predict_pattern_trained(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        d.fit(self._identical_metrics_list())
        result = d.predict_pattern(self._identical_metrics_list()[0])
        assert result is not None
        assert "cluster_id" in result

    def test_detect_anomaly_untrained(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        is_anom, score = d.detect_anomaly({"duration_seconds": 1.0})
        assert is_anom is False
        assert score == 0.0

    def test_detect_anomaly_trained(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        d.fit(self._identical_metrics_list())
        is_anom, score = d.detect_anomaly(self._identical_metrics_list()[0])
        assert isinstance(is_anom, bool)
        assert isinstance(score, float)

    def test_get_pattern_summary_untrained(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        s = d.get_pattern_summary()
        assert s["pattern_count"] == 0
        assert s["trained"] is False

    def test_get_pattern_summary_trained(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        d.fit(self._identical_metrics_list())
        s = d.get_pattern_summary()
        assert s["trained"] is True
        assert s["pattern_count"] > 0

    def test_save_and_load(self, tmp_path):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        d.fit(self._identical_metrics_list())
        path = str(tmp_path / "model.pkl")
        d.save(path)
        d2 = MLPatternDetector()
        d2.load(path)
        assert d2.clusterer is not None
        assert len(d2.patterns) > 0


# ═══════════════════════════════════════════════════════════════════════════
# custom_tools — app.pipeline.agents.custom_tools
# ═══════════════════════════════════════════════════════════════════════════

class TestToolRegistry:
    def test_register_and_get(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def my_fn(inputs):
            return f"result: {inputs.get('x', '')}"
        cls = r.register("my_tool", "A test tool", {"x": (str, "Input value")}, my_fn)
        assert r.get_tool("my_tool") is cls

    def test_get_nonexistent(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.get_tool("missing") is None

    def test_list_tools(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def fn1(i): return "a"
        def fn2(i): return "b"
        r.register("t1", "", {"x": (str, "")}, fn1)
        r.register("t2", "", {"y": (int, "")}, fn2)
        tools = r.list_tools()
        assert "t1" in tools
        assert "t2" in tools

    def test_create_instance(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def my_fn(inputs):
            return f"ok: {inputs.get('name', '')}"
        cls = r.register("greet", "Greets", {"name": (str, "Name")}, my_fn)
        instance = r.create_instance("greet")
        assert instance is not None

    def test_create_instance_nonexistent(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.create_instance("missing") is None

    def test_registered_tool_execution(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def my_fn(inputs):
            return f"Hello, {inputs.get('name', 'World')}!"
        r.register("greet", "Greeter", {"name": (str, "Name")}, my_fn)
        instance = r.create_instance("greet")
        result = instance._run(name="Alice")
        assert result == "Hello, Alice!"

    def test_tool_execution_error_handling(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def broken_fn(inputs):
            raise ValueError("oops")
        r.register("broken", "Broken", {"x": (str, "x")}, broken_fn)
        instance = r.create_instance("broken")
        result = instance._run(x="test")
        assert "ERROR: Tool execution failed" in result


class TestCustomToolsGlobals:
    def test_register_custom_tool_global(self):
        from app.pipeline.agents import custom_tools as ct
        def fn(i): return str(i)
        cls = ct.register_custom_tool("global_test", "desc", {"q": (str, "q")}, fn)
        assert ct.get_custom_tool("global_test") is not None
        assert "global_test" in ct.list_custom_tools()

    def test_get_custom_tool_nonexistent(self):
        from app.pipeline.agents import custom_tools as ct
        assert ct.get_custom_tool("no_such_tool_xyz") is None


class TestCitationFormatterTool:
    def test_apa_style(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool
        cls = create_citation_formatter_tool()
        instance = cls()
        result = instance._run(authors=["Smith, J.", "Doe, A."], title="My Paper", year="2024", style="apa")
        assert "Smith, J., Doe, A." in result
        assert "2024" in result

    def test_apa_style_more_than_three_authors(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool
        cls = create_citation_formatter_tool()
        instance = cls()
        result = instance._run(authors=["A", "B", "C", "D"], title="Paper", year="2024", style="apa")
        assert "et al." in result

    def test_mla_style(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool
        cls = create_citation_formatter_tool()
        instance = cls()
        result = instance._run(authors=["Smith, J."], title="My Paper", year="2024", style="mla")
        assert 'Smith, J.' in result
        assert 'My Paper' in result
        assert '2024' in result

    def test_mla_style_no_authors(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool
        cls = create_citation_formatter_tool()
        instance = cls()
        result = instance._run(authors=[], title="My Paper", year="2024", style="mla")
        assert 'My Paper' in result
        assert '2024' in result

    def test_default_style(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool
        cls = create_citation_formatter_tool()
        instance = cls()
        result = instance._run(authors=["Smith, J."], title="My Paper", year="2024", style="other")
        assert "Smith, J." in result
        assert "My Paper" in result
        assert "2024" in result


class TestKeywordExtractorTool:
    def test_extract_keywords(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool
        cls = create_keyword_extractor_tool()
        instance = cls()
        result = instance._run(text="machine learning deep learning artificial intelligence", max_keywords=3)
        import json
        data = json.loads(result)
        assert len(data["keywords"]) <= 3
        assert "learning" in data["keywords"]

    def test_extract_keywords_empty_text(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool
        cls = create_keyword_extractor_tool()
        instance = cls()
        result = instance._run(text="", max_keywords=5)
        import json
        data = json.loads(result)
        assert data["keywords"] == []

    def test_extract_keywords_short_words_skipped(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool
        cls = create_keyword_extractor_tool()
        instance = cls()
        result = instance._run(text="a an the at by for in of on to", max_keywords=10)
        import json
        data = json.loads(result)
        assert data["keywords"] == []


# ═══════════════════════════════════════════════════════════════════════════
# TransformerPatternDetector — app.pipeline.agents.deep_learning
#
# Tests are in test_deep_learning_gaps.py (needs sys.modules patching to
# avoid the ~2 min torch import). Keep this section as a placeholder so
# test discovery is not broken.
# ═══════════════════════════════════════════════════════════════════════════

# (imported in test_deep_learning_gaps.py)
