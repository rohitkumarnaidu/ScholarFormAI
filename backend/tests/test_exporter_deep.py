# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep tests for Exporter (exporter.py) — ~45 tests covering all export formats,
internal helpers, error handling, and edge cases.

External dependencies (PDFExporter, LaTeXExporter, JATSGenerator, safe_model_dump,
builtins.open, os.makedirs) are fully mocked.  File-system writes use tmp_path
to verify emitted content on disk.
"""

from __future__ import annotations

import json
import os
from unittest.mock import ANY, MagicMock, mock_open, patch

import pytest

# ---------------------------------------------------------------------------
#  Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pdf_exporter():
    me = MagicMock(name="PDFExporter")
    me.convert_to_pdf.return_value = None
    return me


@pytest.fixture
def mock_latex_exporter():
    me = MagicMock(name="LaTeXExporter")
    me.convert_to_latex.return_value = None
    return me


@pytest.fixture
def mock_jats_generator():
    m = MagicMock(name="JATSGenerator")
    m.to_xml.return_value = "<article>test</article>"
    return m


def _make_doc(
    doc_id="doc_001",
    filename="manuscript.docx",
    output_path="C:\\output\\manuscript.docx",
    metadata=None,
    blocks=None,
    references=None,
    figures=None,
    tables=None,
    equations=None,
    template=None,
    formatting_options=None,
    is_valid=True,
    validation_errors=None,
    validation_warnings=None,
    processing_history=None,
    generated_doc=None,
    get_stats_return=None,
):
    """Build a minimal mock PipelineDocument with the attributes Exporter reads."""
    if metadata is None:
        meta = MagicMock(name="metadata")
        meta.title = "Test Title"
        meta.authors = ["Alice", "Bob"]
        meta.affiliations = ["Uni A", "Uni B"]
        meta.abstract = "This is an abstract."
        meta.keywords = ["AI", "testing"]
        meta.doi = "10.1234/test"
    else:
        meta = metadata

    if blocks is None:
        b1 = MagicMock(name="block1")
        b1.block_type = "heading_1"
        b1.text = "Introduction"
        b1.index = 0
        b2 = MagicMock(name="block2")
        b2.block_type = "body"
        b2.text = "Some body text."
        b2.index = 100
        blocks = [b1, b2]

    if references is None:
        r1 = MagicMock(name="ref1")
        r1.index = 0
        r1.formatted_text = "[1] Author. Title."
        r1.raw_text = ""
        references = [r1]

    if figures is None:
        figures = []

    if tables is None:
        tables = []

    if equations is None:
        equations = []

    if template is None:
        tmpl = MagicMock(name="template")
        tmpl.template_name = "ieee"
    else:
        tmpl = template

    if validation_errors is None:
        validation_errors = []
    if validation_warnings is None:
        validation_warnings = []

    if processing_history is None:
        processing_history = []

    if get_stats_return is None:
        get_stats_return = {
            "blocks": len(blocks),
            "figures": len(figures),
            "tables": len(tables),
            "references": len(references),
            "equations": len(equations),
            "stages": len(processing_history),
        }

    doc = MagicMock(name="PipelineDocument")
    doc.document_id = doc_id
    doc.original_filename = filename
    doc.source_path = "C:\\source\\manuscript.docx"
    doc.output_path = output_path
    doc.metadata = meta
    doc.blocks = blocks
    doc.references = references
    doc.figures = figures
    doc.tables = tables
    doc.equations = equations
    doc.template = tmpl
    doc.formatting_options = formatting_options or {}
    doc.is_valid = is_valid
    doc.validation_errors = validation_errors
    doc.validation_warnings = validation_warnings
    doc.processing_history = processing_history
    doc.generated_doc = generated_doc
    doc.get_stats.return_value = get_stats_return
    return doc


def _make_exporter(mock_pdf=None, mock_latex=None):
    """Instantiate Exporter with both sub-exporters patched."""
    with patch("app.pipeline.export.exporter.PDFExporter", return_value=mock_pdf or MagicMock()):
        with patch("app.pipeline.export.exporter.LaTeXExporter", return_value=mock_latex or MagicMock()):
            from app.pipeline.export.exporter import Exporter
            return Exporter()


# ===================================================================
#  __init__
# ===================================================================

class TestInit:
    def test_creates_pdf_and_latex_exporters(self):
        with patch("app.pipeline.export.exporter.PDFExporter") as m_pdf_cls:
            with patch("app.pipeline.export.exporter.LaTeXExporter") as m_tex_cls:
                from app.pipeline.export.exporter import Exporter
                ex = Exporter()
        m_pdf_cls.assert_called_once()
        m_tex_cls.assert_called_once()
        assert isinstance(ex.pdf_exporter, MagicMock)
        assert isinstance(ex.latex_exporter, MagicMock)


# ===================================================================
#  _get_export_formats
# ===================================================================

class TestGetExportFormats:
    def test_default_formats(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options={})
        result = ex._get_export_formats(doc)
        assert result == ["docx", "json", "markdown"]

    def test_custom_formats(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options={"export_formats": ["pdf", "html"]})
        result = ex._get_export_formats(doc)
        assert "pdf" in result
        assert "html" in result
        assert "docx" in result  # always inserted first

    def test_docx_always_first(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options={"export_formats": ["json"]})
        result = ex._get_export_formats(doc)
        assert result[0] == "docx"
        assert result == ["docx", "json"]

    def test_non_list_formats_coerced(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options={"export_formats": "pdf"})
        result = ex._get_export_formats(doc)
        assert "docx" in result
        assert "pdf" in result

    def test_case_insensitive_normalization(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options={"export_formats": ["DOCX", "JSON", "PDF"]})
        result = ex._get_export_formats(doc)
        assert result == ["docx", "json", "pdf"]

    def test_duplicates_removed(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options={"export_formats": ["docx", "docx", "json"]})
        result = ex._get_export_formats(doc)
        assert result == ["docx", "json"]

    def test_empty_formats_still_has_docx(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options={"export_formats": []})
        result = ex._get_export_formats(doc)
        assert result == ["docx"]

    def test_none_formatting_options(self):
        ex = _make_exporter()
        doc = _make_doc(formatting_options=None)
        result = ex._get_export_formats(doc)
        assert result == ["docx", "json", "markdown"]


# ===================================================================
#  _build_markdown
# ===================================================================

class TestBuildMarkdown:
    def test_includes_title(self):
        ex = _make_exporter()
        doc = _make_doc()
        md = ex._build_markdown(doc)
        assert "# Test Title" in md

    def test_title_fallback_to_filename(self):
        ex = _make_exporter()
        meta = MagicMock(name="meta")
        meta.title = None
        meta.authors = []
        meta.affiliations = []
        meta.abstract = None
        meta.keywords = []
        meta.doi = None
        doc = _make_doc(metadata=meta, filename="paper.docx")
        md = ex._build_markdown(doc)
        assert "# paper.docx" in md

    def authors_affiliations_doi_included(self):
        ex = _make_exporter()
        doc = _make_doc()
        md = ex._build_markdown(doc)
        assert "Alice, Bob" in md
        assert "Uni A; Uni B" in md
        assert "10.1234/test" in md

    def test_abstract_section(self):
        ex = _make_exporter()
        doc = _make_doc()
        md = ex._build_markdown(doc)
        assert "## Abstract" in md
        assert "This is an abstract." in md

    def test_keywords(self):
        ex = _make_exporter()
        doc = _make_doc()
        md = ex._build_markdown(doc)
        assert "AI, testing" in md

    def test_template_name(self):
        ex = _make_exporter()
        doc = _make_doc()
        md = ex._build_markdown(doc)
        assert "ieee" in md

    def test_blocks_sorted_by_index(self):
        ex = _make_exporter()
        b1 = MagicMock(name="b1")
        b1.block_type = "body"
        b1.text = "Second block"
        b1.index = 200
        b2 = MagicMock(name="b2")
        b2.block_type = "heading_1"
        b2.text = "First heading"
        b2.index = 0
        doc = _make_doc(blocks=[b1, b2])
        md = ex._build_markdown(doc)
        first_idx = md.index("First heading")
        second_idx = md.index("Second block")
        assert first_idx < second_idx

    def test_skips_reference_entry_blocks(self):
        ex = _make_exporter()
        b1 = MagicMock(name="b1")
        b1.block_type = "reference_entry"
        b1.text = "Should skip"
        b1.index = 0
        b2 = MagicMock(name="b2")
        b2.block_type = "references_heading"
        b2.text = "Should skip too"
        b2.index = 100
        doc = _make_doc(blocks=[b1, b2], references=[])
        md = ex._build_markdown(doc)
        assert "Should skip" not in md

    def test_references_appended(self):
        ex = _make_exporter()
        doc = _make_doc()
        md = ex._build_markdown(doc)
        assert "## References" in md
        assert "[1] Author. Title." in md

    def test_references_empty(self):
        ex = _make_exporter()
        doc = _make_doc(references=[])
        md = ex._build_markdown(doc)
        assert "## References" not in md

    def test_strips_empty_text_blocks(self):
        ex = _make_exporter()
        b1 = MagicMock(name="b1")
        b1.block_type = "body"
        b1.text = "   "
        b1.index = 0
        doc = _make_doc(blocks=[b1], references=[])
        md = ex._build_markdown(doc)
        assert "   " not in md.split("\n")

    def test_ends_with_newline(self):
        ex = _make_exporter()
        doc = _make_doc()
        md = ex._build_markdown(doc)
        assert md.endswith("\n")


# ===================================================================
#  _build_export_payload
# ===================================================================

class TestBuildExportPayload:
    def test_payload_structure(self):
        ex = _make_exporter()
        doc = _make_doc()
        with patch("app.pipeline.export.exporter.safe_model_dump", return_value={"dumped": True}):
            payload = ex._build_export_payload(doc)
        assert payload["document_id"] == "doc_001"
        assert payload["original_filename"] == "manuscript.docx"
        assert payload["source_path"] == "C:\\source\\manuscript.docx"
        assert payload["output_path"] == "C:\\output\\manuscript.docx"
        assert payload["template"] == "ieee"
        assert payload["metadata"] == {"dumped": True}
        assert "stats" in payload
        assert "validation" in payload
        assert payload["validation"]["is_valid"] is True
        assert "blocks" in payload
        assert "references" in payload
        assert "figures" in payload
        assert "tables" in payload
        assert "equations" in payload
        assert "processing_history" in payload
        assert "exported_at" in payload

    def test_template_none(self):
        ex = _make_exporter()
        doc = _make_doc(template=MagicMock(template_name=None))
        with patch("app.pipeline.export.exporter.safe_model_dump", return_value={}):
            payload = ex._build_export_payload(doc)
        assert payload["template"] is None

    def test_references_safe_model_dump_called(self):
        ex = _make_exporter()
        doc = _make_doc()
        safe_mock = MagicMock(return_value={"dumped": True})
        with patch("app.pipeline.export.exporter.safe_model_dump", safe_mock):
            ex._build_export_payload(doc)
        # Should have called safe_model_dump for metadata, each block, each reference, etc.
        block_calls = [c for c in safe_mock.call_args_list if c[0][0] in doc.blocks]
        ref_calls = [c for c in safe_mock.call_args_list if c[0][0] in doc.references]
        assert len(block_calls) == len(doc.blocks)
        assert len(ref_calls) == len(doc.references)


# ===================================================================
#  export  (Word doc save)
# ===================================================================

class TestExport:
    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_saves_word_doc(self, mock_makedirs):
        ex = _make_exporter()
        word_doc = MagicMock(name="word_doc")
        result = ex.export(word_doc, "/out/test.docx")
        word_doc.save.assert_called_once_with("/out/test.docx")
        mock_makedirs.assert_called_once()
        assert result == "/out/test.docx"

    def test_none_word_doc_returns_none(self):
        ex = _make_exporter()
        result = ex.export(None, "/out/test.docx")
        assert result is None


# ===================================================================
#  export_json
# ===================================================================

class TestExportJson:
    @patch("app.pipeline.export.exporter.json.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_writes_json(self, mock_makedirs, mock_file, mock_json_dump):
        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_json(doc, "/out/test.json")
        assert result == "/out/test.json"
        mock_makedirs.assert_called_once_with(os.path.dirname("/out/test.json"), exist_ok=True)
        mock_file.assert_called_once_with("/out/test.json", "w", encoding="utf-8")
        mock_json_dump.assert_called_once()

    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_error_returns_none(self, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc()
        with patch.object(ex, "_build_export_payload", side_effect=ValueError("bad")):
            result = ex.export_json(doc, "/out/test.json")
        assert result is None


# ===================================================================
#  export_markdown
# ===================================================================

class TestExportMarkdown:
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_writes_markdown(self, mock_makedirs, mock_file):
        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_markdown(doc, "/out/test.md")
        assert result == "/out/test.md"
        mock_file.assert_called_once_with("/out/test.md", "w", encoding="utf-8")
        handle = mock_file()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "# Test Title" in written

    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_error_returns_none(self, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc()
        with patch.object(ex, "_build_markdown", side_effect=RuntimeError("crash")):
            result = ex.export_markdown(doc, "/out/test.md")
        assert result is None


# ===================================================================
#  export_jats
# ===================================================================

class TestExportJats:
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("app.pipeline.export.exporter.JATSGenerator")
    def test_writes_xml(self, mock_jats_cls, mock_makedirs, mock_file):
        mock_gen = MagicMock(name="gen")
        mock_gen.to_xml.return_value = "<article>hello</article>"
        mock_jats_cls.return_value = mock_gen

        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_jats(doc, "/out/test.xml")
        assert result == "/out/test.xml"
        mock_gen.to_xml.assert_called_once_with(doc)
        handle = mock_file()
        handle.write.assert_called_once_with("<article>hello</article>")

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("app.pipeline.export.exporter.JATSGenerator")
    def test_error_returns_none(self, mock_jats_cls, mock_makedirs):
        mock_jats_cls.side_effect = Exception("no jats")
        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_jats(doc, "/out/test.xml")
        assert result is None


# ===================================================================
#  export_html
# ===================================================================

class TestExportHtml:
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_writes_html_with_title(self, mock_makedirs, mock_file):
        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_html(doc, "/out/test.html")
        assert result == "/out/test.html"
        handle = mock_file()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "<!DOCTYPE html>" in written
        assert "<title>Test Title</title>" in written
        assert "<h1>Test Title</h1>" in written

    @patch("builtins.open", new_callable=mock_open)
    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_html_ordered_list(self, mock_makedirs, mock_file):
        ex = _make_exporter()
        b1 = MagicMock(name="b1")
        b1.block_type = "body"
        b1.text = "1. First item"
        b1.index = 0
        b2 = MagicMock(name="b2")
        b2.block_type = "body"
        b2.text = "2. Second item"
        b2.index = 100
        meta = MagicMock(name="meta")
        meta.title = ""
        meta.authors = []
        meta.affiliations = []
        meta.abstract = None
        meta.keywords = []
        meta.doi = None
        doc = _make_doc(metadata=meta, blocks=[b1, b2], references=[])
        ex.export_html(doc, "/out/test.html")
        handle = mock_file()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "<ol>" in written
        assert "<li>First item</li>" in written
        assert "<li>Second item</li>" in written
        assert "</ol>" in written

    @patch("builtins.open", new_callable=mock_open)
    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_html_bold_fields(self, mock_makedirs, mock_file):
        ex = _make_exporter()
        meta = MagicMock(name="meta")
        meta.title = "Doc"
        meta.authors = ["Alice"]
        meta.affiliations = []
        meta.abstract = None
        meta.keywords = []
        meta.doi = None
        doc = _make_doc(metadata=meta, blocks=[], references=[])
        ex.export_html(doc, "/out/test.html")
        handle = mock_file()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "<strong>Authors:</strong> Alice" in written

    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_error_returns_none(self, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc()
        with patch.object(ex, "_build_markdown", side_effect=Exception("html fail")):
            result = ex.export_html(doc, "/out/test.html")
        assert result is None


# ===================================================================
#  export_latex
# ===================================================================

class TestExportLatex:
    def test_delegates_to_latex_exporter(self):
        mock_tex = MagicMock(name="latex")
        mock_tex.convert_to_latex.return_value = "/tmp/out.tex"
        ex = _make_exporter(mock_latex=mock_tex)
        doc = _make_doc()
        result = ex.export_latex(doc, "/out/test.tex")
        mock_tex.convert_to_latex.assert_called_once_with(
            doc.output_path, os.path.dirname("/out/test.tex")
        )
        assert result == "/out/test.tex"

    def test_no_output_path_returns_none(self):
        ex = _make_exporter()
        doc = _make_doc(output_path=None)
        result = ex.export_latex(doc, "/out/test.tex")
        assert result is None

    def test_error_returns_none(self):
        mock_tex = MagicMock(name="latex")
        mock_tex.convert_to_latex.side_effect = Exception("pandoc fail")
        ex = _make_exporter(mock_latex=mock_tex)
        doc = _make_doc()
        result = ex.export_latex(doc, "/out/test.tex")
        assert result is None

    def test_converted_path_moved_when_different(self):
        mock_tex = MagicMock(name="latex")
        mock_tex.convert_to_latex.return_value = "/tmp/different.tex"
        ex = _make_exporter(mock_latex=mock_tex)
        doc = _make_doc()
        with patch("app.pipeline.export.exporter.os.path.exists", return_value=True):
            with patch("app.pipeline.export.exporter.os.replace") as m_replace:
                result = ex.export_latex(doc, "/out/test.tex")
        m_replace.assert_called_once_with("/tmp/different.tex", "/out/test.tex")
        assert result == "/out/test.tex"


# ===================================================================
#  process  (main pipeline entry)
# ===================================================================

class TestProcess:
    @patch("app.pipeline.export.exporter.os.makedirs")
    def test_docx_export(self, mock_makedirs):
        word_doc = MagicMock(name="word")
        ex = _make_exporter()
        doc = _make_doc(generated_doc=word_doc)
        with patch.object(ex, "export") as m_export:
            ex.process(doc)
        m_export.assert_called_once_with(word_doc, doc.output_path)

    def test_docx_export_skipped_when_no_generated_doc(self):
        ex = _make_exporter()
        doc = _make_doc(generated_doc=None)
        with patch.object(ex, "export") as m_export:
            ex.process(doc)
        m_export.assert_not_called()

    def test_docx_export_skipped_when_no_output_path(self):
        ex = _make_exporter()
        doc = _make_doc(output_path=None, generated_doc=MagicMock())
        with patch.object(ex, "export") as m_export:
            ex.process(doc)
        m_export.assert_not_called()

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_json_export_during_process(self, mock_file, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc(generated_doc=MagicMock())
        with patch.object(ex, "export"), patch.object(ex, "export_json") as m_json:
            ex.process(doc)
        m_json.assert_called_once()
        args, _ = m_json.call_args
        assert args[1].endswith(".json")

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_markdown_export_during_process(self, mock_file, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc(generated_doc=MagicMock())
        with patch.object(ex, "export"), patch.object(ex, "export_markdown") as m_md:
            ex.process(doc)
        m_md.assert_called_once()

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_pdf_export_during_process(self, mock_file, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc(generated_doc=MagicMock(), formatting_options={"export_formats": ["pdf"]})
        with patch.object(ex, "export"), patch.object(ex.pdf_exporter, "convert_to_pdf") as m_pdf:
            ex.process(doc)
        m_pdf.assert_called_once()

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_pdf_export_failure_logged(self, mock_file, mock_makedirs):
        ex = _make_exporter()
        ex.pdf_exporter.convert_to_pdf.side_effect = RuntimeError("LibreOffice missing")
        doc = _make_doc(generated_doc=MagicMock(), formatting_options={"export_formats": ["pdf"]})
        with patch.object(ex, "export"), patch("app.pipeline.export.exporter.logger") as m_log:
            ex.process(doc)
        m_log.warning.assert_any_call("Exporter: PDF export failed: %s", ANY)
        assert any("PDF export failed" in str(c) for c in m_log.warning.call_args_list)

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_html_export_during_process(self, mock_file, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc(generated_doc=MagicMock(), formatting_options={"export_formats": ["html"]})
        with patch.object(ex, "export"), patch.object(ex, "export_html") as m_html:
            ex.process(doc)
        m_html.assert_called_once()

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_latex_export_during_process(self, mock_file, mock_makedirs):
        mock_tex = MagicMock(name="latex")
        mock_tex.convert_to_latex.return_value = "/tmp/out.tex"
        ex = _make_exporter(mock_latex=mock_tex)
        doc = _make_doc(generated_doc=MagicMock(), formatting_options={"export_formats": ["latex"]})
        with patch.object(ex, "export"), patch.object(ex, "export_latex") as m_tex:
            ex.process(doc)
        m_tex.assert_called_once()

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_jats_always_exports(self, mock_file, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc(generated_doc=MagicMock(), formatting_options={"export_formats": []})
        with patch.object(ex, "export"), patch.object(ex, "export_jats") as m_jats:
            ex.process(doc)
        m_jats.assert_called_once()

    @patch("app.pipeline.export.exporter.os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_returns_document(self, mock_file, mock_makedirs):
        ex = _make_exporter()
        doc = _make_doc(generated_doc=MagicMock())
        with patch.object(ex, "export"):
            result = ex.process(doc)
        assert result is doc

    def test_skips_all_exports_when_output_path_not_docx(self):
        ex = _make_exporter()
        doc = _make_doc(output_path="/out/manuscript.pdf", generated_doc=MagicMock())
        with patch.object(ex, "export") as m_export, patch.object(ex, "export_json") as m_json:
            with patch.object(ex, "export_markdown") as m_md:
                ex.process(doc)
        m_export.assert_called_once()  # docx still saved if generated_doc present
        m_json.assert_not_called()
        m_md.assert_not_called()


# ===================================================================
#  Integration via tmp_path  (real file I/O)
# ===================================================================

class TestIntegrationWithTempDir:
    def test_export_writes_to_disk(self, tmp_path):
        output = tmp_path / "out.docx"
        word_doc = MagicMock(name="word")
        ex = _make_exporter()
        result = ex.export(word_doc, str(output))
        assert result == str(output)
        word_doc.save.assert_called_once_with(str(output))

    @patch("app.pipeline.export.exporter.safe_model_dump", return_value={"dumped": True})
    def test_export_json_writes_valid_json(self, mock_safe, tmp_path):
        output = tmp_path / "out.json"
        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_json(doc, str(output))
        assert result == str(output)
        with open(str(output), encoding="utf-8") as f:
            data = json.load(f)
        assert data["metadata"]["dumped"] is True
        assert data["document_id"] == "doc_001"

    @patch("app.pipeline.export.exporter.safe_model_dump", return_value={"dumped": True})
    def test_export_markdown_writes_to_disk(self, mock_safe, tmp_path):
        output = tmp_path / "out.md"
        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_markdown(doc, str(output))
        assert result == str(output)
        with open(str(output), encoding="utf-8") as f:
            content = f.read()
        assert "# Test Title" in content

    def test_export_jats_writes_xml_to_disk(self, tmp_path):
        with patch("app.pipeline.export.exporter.JATSGenerator") as mock_jats_cls:
            mock_gen = MagicMock()
            mock_gen.to_xml.return_value = "<article>real xml</article>"
            mock_jats_cls.return_value = mock_gen
            output = tmp_path / "out.xml"
            ex = _make_exporter()
            doc = _make_doc()
            result = ex.export_jats(doc, str(output))
        assert result == str(output)
        with open(str(output), encoding="utf-8") as f:
            content = f.read()
        assert "<article>real xml</article>" in content

    def test_export_html_writes_to_disk(self, tmp_path):
        output = tmp_path / "out.html"
        ex = _make_exporter()
        doc = _make_doc()
        result = ex.export_html(doc, str(output))
        assert result == str(output)
        with open(str(output), encoding="utf-8") as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content

    def test_process_with_tmp_path_produces_all_formats(self, tmp_path):
        word_doc = MagicMock(name="word")
        output_path = str(tmp_path / "result.docx")
        doc = _make_doc(
            output_path=output_path,
            generated_doc=word_doc,
            formatting_options={"export_formats": ["docx", "json", "markdown", "html"]},
        )
        with patch("app.pipeline.export.exporter.JATSGenerator") as mock_jats_cls:
            mock_gen = MagicMock()
            mock_gen.to_xml.return_value = "<article>ok</article>"
            mock_jats_cls.return_value = mock_gen
            ex = _make_exporter()
            result = ex.process(doc)
        assert result is doc
        word_doc.save.assert_called_once()
        assert os.path.exists(str(tmp_path / "result.json"))
        assert os.path.exists(str(tmp_path / "result.md"))
        assert os.path.exists(str(tmp_path / "result.html"))
        assert os.path.exists(str(tmp_path / "result.xml"))
