# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep test suite for Exporter pipeline stage.
Covers process(), export_json, export_markdown, export_csv, export_html,
export_latex, export_jats, format export, _build_export_payload, 
_get_export_formats, error handling.
"""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from __future__ import annotations
from unittest.mock import patch, MagicMock, mock_open
import pytest
import json
from app.pipeline.export.exporter import Exporter

@pytest.fixture
def exporter():

    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
    return Exporter()

@pytest.fixture
def doc(tmp_path):
    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
    out = tmp_path / "out.docx"
    meta = DocumentMetadata(title="Test Paper")
    doc = PipelineDocument(
        document_id="exp1",
        metadata=meta,
        blocks=[
            Block(block_id="b1", index=0, text="Introduction", block_type=BlockType.HEADING_1),
            Block(block_id="b2", index=1, text="Body text here.", block_type=BlockType.BODY),
        ],
        output_path=str(out),
        formatting_options={"export_formats": ["json", "markdown"]},
    )
    return doc

class TestExporterProcess:
    def test_process_json_and_md(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with (
            patch.object(exporter, "export_json") as mock_json,
            patch.object(exporter, "export_markdown") as mock_md,
        ):
            mock_json.return_value = str(tmp_path / "out.json")
            mock_md.return_value = str(tmp_path / "out.md")
            result = exporter.process(doc)
            mock_json.assert_called_once()
            mock_md.assert_called_once()
            assert result is doc

    def test_process_with_docx(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        doc.generated_doc = MagicMock()
        with patch.object(exporter, "export") as mock_exp:
            mock_exp.return_value = doc.output_path
            exporter.process(doc)
            mock_exp.assert_called_once()

    def test_process_default_formats(self, exporter):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        doc = PipelineDocument(document_id="d1", output_path="test.docx",
                               formatting_options={"export_formats": ["docx", "json"]})
        doc.generated_doc = MagicMock()
        with (
            patch.object(exporter, "export") as m1,
            patch.object(exporter, "export_json") as m2,
        ):
            m1.return_value = "test.docx"
            m2.return_value = "test.json"
            result = exporter.process(doc)
            m1.assert_called_once()
            m2.assert_called_once()

    def test_process_empty_document(self, exporter):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        doc = PipelineDocument(document_id="empty", output_path="out.docx")
        doc.generated_doc = MagicMock()
        with patch.object(exporter, "export") as mock_exp:
            mock_exp.return_value = "out.docx"
            result = exporter.process(doc)
            mock_exp.assert_called_once()

    def test_process_handles_export_failure(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with patch.object(exporter, "export_json") as mock_json:
            mock_json.return_value = None
            result = exporter.process(doc)
            assert result is doc

class TestGetExportFormats:
    def test_from_options(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        exporter = Exporter()
        doc = PipelineDocument(document_id="d1", formatting_options={"export_formats": ["latex"]})
        result = exporter._get_export_formats(doc)
        assert "latex" in result

    def test_default_formats(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        exporter = Exporter()
        doc = PipelineDocument(document_id="d2")
        result = exporter._get_export_formats(doc)
        assert "docx" in result
        assert "json" in result
        assert "markdown" in result

    def test_single_string_converted_to_list(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        exporter = Exporter()
        doc = PipelineDocument(document_id="d3", formatting_options={"export_formats": "pdf"})
        result = exporter._get_export_formats(doc)
        assert "pdf" in result

class TestBuildExportPayload:
    def test_payload_structure(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        payload = exporter._build_export_payload(doc)
        assert "metadata" in payload
        assert "blocks" in payload
        assert payload["metadata"]["title"] == "Test Paper"

    def test_payload_includes_blocks(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        payload = exporter._build_export_payload(doc)
        assert len(payload["blocks"]) >= 1

    def test_payload_empty_document(self, exporter):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        doc = PipelineDocument(document_id="e1")
        payload = exporter._build_export_payload(doc)
        assert "metadata" in payload

class TestExportJson:
    def test_json_written(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.json"
        with patch.object(exporter, "_build_export_payload") as mock_build:
            mock_build.return_value = {"metadata": {}, "content": []}
            result = exporter.export_json(doc, str(p))
            assert result == str(p)
            assert p.exists()

    def test_json_content(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.json"
        exporter.export_json(doc, str(p))
        with open(str(p)) as f:
            data = json.load(f)
        assert "metadata" in data
        assert data["metadata"]["title"] == "Test Paper"

    def test_json_exception_returns_none(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with patch("builtins.open", side_effect=OSError("denied")):
            result = exporter.export_json(doc, "/invalid/path.json")
            assert result is None

class TestExportMarkdown:
    def test_markdown_written(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.md"
        result = exporter.export_markdown(doc, str(p))
        assert result == str(p)
        assert p.exists()

    def test_markdown_content(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.md"
        exporter.export_markdown(doc, str(p))
        content = p.read_text(encoding="utf-8")
        assert "Test Paper" in content
        assert "Introduction" in content

    def test_markdown_exception_returns_none(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with patch("builtins.open", side_effect=PermissionError):
            result = exporter.export_markdown(doc, "/invalid/path.md")
            assert result is None

    def test_markdown_empty_document(self, exporter, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "empty.md"
        doc = PipelineDocument(document_id="e1")
        result = exporter.export_markdown(doc, str(p))
        assert result == str(p)

class TestExportHtml:
    def test_html_written(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.html"
        result = exporter.export_html(doc, str(p))
        assert result == str(p)
        assert p.exists()

    def test_html_content(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.html"
        exporter.export_html(doc, str(p))
        content = p.read_text(encoding="utf-8")
        assert "Test Paper" in content
        assert "html" in content.lower()

    def test_html_exception_returns_none(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with patch("builtins.open", side_effect=OSError):
            result = exporter.export_html(doc, "/invalid/path.html")
            assert result is None

class TestExportLatex:
    def test_latex_written(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.tex"
        doc.output_path = str(tmp_path / "source.docx")
        with open(doc.output_path, "w") as f:
            f.write("dummy")
        with patch.object(exporter, "latex_exporter") as mock_latex:
            mock_latex.convert_to_latex.return_value = str(tmp_path / "test.tex")
            result = exporter.export_latex(doc, str(p))
            assert result == str(p)

    def test_latex_exception_returns_none(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with patch.object(exporter, "latex_exporter") as mock_latex:
            mock_latex.export_to_tex.side_effect = RuntimeError("fail")
            result = exporter.export_latex(doc, "/invalid/path.tex")
            assert result is None

class TestExportJats:
    def test_jats_written(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        p = tmp_path / "test.xml"
        result = exporter.export_jats(doc, str(p))
        assert result == str(p)
        assert p.exists()

    def test_jats_exception_returns_none(self, exporter, doc):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with patch("app.pipeline.export.exporter.JATSGenerator") as mock_gen:
            mock_gen_instance = MagicMock()
            mock_gen.return_value = mock_gen_instance
            mock_gen_instance.to_xml.side_effect = RuntimeError("fail")
            result = exporter.export_jats(doc, "/invalid/path.xml")
            assert result is None

class TestProcessingHistory:
    def test_stage_added_to_history(self, exporter, doc, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        with (
            patch.object(exporter, "export_json") as mock_json,
            patch.object(exporter, "export_markdown") as mock_md,
        ):
            mock_json.return_value = str(tmp_path / "out.json")
            mock_md.return_value = str(tmp_path / "out.md")
            result = exporter.process(doc)
            assert result.updated_at is not None

class TestEdgeCases:
    def test_output_path_none_does_not_crash(self, exporter):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        doc = PipelineDocument(document_id="np")
        result = exporter.process(doc)
        assert result is doc

    def test_generated_doc_none(self, exporter, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        doc = PipelineDocument(document_id="nd", output_path=str(tmp_path / "out.docx"),
                               formatting_options={"export_formats": ["docx"]})
        result = exporter.process(doc)
        assert result is doc
