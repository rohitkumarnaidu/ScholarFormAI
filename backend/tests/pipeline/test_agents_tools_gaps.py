# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# FigureAnalysisTool — app.pipeline.agents.tools.figure_tool
# ==============================================================================

class TestFigureAnalysisTool:
    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_success_with_figures(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.analyze_layout.return_value = {
            "elements": [
                {"type": "figure", "text": "Fig 1 caption", "bbox": {"x": 0, "y": 0}, "page": 1},
                {"type": "figure", "text": "Fig 2 caption", "bbox": {"x": 10, "y": 10}, "page": 2},
                {"type": "paragraph", "text": "some text", "bbox": {}, "page": 1},
            ]
        }
        mock_llm_cls.return_value = mock_client
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        tool = FigureAnalysisTool()
        result = json.loads(tool._run("test.pdf"))
        assert result["status"] == "success"
        assert result["figures"]["total_count"] == 2
        assert result["figures"]["with_captions"] == 2

    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_no_figures(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.analyze_layout.return_value = {"elements": [{"type": "paragraph", "text": "text"}]}
        mock_llm_cls.return_value = mock_client
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        tool = FigureAnalysisTool()
        result = json.loads(tool._run("test.pdf"))
        assert result["figures"]["total_count"] == 0

    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_layout_data_none(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.analyze_layout.return_value = None
        mock_llm_cls.return_value = mock_client
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        tool = FigureAnalysisTool()
        assert "ERROR" in tool._run("test.pdf")

    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_exception_handling(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.analyze_layout.side_effect = RuntimeError("failed")
        mock_llm_cls.return_value = mock_client
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        tool = FigureAnalysisTool()
        assert "ERROR" in tool._run("test.pdf")

    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_arun_raises_not_implemented(self, mock_llm_cls):
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        tool = FigureAnalysisTool()
        with pytest.raises(NotImplementedError):
            import asyncio; asyncio.run(tool._arun("test.pdf"))


# ==============================================================================
# LayoutAnalysisTool — app.pipeline.agents.tools.layout_tool
# ==============================================================================

class TestLayoutAnalysisTool:
    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_success(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.analyze_layout.return_value = {
            "elements": [
                {"type": "heading", "text": "Intro", "font_size": 16, "bbox": {}},
                {"type": "paragraph", "text": "Some text", "font_size": 12, "bbox": {}},
                {"type": "figure", "text": "", "font_size": None, "bbox": {}},
                {"type": "table", "text": "", "font_size": None, "bbox": {}},
            ]
        }
        mock_llm_cls.return_value = mock_client
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        tool = LayoutAnalysisTool()
        result = json.loads(tool._run("test.pdf"))
        assert result["status"] == "success"
        assert result["layout"]["total_elements"] == 4
        assert result["layout"]["headings"] == 1
        assert result["layout"]["paragraphs"] == 1
        assert result["layout"]["has_figures"] is True
        assert result["layout"]["has_tables"] is True

    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_layout_data_none(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.analyze_layout.return_value = None
        mock_llm_cls.return_value = mock_client
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        tool = LayoutAnalysisTool()
        assert "ERROR" in tool._run("test.pdf")

    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_exception_handling(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.analyze_layout.side_effect = RuntimeError("failed")
        mock_llm_cls.return_value = mock_client
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        tool = LayoutAnalysisTool()
        assert "ERROR" in tool._run("test.pdf")

    @patch("app.pipeline.parsing.llm_pdf_parser.LLMPDFParser")
    def test_arun_not_implemented(self, mock_llm_cls):
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        tool = LayoutAnalysisTool()
        with pytest.raises(NotImplementedError):
            import asyncio; asyncio.run(tool._arun("test.pdf"))


# ==============================================================================
# MetadataExtractionTool — app.pipeline.agents.tools.metadata_tool
# ==============================================================================

class TestMetadataExtractionTool:
    def _make_tool(self):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        return MetadataExtractionTool()

    def test_cache_hit(self):
        with patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient"), \
             patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = {"cached": True}
            tool = self._make_tool()
            result = json.loads(tool._run("/nonexistent/file.pdf"))
            assert result == {"cached": True}

    def test_grobid_unavailable(self):
        with patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient") as mock_gc_cls, \
             patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = None
            mock_client = MagicMock()
            mock_client.is_available.return_value = False
            mock_gc_cls.return_value = mock_client
            tool = self._make_tool()
            assert "ERROR" in tool._run("/nonexistent/file.pdf")

    def test_successful_extraction(self):
        with patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient") as mock_gc_cls, \
             patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = None
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client.extract_metadata.return_value = {
                "title": "Test Paper", "authors": ["A"], "abstract": "abs",
                "affiliations": [], "publication_date": "2024", "doi": "10.1234",
                "keywords": ["ml"], "references": ["ref1"]
            }
            mock_gc_cls.return_value = mock_client
            tool = self._make_tool()
            result = json.loads(tool._run("/nonexistent/file.pdf"))
            assert result["status"] == "success"
            assert result["metadata"]["title"] == "Test Paper"
            assert result["metadata"]["reference_count"] == 1

    def test_metadata_none(self):
        with patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient") as mock_gc_cls, \
             patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = None
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client.extract_metadata.return_value = None
            mock_gc_cls.return_value = mock_client
            tool = self._make_tool()
            assert "ERROR" in tool._run("/nonexistent/file.pdf")

    def test_exception_handling(self):
        with patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient"), \
             patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.side_effect = RuntimeError("boom")
            tool = self._make_tool()
            assert "ERROR" in tool._run("/nonexistent/file.pdf")


# ==============================================================================
# ReferenceExtractionTool — app.pipeline.agents.tools.reference_tool
# ==============================================================================

class TestReferenceExtractionTool:
    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    def test_grobid_unavailable(self, mock_gc_cls):
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        mock_gc_cls.return_value = mock_client
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        tool = ReferenceExtractionTool()
        assert "ERROR" in tool._run("test.pdf")

    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    def test_no_references(self, mock_gc_cls):
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.extract_metadata.return_value = {}
        mock_gc_cls.return_value = mock_client
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        tool = ReferenceExtractionTool()
        assert "ERROR" in tool._run("test.pdf")

    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    def test_successful_extraction(self, mock_gc_cls):
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.extract_metadata.return_value = {
            "references": [
                {"raw_text": "Ref 1", "title": "Paper1", "authors": ["A"], "year": "2020", "doi": "10.1", "venue": "J"},
                {"raw_text": "Ref 2", "title": "Paper2", "authors": ["B"], "year": "2021", "doi": "", "venue": ""},
            ]
        }
        mock_gc_cls.return_value = mock_client
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        tool = ReferenceExtractionTool()
        result = json.loads(tool._run("test.pdf"))
        assert result["status"] == "success"
        assert result["references"]["total_count"] == 2
        assert result["references"]["has_dois"] == 1

    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    def test_exception_handling(self, mock_gc_cls):
        mock_client = MagicMock()
        mock_client.is_available.side_effect = RuntimeError("boom")
        mock_gc_cls.return_value = mock_client
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        tool = ReferenceExtractionTool()
        assert "ERROR" in tool._run("test.pdf")


# ==============================================================================
# ValidationTool — app.pipeline.agents.tools.validation_tool
# ==============================================================================

def _make_mock_doc(**kwargs):
    doc = MagicMock()
    doc.document_id = kwargs.get("doc_id", "doc1")
    doc.metadata.title = kwargs.get("title", "Test Title")
    doc.metadata.authors = kwargs.get("authors", ["A"])
    doc.metadata.abstract = kwargs.get("abstract", "Abs")
    doc.references = kwargs.get("references", [])
    return doc


class TestValidationTool:
    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_document_not_in_cache(self, mock_dv_cls):
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        tool = ValidationTool()
        assert "ERROR" in tool._run("unknown_id")

    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_valid_document(self, mock_dv_cls):
        validator = MagicMock()
        valid_result = MagicMock()
        valid_result.is_valid = True
        valid_result.errors = []
        valid_result.warnings = []
        validator.validate.return_value = valid_result
        mock_dv_cls.return_value = validator
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        tool = ValidationTool()
        doc = _make_mock_doc(doc_id="d1")
        tool.set_document("d1", doc)
        result = json.loads(tool._run("d1"))
        assert result["status"] == "success"
        assert result["validation"]["is_valid"] is True
        assert result["validation"]["error_count"] == 0
        assert result["validation"]["metadata_quality"]["has_title"] is True

    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_document_with_errors_and_warnings(self, mock_dv_cls):
        validator = MagicMock()
        valid_result = MagicMock()
        valid_result.is_valid = False
        valid_result.errors = ["err1", "err2", "err3"]
        valid_result.warnings = ["warn1"]
        validator.validate.return_value = valid_result
        mock_dv_cls.return_value = validator
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        tool = ValidationTool()
        doc = _make_mock_doc(doc_id="d1")
        tool.set_document("d1", doc)
        result = json.loads(tool._run("d1"))
        assert result["validation"]["is_valid"] is False
        assert result["validation"]["error_count"] == 3
        assert result["validation"]["warning_count"] == 1

    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_exception_handling(self, mock_dv_cls):
        validator = MagicMock()
        validator.validate.side_effect = RuntimeError("validation failed")
        mock_dv_cls.return_value = validator
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        tool = ValidationTool()
        doc = _make_mock_doc(doc_id="d1")
        tool.set_document("d1", doc)
        assert "ERROR" in tool._run("d1")
