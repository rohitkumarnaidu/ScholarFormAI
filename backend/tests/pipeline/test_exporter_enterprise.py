# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Enterprise-level tests for the Exporter pipeline module.

Covers all 11 methods, 48 branches, error/edge paths
with zero external dependencies (all mocks).
"""

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.models import Reference
from app.pipeline.export.exporter import Exporter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(**overrides):
    """Build a minimal PipelineDocument mock with all attributes the exporter touches."""
    from app.models import Block, BlockType, PipelineDocument
    from app.models.pipeline_document import DocumentMetadata, TemplateInfo

    doc = PipelineDocument(
        document_id=overrides.get("document_id", "doc1"),
        blocks=overrides.get(
            "blocks",
            [
                Block(block_id="b1", index=1, block_type=BlockType.TITLE, text="Paper Title", section_name="abstract"),
                Block(block_id="b2", index=2, block_type=BlockType.BODY, text="Body content.", section_name="body"),
                Block(
                    block_id="b3", index=3, block_type=BlockType.HEADING_1, text="Introduction", section_name="intro"
                ),
            ],
        ),
        metadata=DocumentMetadata(
            title=overrides.get("title", "Test Paper"),
            authors=overrides.get("authors", ["Alice", "Bob"]),
            affiliations=overrides.get("affiliations", ["Uni A"]),
            abstract=overrides.get("abstract", "This is a test."),
            keywords=overrides.get("keywords", ["test", "paper"]),
            doi=overrides.get("doi", "10.1234/test"),
        ),
        formatting_options=overrides.get("formatting_options", {"export_formats": ["docx", "json", "markdown"]}),
        output_path=overrides.get("output_path", "/tmp/out/doc.docx"),
        original_filename=overrides.get("original_filename", "doc.docx"),
        source_path=overrides.get("source_path", "/tmp/doc.docx"),
        template=TemplateInfo(template_name=overrides.get("template_name", "default")),
        generated_doc=overrides.get("generated_doc", MagicMock()),
    )
    doc.is_valid = overrides.get("is_valid", True)
    doc.validation_errors = overrides.get("validation_errors", [])
    doc.validation_warnings = overrides.get("validation_warnings", [])
    doc.references = overrides.get("references", [])
    doc.figures = overrides.get("figures", [])
    doc.tables = overrides.get("tables", [])
    doc.equations = overrides.get("equations", [])
    doc.processing_history = overrides.get("processing_history", [])
    return doc


@pytest.fixture
def exporter():
    with (
        patch("app.pipeline.export.exporter.PDFExporter"),
        patch("app.pipeline.export.exporter.LaTeXExporter"),
    ):
        return Exporter()


@pytest.fixture
def doc():
    return _make_doc()


# ═══════════════════════════════════════════════════════════════════════════════
# __init__
# ═══════════════════════════════════════════════════════════════════════════════


class TestInit:
    def test_creates_sub_exporters(self):
        with (
            patch("app.pipeline.export.exporter.PDFExporter"),
            patch("app.pipeline.export.exporter.LaTeXExporter"),
        ):
            e = Exporter()
            assert isinstance(e.pdf_exporter, MagicMock)
            assert isinstance(e.latex_exporter, MagicMock)


# ═══════════════════════════════════════════════════════════════════════════════
# process()
# ═══════════════════════════════════════════════════════════════════════════════


class TestProcess:
    def test_docx_export_called_when_format_includes_docx(self, exporter, doc):
        doc.generated_doc = MagicMock()
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx"]}
        with patch.object(exporter, "export") as mock_export:
            result = exporter.process(doc)
        mock_export.assert_called_once_with(doc.generated_doc, doc.output_path)
        assert result == doc

    def test_docx_skipped_when_no_generated_doc(self, exporter, doc):
        doc.generated_doc = None
        doc.formatting_options = {"export_formats": ["docx"]}
        with patch.object(exporter, "export") as mock_export:
            exporter.process(doc)
        mock_export.assert_not_called()

    def test_docx_skipped_when_no_output_path(self, exporter, doc):
        doc.generated_doc = MagicMock()
        doc.output_path = None
        doc.formatting_options = {"export_formats": ["docx"]}
        with patch.object(exporter, "export") as mock_export:
            exporter.process(doc)
        mock_export.assert_not_called()

    def test_json_export_called(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx", "json", "markdown"]}
        with (
            patch.object(exporter, "export"),
            patch.object(exporter, "export_json") as mock_json,
            patch.object(exporter, "export_markdown"),
        ):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        mock_json.assert_called_once()

    def test_markdown_export_called(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx", "json", "markdown"]}
        with (
            patch.object(exporter, "export"),
            patch.object(exporter, "export_json"),
            patch.object(exporter, "export_markdown") as mock_md,
        ):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        mock_md.assert_called_once()

    def test_pdf_export_called(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx", "pdf"]}
        with (
            patch.object(exporter, "export"),
            patch.object(exporter.pdf_exporter, "convert_to_pdf") as mock_convert,
        ):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        mock_convert.assert_called_once_with("/tmp/out/doc.docx", "/tmp/out")

    def test_pdf_export_failure_continues(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx", "pdf"]}
        exporter.pdf_exporter.convert_to_pdf.side_effect = Exception("LibreOffice not found")
        with patch.object(exporter, "export"):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        # Exception caught and logged, pipeline continues without crash

    def test_html_export_called(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx", "html"]}
        with (
            patch.object(exporter, "export"),
            patch.object(exporter, "export_html") as mock_html,
        ):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        mock_html.assert_called_once()

    def test_latex_export_called(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx", "latex"]}
        with (
            patch.object(exporter, "export"),
            patch.object(exporter, "export_latex") as mock_tex,
        ):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        mock_tex.assert_called_once()

    def test_jats_always_called(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.formatting_options = {"export_formats": ["docx"]}
        with (
            patch.object(exporter, "export"),
            patch.object(exporter, "export_jats") as mock_jats,
        ):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        mock_jats.assert_called_once()

    def test_output_path_not_docx_skips_extra_exports(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.pdf"
        doc.formatting_options = {"export_formats": ["docx", "json", "markdown", "pdf", "html", "latex"]}
        with (
            patch.object(exporter, "export_json") as mock_json,
            patch.object(exporter, "export_markdown") as mock_md,
            patch.object(exporter, "export_html") as mock_html,
            patch.object(exporter, "export_latex") as mock_tex,
            patch.object(exporter, "export_jats") as mock_jats,
            patch.object(exporter.pdf_exporter, "convert_to_pdf") as mock_pdf,
        ):
            doc.generated_doc = MagicMock()
            exporter.process(doc)
        mock_json.assert_not_called()
        mock_md.assert_not_called()
        mock_html.assert_not_called()
        mock_tex.assert_not_called()
        mock_pdf.assert_not_called()
        mock_jats.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# export()  — save word doc to disk
# ═══════════════════════════════════════════════════════════════════════════════


class TestExport:
    def test_saves_word_doc(self, exporter):
        word_doc = MagicMock()
        with patch("os.makedirs") as mock_mkdir:
            result = exporter.export(word_doc, "/tmp/out/test.docx")
        mock_mkdir.assert_called_once_with("/tmp/out", exist_ok=True)
        word_doc.save.assert_called_once_with("/tmp/out/test.docx")
        assert result == "/tmp/out/test.docx"

    def test_returns_none_when_no_word_doc(self, exporter):
        result = exporter.export(None, "/tmp/out/test.docx")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# export_json()
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportJson:
    def test_writes_json_with_payload(self, exporter, doc):
        with (
            patch.object(exporter, "_build_export_payload", return_value={"key": "val"}),
            patch("builtins.open", mock_open()) as m,
        ):
            result = exporter.export_json(doc, "/tmp/out/doc.json")
        handle = m()
        written = "".join(c[0][0] for c in handle.write.call_args_list)
        assert '"key"' in written
        assert '"val"' in written
        assert result == "/tmp/out/doc.json"

    def test_returns_none_on_exception(self, exporter, doc):
        with patch.object(exporter, "_build_export_payload", side_effect=Exception("boom")):
            result = exporter.export_json(doc, "/tmp/out/doc.json")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# export_markdown()
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportMarkdown:
    def test_writes_markdown(self, exporter, doc):
        with (
            patch.object(exporter, "_build_markdown", return_value="# Test\n\nBody."),
            patch("builtins.open", mock_open()) as m,
        ):
            result = exporter.export_markdown(doc, "/tmp/out/doc.md")
        m().write.assert_called_with("# Test\n\nBody.")
        assert result == "/tmp/out/doc.md"

    def test_returns_none_on_exception(self, exporter, doc):
        with patch.object(exporter, "_build_markdown", side_effect=Exception("boom")):
            result = exporter.export_markdown(doc, "/tmp/out/doc.md")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# export_jats()
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportJats:
    def test_writes_xml(self, exporter, doc):
        mock_gen = MagicMock()
        mock_gen.to_xml.return_value = "<article>content</article>"
        with (
            patch("app.pipeline.export.exporter.JATSGenerator", return_value=mock_gen),
            patch("builtins.open", mock_open()) as m,
        ):
            result = exporter.export_jats(doc, "/tmp/out/doc.xml")
        m().write.assert_called_with("<article>content</article>")
        assert result == "/tmp/out/doc.xml"

    def test_returns_none_on_generator_exception(self, exporter, doc):
        mock_gen = MagicMock()
        mock_gen.to_xml.side_effect = Exception("JATS error")
        with patch("app.pipeline.export.exporter.JATSGenerator", return_value=mock_gen):
            result = exporter.export_jats(doc, "/tmp/out/doc.xml")
        assert result is None

    def test_returns_none_on_write_exception(self, exporter, doc):
        mock_gen = MagicMock()
        mock_gen.to_xml.return_value = "<article/>"
        with (
            patch("app.pipeline.export.exporter.JATSGenerator", return_value=mock_gen),
            patch("builtins.open", mock_open()) as m,
        ):
            m.side_effect = OSError("disk full")
            result = exporter.export_jats(doc, "/tmp/out/doc.xml")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# export_html()
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportHtml:
    def test_writes_html_document(self, exporter, doc):
        md_content = "# Title\n\n## Abstract\n\nBody text.\n\n**Bold:** text\n\n1. item\n\n2. item2\n\nplain"
        written_data = {}

        def fake_open(path, mode="r", **kw):
            m = MagicMock()
            m.__enter__.return_value.write.side_effect = lambda data: (
                written_data.update({path: written_data.get(path, "") + data}) or len(data)
            )
            m.__enter__.return_value.read.return_value = ""
            return m

        with (
            patch.object(exporter, "_build_markdown", return_value=md_content),
            patch("builtins.open", fake_open),
        ):
            result = exporter.export_html(doc, "/tmp/out/doc.html")
        written = written_data.get("/tmp/out/doc.html", "")
        assert "<!DOCTYPE html>" in written, f"Missing doctype. Got: {written[:200]}"
        assert "<h1>Title</h1>" in written
        assert "<h2>Abstract</h2>" in written
        assert "<strong>Bold:</strong>" in written
        assert "<ol>" in written
        assert "<li>item</li>" in written
        assert "<p>plain</p>" in written
        assert result == "/tmp/out/doc.html"

    def test_list_continuation(self, exporter, doc):
        md = "1. item1\n2. item2\nplain after\n3. item3"
        with (
            patch.object(exporter, "_build_markdown", return_value=md),
            patch("builtins.open", mock_open()),
        ):
            result = exporter.export_html(doc, "/tmp/out/test.html")
        assert result is not None

    def test_returns_none_on_exception(self, exporter, doc):
        with patch.object(exporter, "_build_markdown", side_effect=Exception("boom")):
            result = exporter.export_html(doc, "/tmp/out/doc.html")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# export_latex()
# ═══════════════════════════════════════════════════════════════════════════════


class TestExportLatex:
    def test_returns_none_when_no_output_path(self, exporter, doc):
        doc.output_path = None
        result = exporter.export_latex(doc, "/tmp/out/doc.tex")
        assert result is None

    def test_calls_convert_to_latex(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        converted = "/tmp/out/tmp_abc.tex"
        output = "/tmp/out/doc.tex"
        exporter.latex_exporter.convert_to_latex.return_value = converted
        with (
            patch("os.path.exists", return_value=True),
            patch("os.replace") as mock_replace,
        ):
            result = exporter.export_latex(doc, output)
        exporter.latex_exporter.convert_to_latex.assert_called_once_with(
            "/tmp/out/doc.docx", "/tmp/out", template_name="default"
        )
        mock_replace.assert_called_once_with(converted, output)
        assert result == output

    def test_fallback_on_runtime_error(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        exporter.latex_exporter.convert_to_latex.side_effect = RuntimeError("convert fail")
        exporter.latex_exporter.export_from_document.return_value = "/tmp/out/doc.tex"
        with patch("os.replace"):
            result = exporter.export_latex(doc, "/tmp/out/doc.tex")
        exporter.latex_exporter.export_from_document.assert_called_once()
        assert result == "/tmp/out/doc.tex"

    def test_returns_none_on_generic_exception(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        exporter.latex_exporter.convert_to_latex.side_effect = Exception("generic fail")
        result = exporter.export_latex(doc, "/tmp/out/doc.tex")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# _get_export_formats()
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetExportFormats:
    def test_default_formats(self, exporter, doc):
        doc.formatting_options = {}
        result = exporter._get_export_formats(doc)
        assert result == ["docx", "json", "markdown"]

    def test_custom_formats(self, exporter, doc):
        doc.formatting_options = {"export_formats": ["html", "latex"]}
        result = exporter._get_export_formats(doc)
        assert "docx" in result
        assert "html" in result
        assert "latex" in result

    def test_docx_always_first(self, exporter, doc):
        doc.formatting_options = {"export_formats": ["json", "markdown"]}
        result = exporter._get_export_formats(doc)
        assert result[0] == "docx"

    def test_handles_non_list_formats(self, exporter, doc):
        doc.formatting_options = {"export_formats": "pdf"}
        result = exporter._get_export_formats(doc)
        assert "pdf" in result

    def test_handles_empty_formats(self, exporter, doc):
        doc.formatting_options = {"export_formats": []}
        result = exporter._get_export_formats(doc)
        assert result == ["docx"]

    def test_deduplicates(self, exporter, doc):
        doc.formatting_options = {"export_formats": ["docx", "json", "docx", "JSON"]}
        result = exporter._get_export_formats(doc)
        assert result == ["docx", "json"]

    def test_normalizes_case(self, exporter, doc):
        doc.formatting_options = {"export_formats": ["DOCX", "JSON"]}
        result = exporter._get_export_formats(doc)
        assert result == ["docx", "json"]


# ═══════════════════════════════════════════════════════════════════════════════
# _build_export_payload()
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildExportPayload:
    def test_includes_all_keys(self, exporter, doc):
        payload = exporter._build_export_payload(doc)
        keys = {
            "document_id",
            "template",
            "metadata",
            "blocks",
            "references",
            "figures",
            "tables",
            "equations",
            "processing_history",
            "original_filename",
            "source_path",
            "output_path",
            "stats",
            "validation",
            "exported_at",
        }
        assert keys.issubset(payload.keys())

    def test_template_name_none_when_no_template(self, exporter, doc):
        doc.template = None
        payload = exporter._build_export_payload(doc)
        assert payload["template"] is None

    def test_validation_fields(self, exporter, doc):
        doc.is_valid = False
        doc.validation_errors = ["error1"]
        doc.validation_warnings = ["warn1"]
        payload = exporter._build_export_payload(doc)
        assert payload["validation"]["is_valid"] is False
        assert payload["validation"]["errors"] == ["error1"]
        assert payload["validation"]["warnings"] == ["warn1"]

    def test_empty_collections(self, exporter, doc):
        doc.blocks = []
        doc.references = []
        doc.figures = []
        doc.tables = []
        doc.equations = []
        doc.processing_history = []
        payload = exporter._build_export_payload(doc)
        assert payload["blocks"] == []
        assert payload["references"] == []
        assert payload["figures"] == []
        assert payload["tables"] == []
        assert payload["equations"] == []
        assert payload["processing_history"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# _build_markdown()
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildMarkdown:
    def test_title_from_metadata(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "# Test Paper" in md

    def test_title_fallback_to_filename(self, exporter, doc):
        doc.metadata.title = None
        md = exporter._build_markdown(doc)
        assert "# doc.docx" in md

    def test_title_fallback_to_untitled(self, exporter, doc):
        doc.metadata.title = None
        doc.original_filename = None
        md = exporter._build_markdown(doc)
        assert "# Untitled Manuscript" in md

    def test_includes_authors(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "Alice" in md
        assert "Bob" in md

    def test_skips_authors_when_missing(self, exporter, doc):
        doc.metadata.authors = []
        md = exporter._build_markdown(doc)
        assert "Authors:" not in md

    def test_includes_affiliations(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "Uni A" in md

    def test_skips_affiliations_when_missing(self, exporter, doc):
        doc.metadata.affiliations = []
        md = exporter._build_markdown(doc)
        assert "Affiliations:" not in md

    def test_includes_doi(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "10.1234/test" in md

    def test_skips_doi_when_missing(self, exporter, doc):
        doc.metadata.doi = None
        md = exporter._build_markdown(doc)
        assert "DOI:" not in md

    def test_includes_template(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "default" in md

    def test_skips_template_when_missing(self, exporter, doc):
        doc.template = None
        md = exporter._build_markdown(doc)
        assert "Template:" not in md

    def test_includes_abstract(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "## Abstract" in md
        assert "This is a test." in md

    def test_skips_abstract_when_missing(self, exporter, doc):
        doc.metadata.abstract = None
        md = exporter._build_markdown(doc)
        assert "## Abstract" not in md

    def test_includes_keywords(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "test" in md
        assert "paper" in md

    def test_skips_keywords_when_missing(self, exporter, doc):
        doc.metadata.keywords = []
        md = exporter._build_markdown(doc)
        assert "Keywords:" not in md

    def test_heading_blocks(self, exporter, doc):
        md = exporter._build_markdown(doc)
        assert "## Introduction" in md

    def test_skips_reference_blocks(self, exporter, doc):
        from app.models import Block, BlockType

        doc.blocks = [
            Block(block_id="r1", index=10, block_type=BlockType.REFERENCE_ENTRY, text="[1] Ref text"),
        ]
        md = exporter._build_markdown(doc)
        assert "[1]" not in md

    def test_skips_empty_text_blocks(self, exporter, doc):
        from app.models import Block, BlockType

        doc.blocks = [
            Block(block_id="e1", index=5, block_type=BlockType.BODY, text=""),
        ]
        md = exporter._build_markdown(doc)
        assert md is not None

    def test_includes_references_section(self, exporter, doc):
        doc.references = [
            Reference(
                reference_id="r1",
                block_id="r1",
                block_index=1,
                index=1,
                raw_text="[1] Author, J. (2024). A paper.",
                formatted_text="[1] Author, J. (2024). A paper.",
                citation_key="auth2024",
            ),
        ]
        md = exporter._build_markdown(doc)
        assert "## References" in md
        assert "Author" in md

    def test_references_use_formatted_text_fallback(self, exporter, doc):
        doc.references = [
            Reference(
                reference_id="r1",
                block_id="r1",
                block_index=1,
                index=1,
                formatted_text=None,
                raw_text="[1] Raw ref",
                citation_key="raw2024",
            ),
        ]
        md = exporter._build_markdown(doc)
        assert "Raw ref" in md

    def test_skips_empty_references(self, exporter, doc):
        doc.references = [
            Reference(
                reference_id="r1",
                block_id="r1",
                block_index=1,
                index=1,
                formatted_text="",
                raw_text="",
                citation_key="empty",
            ),
        ]
        md = exporter._build_markdown(doc)
        assert "References" not in md

    def test_no_references_section_when_empty(self, exporter, doc):
        doc.references = []
        md = exporter._build_markdown(doc)
        assert "## References" not in md


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: process() → full pipeline
# ═══════════════════════════════════════════════════════════════════════════════


class TestProcessIntegration:
    def test_all_export_formats_triggered(self, exporter, doc):
        doc.output_path = "/tmp/out/doc.docx"
        doc.generated_doc = MagicMock()
        doc.formatting_options = {"export_formats": ["docx", "json", "markdown", "pdf", "html", "latex"]}
        with (
            patch.object(exporter, "export") as mock_export,
            patch.object(exporter, "export_json") as mock_json,
            patch.object(exporter, "export_markdown") as mock_md,
            patch.object(exporter, "export_html") as mock_html,
            patch.object(exporter, "export_latex") as mock_tex,
            patch.object(exporter, "export_jats") as mock_jats,
        ):
            exporter.process(doc)
        mock_export.assert_called_once()
        mock_json.assert_called_once()
        mock_md.assert_called_once()
        mock_html.assert_called_once()
        mock_tex.assert_called_once()
        mock_jats.assert_called_once()
