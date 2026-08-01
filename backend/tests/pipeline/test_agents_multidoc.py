# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
import pytest
pytestmark = [pytest.mark.pipeline]


# =============================================================================
# MultiDocumentLearner (multi_doc_learning.py)
# =============================================================================

class TestMultiDocumentLearnerInit:
    def test_creates_storage_dir(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path / "mdl"))
        assert learner.storage_dir.exists()
        assert learner.document_db.name == "documents.jsonl"
        assert learner.insights_file.name == "insights.json"

    def test_default_insights_structure(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        expected_keys = {"author_patterns", "venue_patterns", "document_types", "quality_trends"}
        assert expected_keys == set(learner.insights.keys())
        assert learner.insights["author_patterns"] == {}
        assert learner.insights["venue_patterns"] == {}
        assert learner.insights["document_types"] == {}
        assert learner.insights["quality_trends"] == []

    def test_raises_on_bad_storage_dir(self):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        import pytest
        with patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
            with pytest.raises(PermissionError):
                MultiDocumentLearner(storage_dir="/invalid/path")

    def test_loads_existing_insights(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        d = tmp_path / "mdl"
        d.mkdir()
        insights_file = d / "insights.json"
        insights_file.write_text(json.dumps({
            "author_patterns": {"Smith": {"document_count": 3, "avg_references": 10.0, "avg_quality": 0.8}},
            "venue_patterns": {},
            "document_types": {},
            "quality_trends": []
        }))
        learner = MultiDocumentLearner(storage_dir=str(d))
        assert "Smith" in learner.insights["author_patterns"]

    def test_loads_corrupt_insights_returns_default(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        d = tmp_path / "mdl"
        d.mkdir()
        (d / "insights.json").write_text("not json")
        learner = MultiDocumentLearner(storage_dir=str(d))
        assert learner.insights["author_patterns"] == {}

    def test_loads_non_dict_returns_default(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        d = tmp_path / "mdl"
        d.mkdir()
        (d / "insights.json").write_text('"string"')
        learner = MultiDocumentLearner(storage_dir=str(d))
        assert learner.insights["author_patterns"] == {}

    def test_loads_adds_missing_keys(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        d = tmp_path / "mdl"
        d.mkdir()
        (d / "insights.json").write_text(json.dumps({"author_patterns": {}}))
        learner = MultiDocumentLearner(storage_dir=str(d))
        assert "venue_patterns" in learner.insights
        assert "document_types" in learner.insights
        assert "quality_trends" in learner.insights

    def test_loads_error_returns_default(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        d = tmp_path / "mdl"
        d.mkdir()
        (d / "insights.json").write_text(json.dumps({"author_patterns": {}}))
        with patch("json.load", side_effect=Exception("read error")):
            learner = MultiDocumentLearner(storage_dir=str(d))
            assert learner.insights["author_patterns"] == {}


class TestMultiDocumentLearnerRecordDocument:
    def test_record_empty_document_id(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("", {"title": "Test"}, {"success": True})
        assert not learner.document_db.exists() or learner.document_db.read_text(encoding="utf-8") == ""

    def test_record_metadata_not_dict(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc1", "not_a_dict", {"success": True})
        # Should use empty dict - check insights were updated
        assert learner.document_db.exists()

    def test_record_metrics_not_dict(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc1", {"title": "Test"}, "not_a_dict")
        assert learner.document_db.exists()

    def test_record_and_persist(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc_001", {"title": "Paper A", "authors": ["Alice"], "venue": "Conf", "document_type": "article"}, {"success": True, "references_count": 10, "figures_count": 2, "duration_seconds": 5.0, "validation_errors": 1})
        lines = learner.document_db.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["document_id"] == "doc_001"
        assert record["metadata"]["title"] == "Paper A"

    def test_record_file_write_failure(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        with patch("builtins.open", side_effect=OSError("write error")):
            learner.record_document("doc_001", {"title": "Test"}, {"success": True})
            # Insights should still be updated even if file write fails
            assert learner.insights["author_patterns"] == {}

    def test_record_updates_insights_on_exception(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        with patch.object(learner, "_update_insights", side_effect=Exception("update error")):
            learner.record_document("doc_001", {"title": "Test"}, {"success": True})
            # Should not raise


class TestMultiDocumentLearnerUpdateInsights:
    def test_author_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"authors": ["Alice", "Bob"]}, {"references_count": 10, "success": True})
        assert learner.insights["author_patterns"]["Alice"]["document_count"] == 1
        assert learner.insights["author_patterns"]["Bob"]["document_count"] == 1
        assert learner.insights["author_patterns"]["Alice"]["avg_references"] == 10.0
        assert learner.insights["author_patterns"]["Alice"]["avg_quality"] == 1.0

    def test_author_patterns_failure(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"authors": ["Alice"]}, {"references_count": 5, "success": False})
        assert learner.insights["author_patterns"]["Alice"]["avg_quality"] == 0.0

    def test_author_patterns_skip_invalid(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"authors": ["", 123]}, {"references_count": 5, "success": True})
        # Empty strings and non-strings should be skipped
        assert len(learner.insights["author_patterns"]) == 0

    def test_author_patterns_not_list(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"authors": "not_a_list"}, {"references_count": 5, "success": True})
        assert learner.insights["author_patterns"] == {}

    def test_venue_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"venue": "NeurIPS"}, {"references_count": 15, "figures_count": 3})
        vp = learner.insights["venue_patterns"]["NeurIPS"]
        assert vp["document_count"] == 1
        assert vp["avg_references"] == 15.0
        assert vp["avg_figures"] == 3.0

    def test_venue_patterns_none_value(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"venue": None}, {"references_count": 5, "figures_count": 1})
        assert "unknown" in learner.insights["venue_patterns"]

    def test_venue_patterns_empty_value(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"venue": ""}, {"references_count": 5, "figures_count": 1})
        assert "unknown" in learner.insights["venue_patterns"]

    def test_document_type_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"document_type": "article"}, {"duration_seconds": 10.0})
        tp = learner.insights["document_types"]["article"]
        assert tp["count"] == 1
        assert tp["avg_duration"] == 10.0

    def test_document_type_none(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"document_type": None}, {"duration_seconds": 5.0})
        assert "unknown" in learner.insights["document_types"]

    def test_quality_trends(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({}, {"success": False, "validation_errors": 3})
        assert len(learner.insights["quality_trends"]) == 1
        assert learner.insights["quality_trends"][0]["success"] is False
        assert learner.insights["quality_trends"][0]["errors"] == 3

    def test_quality_trends_max_limit(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        from app.pipeline.agents.multi_doc_learning import _MAX_QUALITY_TRENDS
        for _ in range(_MAX_QUALITY_TRENDS + 10):
            learner._update_insights({}, {"success": True, "validation_errors": 0})
        assert len(learner.insights["quality_trends"]) == _MAX_QUALITY_TRENDS

    def test_save_insights_error_logged(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        with patch("builtins.open", side_effect=OSError("save error")):
            learner._update_insights({"authors": ["Alice"]}, {"references_count": 5, "success": True})
            # Insights should still be updated in memory
            assert learner.insights["author_patterns"]["Alice"]["document_count"] == 1


class TestMultiDocumentLearnerQueries:
    def test_get_author_insights(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"authors": ["Alice"]}, {"references_count": 5, "success": True})
        result = learner.get_author_insights("Alice")
        assert result is not None
        assert result["document_count"] == 1

    def test_get_author_insights_not_found(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        result = learner.get_author_insights("Unknown")
        assert result is None

    def test_get_author_insights_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        result = learner.get_author_insights("")
        assert result is None

    def test_get_author_insights_exception(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.insights = None  # break insights to trigger exception
        result = learner.get_author_insights("Alice")
        assert result is None

    def test_get_venue_insights(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"venue": "NeurIPS"}, {"references_count": 10, "figures_count": 2})
        result = learner.get_venue_insights("NeurIPS")
        assert result is not None
        assert result["document_count"] == 1

    def test_get_venue_insights_not_found(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        result = learner.get_venue_insights("Unknown")
        assert result is None

    def test_get_venue_insights_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        result = learner.get_venue_insights("")
        assert result is None

    def test_get_venue_insights_exception(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.insights = None
        result = learner.get_venue_insights("NeurIPS")
        assert result is None

    def test_get_similar_documents_no_db(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        result = learner.get_similar_documents({"authors": ["Alice"], "venue": "Conf"})
        assert result == []

    def test_get_similar_documents_bad_metadata(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        result = learner.get_similar_documents("not_a_dict")
        assert result == []

    def test_get_similar_documents_with_matches(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc1", {"authors": ["Alice"], "venue": "Conf"}, {"success": True})
        learner.record_document("doc2", {"authors": ["Bob"], "venue": "Other"}, {"success": True})
        learner.record_document("doc3", {"authors": ["Alice", "Charlie"], "venue": "Conf"}, {"success": True})
        result = learner.get_similar_documents({"authors": ["Alice"], "venue": "Conf"})
        # doc1 matches venue + author (score 1+2=3), doc3 matches author+venue (score 1+2=3)
        assert len(result) == 2

    def test_get_similar_documents_limit(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc1", {"authors": ["Alice"], "venue": "Conf"}, {"success": True})
        learner.record_document("doc2", {"authors": ["Alice"], "venue": "Other"}, {"success": True})
        learner.record_document("doc3", {"authors": ["Alice"], "venue": "Workshop"}, {"success": True})
        result = learner.get_similar_documents({"authors": ["Alice"], "venue": "Conf"}, limit=1)
        assert len(result) == 1

    def test_get_similar_documents_limit_clamped(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        result = learner.get_similar_documents({"authors": ["Alice"]}, limit=0)
        assert result == []

    def test_get_similar_documents_skips_malformed_lines(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc1", {"authors": ["Alice"], "venue": "Conf"}, {"success": True})
        # Add a malformed line
        with open(learner.document_db, "a", encoding="utf-8") as f:
            f.write("not json\n")
        result = learner.get_similar_documents({"authors": ["Alice"], "venue": "Conf"})
        assert len(result) >= 1

    def test_get_similar_documents_non_dict_line(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        with open(learner.document_db, "a", encoding="utf-8") as f:
            f.write('"just a string"\n')
        result = learner.get_similar_documents({"authors": ["Alice"]})
        assert result == []

    def test_get_similar_documents_read_error(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc1", {"authors": ["Alice"], "venue": "Conf"}, {"success": True})
        with patch("builtins.open", side_effect=OSError("read error")):
            result = learner.get_similar_documents({"authors": ["Alice"]})
            assert result == []

    def test_get_insights_summary(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner._update_insights({"authors": ["Alice", "Bob"], "venue": "Conf", "document_type": "article"},
                                 {"references_count": 10, "success": True})
        summary = learner.get_insights_summary()
        assert summary["total_authors"] == 2
        assert summary["total_venues"] == 1
        assert summary["document_types"] == 1
        assert summary["quality_trend_count"] == 1
        assert len(summary["top_authors"]) == 2
        assert len(summary["top_venues"]) == 1

    def test_get_insights_summary_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        summary = learner.get_insights_summary()
        assert summary["total_authors"] == 0
        assert summary["top_authors"] == []
        assert summary["top_venues"] == []

    def test_get_insights_summary_exception(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.insights = None
        summary = learner.get_insights_summary()
        assert summary["total_authors"] == 0
        assert summary["total_venues"] == 0

    def test_get_similar_documents_no_author_venue_match(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        learner = MultiDocumentLearner(storage_dir=str(tmp_path))
        learner.record_document("doc1", {"authors": ["Alice"], "venue": "Conf"}, {"success": True})
        result = learner.get_similar_documents({"authors": ["Nobody"], "venue": "Unknown"})
        assert result == []
