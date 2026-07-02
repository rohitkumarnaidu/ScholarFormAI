# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import os
import json
import subprocess
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import pytest
from app.pipeline.export.exporter import Exporter
from app.pipeline.export.jats_generator import JATSGenerator
from app.pipeline.export.latex_exporter import (
    LaTeXExporter, escape_latex, _resolve_pandoc_binary,
    _convert_via_pandoc, JOURNAL_TEMPLATES
)
from app.pipeline.export.pdf_exporter import PDFExporter

# ===========================================================================
# exporter.py gap coverage
# ===========================================================================

class TestExporterProcessEdgeCases:
    """Cover uncovered branches in Exporter.process()."""

    def _make_doc(self, output_path="/tmp/output.docx", formatting_options=None):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock(spec=PipelineDocument)
        doc.document_id = "doc1"
        doc.original_filename = "test.docx"
        doc.source_path = "/tmp/test.docx"
        doc.output_path = output_path
        doc.template = MagicMock(template_name="ieee")
        meta = MagicMock()
        meta.title = "Test"
        meta.authors = []
        meta.affiliations = []
        meta.doi = None
        meta.abstract = None
        meta.keywords = []
        meta.publication_date = None
        meta.volume = None
        meta.issue = None
        doc.metadata = meta
        doc.is_valid = True
        doc.validation_errors = []
        doc.validation_warnings = []
        doc.blocks = []
        doc.references = []
        doc.figures = []
        doc.tables = []
        doc.equations = []
        doc.processing_history = []
        doc.get_stats.return_value = {}
        doc.formatting_options = formatting_options or {}
        doc.generated_doc = MagicMock()
        return doc

    def test_process_json_export(self):
        """Lines 42-43: json export from output_path."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/output.docx", formatting_options={"export_formats": ["docx", "json"]})
        e = Exporter()
        with patch.object(e, "export") as mock_exp, patch.object(e, "export_json") as mock_json:
            mock_exp.return_value = "/tmp/output.docx"
            mock_json.return_value = "/tmp/output.json"
            e.process(doc)
            mock_json.assert_called_once_with(doc, "/tmp/output.json")

    def test_process_markdown_export(self):
        """Lines 46-47: md export from output_path."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/output.docx", formatting_options={"export_formats": ["docx", "markdown"]})
        e = Exporter()
        with patch.object(e, "export") as mock_exp, patch.object(e, "export_markdown") as mock_md:
            mock_exp.return_value = "/tmp/output.docx"
            mock_md.return_value = "/tmp/output.md"
            e.process(doc)
            mock_md.assert_called_once_with(doc, "/tmp/output.md")

    def test_process_pdf_export_success(self):
        """Lines 50-53: PDF export success."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/output.docx", formatting_options={"export_formats": ["docx", "pdf"]})
        e = Exporter()
        with patch.object(e, "export") as mock_exp, patch.object(e.pdf_exporter, "convert_to_pdf") as mock_pdf:
            mock_exp.return_value = "/tmp/output.docx"
            mock_pdf.return_value = "/tmp/output.pdf"
            e.process(doc)

    def test_process_pdf_export_exception(self):
        """Lines 54-55: PDF export failure caught."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/output.docx", formatting_options={"export_formats": ["docx", "pdf"]})
        e = Exporter()
        with patch.object(e, "export") as mock_exp, patch.object(e.pdf_exporter, "convert_to_pdf", side_effect=Exception("fail")):
            mock_exp.return_value = "/tmp/output.docx"
            result = e.process(doc)
            assert result is doc

    def test_process_html_export(self):
        """Lines 58-59: HTML export from output_path."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/output.docx", formatting_options={"export_formats": ["docx", "html"]})
        e = Exporter()
        with patch.object(e, "export") as mock_exp, patch.object(e, "export_html") as mock_html:
            mock_exp.return_value = "/tmp/output.docx"
            mock_html.return_value = "/tmp/output.html"
            e.process(doc)
            mock_html.assert_called_once_with(doc, "/tmp/output.html")

    def test_process_latex_export(self):
        """Lines 62-63: LaTeX export from output_path."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/output.docx", formatting_options={"export_formats": ["docx", "latex"]})
        e = Exporter()
        with patch.object(e, "export") as mock_exp, patch.object(e, "export_latex") as mock_tex:
            mock_exp.return_value = "/tmp/output.docx"
            mock_tex.return_value = "/tmp/output.tex"
            e.process(doc)
            mock_tex.assert_called_once_with(doc, "/tmp/output.tex")

    def test_process_all_formats_simultaneously(self):
        """Cover all format branches at once."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(
            output_path="/tmp/output.docx",
            formatting_options={"export_formats": ["docx", "json", "markdown", "pdf", "html", "latex"]}
        )
        e = Exporter()
        with (
            patch.object(e, "export") as mock_exp,
            patch.object(e, "export_json") as mock_json,
            patch.object(e, "export_markdown") as mock_md,
            patch.object(e.pdf_exporter, "convert_to_pdf") as mock_pdf,
            patch.object(e, "export_html") as mock_html,
            patch.object(e, "export_latex") as mock_tex,
        ):
            mock_exp.return_value = "/tmp/output.docx"
            mock_json.return_value = "/tmp/output.json"
            mock_md.return_value = "/tmp/output.md"
            mock_pdf.return_value = "/tmp/output.pdf"
            mock_html.return_value = "/tmp/output.html"
            mock_tex.return_value = "/tmp/output.tex"
            result = e.process(doc)
            mock_json.assert_called_once()
            mock_md.assert_called_once()
            mock_pdf.assert_called_once()
            mock_html.assert_called_once()
            mock_tex.assert_called_once()
            assert result is doc

class TestExporterHtmlBranches:
    """Cover uncovered branches in export_html."""

    def _make_doc(self, title="Doc", blocks=None, references=None):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock(spec=PipelineDocument)
        doc.document_id = "d1"
        doc.output_path = "/tmp/out.docx"
        doc.original_filename = "test.docx"
        doc.template = None
        meta = MagicMock()
        meta.title = title
        meta.authors = []
        meta.affiliations = []
        meta.doi = None
        meta.abstract = None
        meta.keywords = []
        doc.metadata = meta
        doc.blocks = blocks or []
        doc.references = references or []
        doc.figures = []
        doc.tables = []
        doc.equations = []
        return doc

    def test_html_bold_text_with_colon(self, tmp_path):
        """Lines 132-135: bold text with colon."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = MagicMock(index=0, block_type="body", text="**Key Result:** 42% improvement")
        doc = self._make_doc(title="Doc", blocks=[b])
        out = str(tmp_path / "out.html")
        result = Exporter().export_html(doc, out)
        with open(out) as f:
            c = f.read()
            assert "<strong>Key Result:</strong>" in c
        assert result == out

    def test_html_numbered_list(self, tmp_path):
        """Lines 137-140: numbered list detection."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = MagicMock(index=0, block_type="body", text="1. First item")
        doc = self._make_doc(title=None, blocks=[b])
        out = str(tmp_path / "out.html")
        Exporter().export_html(doc, out)
        with open(out) as f:
            c = f.read()
            assert "<ol>" in c
            assert "<li>First item</li>" in c

    def test_html_numbered_list_multiple_items(self, tmp_path):
        """Multiple numbered items."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b1 = MagicMock(index=0, block_type="body", text="1. First")
        b2 = MagicMock(index=1, block_type="body", text="2. Second")
        doc = self._make_doc(title=None, blocks=[b1, b2])
        out = str(tmp_path / "out.html")
        Exporter().export_html(doc, out)
        with open(out) as f:
            c = f.read()
            assert c.count("<li>") == 2

    def test_html_list_to_paragraph_transition(self, tmp_path):
        """Lines 141-144: ordered list then paragraph closes ol."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b1 = MagicMock(index=0, block_type="body", text="1. First")
        b2 = MagicMock(index=1, block_type="body", text="Some paragraph")
        doc = self._make_doc(title=None, blocks=[b1, b2])
        out = str(tmp_path / "out.html")
        Exporter().export_html(doc, out)
        with open(out) as f:
            c = f.read()
            assert "<ol>" in c
            assert "</ol>" in c
            assert "<p>Some paragraph</p>" in c

    def test_html_ending_with_list_closed(self, tmp_path):
        """Line 147-148: close remaining open list at end."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = MagicMock(index=0, block_type="body", text="1. Only item")
        doc = self._make_doc(title=None, blocks=[b])
        out = str(tmp_path / "out.html")
        Exporter().export_html(doc, out)
        with open(out) as f:
            c = f.read()
            assert c.count("<ol>") == 1
            assert c.count("</ol>") == 1

    def test_html_empty_title_uses_document(self, tmp_path):
        """Title fallback to 'Document'."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = MagicMock(index=0, block_type="body", text="Hello")
        doc = self._make_doc(title=None, blocks=[b])
        out = str(tmp_path / "out.html")
        Exporter().export_html(doc, out)
        with open(out) as f:
            assert "<title>Document</title>" in f.read()

class TestExporterLatexBranches:
    """Cover uncovered branches in export_latex."""

    def _make_doc(self, output_path="/tmp/in.docx", template=None):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock(spec=PipelineDocument)
        doc.document_id = "d1"
        doc.output_path = output_path
        doc.template = template or MagicMock(template_name="ieee")
        meta = MagicMock()
        meta.title = "Test"
        meta.authors = []
        doc.metadata = meta
        return doc

    def test_export_latex_os_replace_different_paths(self, tmp_path):
        """Line 172: os.replace when paths differ."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/in.docx")
        e = Exporter()
        tex_path = str(tmp_path / "out.tex")
        converted = str(tmp_path / "in.tex")
        Path(converted).write_text("latex")
        with patch.object(e.latex_exporter, "convert_to_latex", return_value=converted):
            with patch("os.replace") as mock_replace:
                result = e.export_latex(doc, tex_path)
                mock_replace.assert_called_once_with(converted, tex_path)
                assert result == tex_path

    def test_export_latex_same_path_skip_replace(self, tmp_path):
        """When paths are the same, no os.replace."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/in.docx")
        e = Exporter()
        tex_path = str(tmp_path / "out.tex")
        with patch.object(e.latex_exporter, "convert_to_latex", return_value=tex_path):
            with patch("os.replace") as mock_replace:
                result = e.export_latex(doc, tex_path)
                mock_replace.assert_not_called()
                assert result == tex_path

    def test_export_latex_convert_path_does_not_exist(self, tmp_path):
        """When converted_path doesn't exist, skip replace."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/in.docx")
        e = Exporter()
        tex_path = str(tmp_path / "out.tex")
        converted = str(tmp_path / "nonexistent.tex")
        with patch.object(e.latex_exporter, "convert_to_latex", return_value=converted):
            with patch("os.path.exists", return_value=False):
                with patch("os.replace") as mock_replace:
                    result = e.export_latex(doc, tex_path)
                    mock_replace.assert_not_called()
                    assert result == tex_path

    def test_export_latex_fallback_on_runtime_error(self, tmp_path):
        """Lines 175-181: RuntimeError fallback to export_from_document."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/in.docx")
        e = Exporter()
        tex_path = str(tmp_path / "out.tex")
        fallback = str(tmp_path / "fallback.tex")
        Path(fallback).write_text("latex")
        with patch.object(e.latex_exporter, "convert_to_latex", side_effect=RuntimeError("pandoc missing")):
            with patch.object(e.latex_exporter, "export_from_document", return_value=fallback) as mock_fb:
                with patch("os.replace") as mock_replace:
                    result = e.export_latex(doc, tex_path)
                    mock_fb.assert_called_once_with(doc, os.path.dirname(tex_path))
                    mock_replace.assert_called_once_with(fallback, tex_path)
                    assert result == tex_path

    def test_export_latex_both_fail(self, tmp_path):
        """Both convert_to_latex and export_from_document fail."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(output_path="/tmp/in.docx")
        e = Exporter()
        with patch.object(e.latex_exporter, "convert_to_latex", side_effect=RuntimeError("pandoc missing")):
            with patch.object(e.latex_exporter, "export_from_document", side_effect=RuntimeError("no template")):
                result = e.export_latex(doc, str(tmp_path / "out.tex"))
                assert result is None

class TestExporterGetExportFormatsGaps:
    """Cover remaining branches in _get_export_formats."""

    def test_empty_format_name_skipped(self):
        """Line 200: empty format name filtered."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock(spec=PipelineDocument)
        doc.formatting_options = {"export_formats": ["docx", "", "json"]}
        doc.document_id = "d1"
        result = Exporter()._get_export_formats(doc)
        assert "docx" in result
        assert "json" in result
        assert len(result) == 2

    def test_duplicate_format_deduplicated(self):
        """Duplicate format names removed."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock(spec=PipelineDocument)
        doc.formatting_options = {"export_formats": ["docx", "json", "docx"]}
        doc.document_id = "d1"
        result = Exporter()._get_export_formats(doc)
        assert result.count("docx") == 1
        assert result.count("json") == 1

class TestExporterBuildMarkdownGaps:
    """Cover remaining branches in _build_markdown."""

    _UNSET = object()

    def _make_doc(self, title="Paper", authors=None, template=_UNSET, keywords=None, abstract=None, affiliations=None, doi=None, blocks=None, references=None):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock(spec=PipelineDocument)
        doc.document_id = "d1"
        doc.original_filename = "test.docx"
        doc.template = template if template is not self._UNSET else MagicMock(template_name="ieee")
        meta = MagicMock()
        meta.title = title
        meta.authors = authors or []
        meta.affiliations = affiliations or []
        meta.doi = doi
        meta.abstract = abstract
        meta.keywords = keywords or []
        doc.metadata = meta
        doc.blocks = blocks or []
        doc.references = references or []
        return doc

    def test_markdown_with_template_name(self):
        """Line 250-252: template name rendered."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        md = Exporter()._build_markdown(self._make_doc(title="Paper", authors=["Alice"]))
        assert "**Template:** ieee" in md

    def test_markdown_no_template(self):
        """No template name."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(title="Paper", template=None)
        md = Exporter()._build_markdown(doc)
        assert "**Template:** " not in md

    def test_markdown_references_formatted_text(self):
        """Line 268: ref with formatted_text."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        r = MagicMock(formatted_text="[1] Smith et al.", raw_text=None, index=0)
        md = Exporter()._build_markdown(self._make_doc(title=None, authors=[], references=[r]))
        assert "[1] Smith et al." in md

    def test_markdown_references_raw_text_fallback(self):
        """Ref with raw_text fallback when formatted_text is None."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        r = MagicMock(formatted_text=None, raw_text="Smith, J. (2023).", index=0)
        md = Exporter()._build_markdown(self._make_doc(title=None, authors=[], references=[r]))
        assert "Smith, J. (2023)." in md

    def test_markdown_references_empty_filtered(self):
        """Ref with both formatted_text and raw_text empty is filtered."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        r1 = MagicMock(formatted_text="[1] Real", raw_text=None, index=0)
        r2 = MagicMock(formatted_text=None, raw_text=None, index=1)
        md = Exporter()._build_markdown(self._make_doc(title=None, authors=[], references=[r1, r2]))
        lines = md.split("\n")
        ref_nums = [l for l in lines if l.strip().startswith("1.")]
        assert len(ref_nums) == 1

    def test_markdown_with_keywords(self):
        """Keywords rendered."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        md = Exporter()._build_markdown(self._make_doc(title="Paper", authors=[], keywords=["ai", "nlp"]))
        assert "**Keywords:** ai, nlp" in md

# ===========================================================================
# jats_generator.py gap coverage
# ===========================================================================

class TestJATSGeneratorGaps:
    """Cover all uncovered lines in jats_generator.py."""

    _DEFAULT_AUTHORS = ["John Doe"]

    def _doc(self, title="Test", authors=_DEFAULT_AUTHORS, publication_date=None, volume=None,
             issue=None, abstract=None, blocks=None, references=None, equations=None):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock()
        doc.metadata.title = title
        doc.metadata.authors = authors if authors is not self._DEFAULT_AUTHORS else ["John Doe"]
        doc.metadata.publication_date = publication_date
        doc.metadata.volume = volume
        doc.metadata.issue = issue
        doc.metadata.abstract = abstract
        doc.blocks = blocks or []
        doc.references = references or []
        doc.equations = equations or []
        return doc

    def test_add_references_full_structure(self):
        """Lines 54-71: ref-list, title, ref, mixed-citation, pub-id."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = MagicMock(reference_id="r1", raw_text="Smith et al. 2023", metadata={"doi": "10.1234/abc"})
        xml = JATSGenerator().to_xml(self._doc(references=[ref]))
        assert "<ref-list>" in xml
        assert "<title>References</title>" in xml
        assert '<ref id="r1">' in xml
        assert "<mixed-citation>" in xml
        assert '<pub-id pub-id-type="doi">' in xml

    def test_add_references_no_doi_in_metadata(self):
        """Ref without doi in metadata."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = MagicMock(reference_id="r2", raw_text="Smith et al. 2023", metadata={})
        xml = JATSGenerator().to_xml(self._doc(references=[ref]))
        assert "<pub-id" not in xml

    def test_add_references_no_metadata_dict(self):
        """Ref with metadata=None."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = MagicMock(reference_id="r3", raw_text="Smith et al. 2023", metadata=None)
        xml = JATSGenerator().to_xml(self._doc(references=[ref]))
        assert '<ref id="r3">' in xml

    def test_add_references_raw_text_none(self):
        """Ref with raw_text=None uses placeholder."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = MagicMock(reference_id="r4", raw_text=None, metadata=None)
        xml = JATSGenerator().to_xml(self._doc(references=[ref]))
        assert "Reference text unavailable" in xml

    def test_add_references_multiple_refs(self):
        """Multiple references enumerated."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        refs = [
            MagicMock(reference_id="r1", raw_text="First.", metadata=None),
            MagicMock(reference_id=None, raw_text="Second.", metadata=None),
        ]
        xml = JATSGenerator().to_xml(self._doc(references=refs))
        assert '<ref id="r1">' in xml
        assert '<ref id="ref_2">' in xml

    def test_placeholder_authors_added(self):
        """Lines 82-86: No authors adds placeholder."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(authors=[]))
        assert "<surname>Author</surname>" in xml

    def test_single_name_author(self):
        """Author with one word name."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(authors=["Plato"]))
        assert "<surname>Plato</surname>" in xml
        assert "<given-names>Plato</given-names>" in xml

    def test_publication_date_string_year_month_day(self):
        """Lines 103-113: string date with full parts."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(publication_date="2023-05-15"))
        assert "<year>2023</year>" in xml
        assert "<month>05</month>" in xml
        assert "<day>15</day>" in xml

    def test_publication_date_string_year_only(self):
        """String date with year only."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(publication_date="2023"))
        assert "<year>2023</year>" in xml
        assert "<month>" not in xml

    def test_publication_date_string_year_month(self):
        """String date with year-month."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(publication_date="2023-05"))
        assert "<year>2023</year>" in xml
        assert "<month>05</month>" in xml

    def test_publication_date_invalid_parse(self):
        """Date string that fails to parse gracefully."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(publication_date="invalid"))
        assert "<pub-date>" in xml

    def test_volume_element(self):
        """Line 117-118: volume."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(volume="10"))
        assert "<volume>10</volume>" in xml

    def test_issue_element(self):
        """Lines 121-122: issue."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(issue="2"))
        assert "<issue>2</issue>" in xml

    def test_abstract_element(self):
        """Lines 126-128: abstract with p."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        xml = JATSGenerator().to_xml(self._doc(abstract="An abstract."))
        assert "<abstract>" in xml
        assert "<p>An abstract.</p>" in xml

    def test_body_with_heading_then_body(self):
        """Lines 136-145: heading intent creates sec, body creates p."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        h = MagicMock(metadata={"semantic_intent": "heading"}, text="Introduction")
        b = MagicMock(metadata={"semantic_intent": "body"}, text="Content.")
        xml = JATSGenerator().to_xml(self._doc(blocks=[h, b]))
        assert "<sec>" in xml
        assert "<title>Introduction</title>" in xml
        assert "<p>Content.</p>" in xml

    def test_body_with_only_body(self):
        """Only body blocks, no sec."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = MagicMock(metadata={"semantic_intent": "body"}, text="Direct.")
        xml = JATSGenerator().to_xml(self._doc(blocks=[b]))
        assert "<sec>" not in xml
        assert "<p>Direct.</p>" in xml

    def test_body_equation_disp_formula(self):
        """Lines 149-159: disp-formula with mathml."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        eq = MagicMock(
            mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>E</mi></math>",
            equation_id="eq1", is_block=True
        )
        xml = JATSGenerator().to_xml(self._doc(equations=[eq]))
        assert "disp-formula" in xml
        assert "eq1" in xml
        assert "mi" in xml

    def test_body_equation_inline_formula(self):
        """inline-formula for non-block equation."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        eq = MagicMock(
            mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>x</mi></math>",
            equation_id="eq2", is_block=False
        )
        xml = JATSGenerator().to_xml(self._doc(equations=[eq]))
        assert "inline-formula" in xml
        assert "eq2" in xml

    def test_body_equation_invalid_mathml(self):
        """Invalid mathml doesn't crash."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        eq = MagicMock(mathml="<invalid>", equation_id="eq3", is_block=True)
        xml = JATSGenerator().to_xml(self._doc(equations=[eq]))
        assert "disp-formula" in xml

# ===========================================================================
# latex_exporter.py gap coverage
# ===========================================================================

class TestEscapeLatex:
    """Cover escape_latex function."""

    def test_all_special_chars(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        text = "&%$#_{}~^\\"
        r = escape_latex(text)
        assert r == r"\&\%\$\#\_\{\}\textasciitilde{}\textasciicircum{}\textbackslash{}"

    def test_plain_text(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        assert escape_latex("Hello World") == "Hello World"

    def test_mixed_text(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        r = escape_latex("Price: $50 & 20%")
        assert r"\$" in r
        assert r"\&" in r
        assert r"\%" in r

    def test_empty_string(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        assert escape_latex("") == ""

    def test_escaped_backslash_and_tilde(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        r = escape_latex("\\~")
        assert r"\textbackslash{}" in r
        assert r"\textasciitilde{}" in r

class TestResolvePandocBinary:
    """Cover _resolve_pandoc_binary."""

    def test_configured_via_env(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        with patch.dict(os.environ, {"PANDOC_PATH": "/custom/pandoc"}, clear=True):
            assert _resolve_pandoc_binary() == "/custom/pandoc"

    def test_env_blank_fallsback_to_shutil(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        with patch.dict(os.environ, {"PANDOC_PATH": ""}, clear=True):
            with patch("app.pipeline.export.latex_exporter.shutil.which", return_value="/usr/bin/pandoc"):
                assert _resolve_pandoc_binary() == "/usr/bin/pandoc"

    def test_env_empty_fallsback_to_shutil(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.pipeline.export.latex_exporter.shutil.which", return_value="/usr/bin/pandoc"):
                assert _resolve_pandoc_binary() == "/usr/bin/pandoc"

class TestConvertViaPandoc:
    """Cover _convert_via_pandoc."""

    def test_success(self, tmp_path):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        out = str(tmp_path / "out.tex")
        Path(out).write_text("")
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("subprocess.run") as m:
                m.return_value.returncode = 0
                m.return_value.stderr = ""
                m.return_value.stdout = ""
                assert _convert_via_pandoc("/in.docx", out, 120) is True

    def test_no_pandoc_binary(self):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value=None):
            assert _convert_via_pandoc("/in.docx", "/out.tex", 120) is False

    def test_nonzero_returncode(self, tmp_path):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("subprocess.run") as m:
                m.return_value.returncode = 1
                m.return_value.stderr = "error"
                m.return_value.stdout = ""
                assert _convert_via_pandoc("/in.docx", str(tmp_path / "out.tex"), 120) is False

    def test_timeout_expired(self, tmp_path):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pandoc", 120)):
                assert _convert_via_pandoc("/in.docx", str(tmp_path / "out.tex"), 120) is False

    def test_oserror(self, tmp_path):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("subprocess.run", side_effect=OSError("exec format error")):
                assert _convert_via_pandoc("/in.docx", str(tmp_path / "out.tex"), 120) is False

class TestLaTeXExporterExportFromDocument:
    """Cover export_from_document and all _write_* methods."""

    def _make_doc(self, title="Paper", authors=None, abstract=None, keywords=None,
                  blocks=None, figures=None, tables=None, equations=None,
                  references=None, template_name="default", publication_date=None):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = MagicMock(spec=PipelineDocument)
        doc.template = MagicMock(template_name=template_name) if template_name else None
        meta = MagicMock()
        meta.title = title
        meta.authors = authors or []
        meta.abstract = abstract
        meta.keywords = keywords or []
        meta.publication_date = publication_date
        doc.metadata = meta
        doc.blocks = blocks or []
        doc.figures = figures or []
        doc.tables = tables or []
        doc.equations = equations or []
        doc.references = references or []
        return doc

    @staticmethod
    def _block(block_id="b1", index=0, text="Hello", block_type="body"):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = MagicMock(spec=Block)
        b.block_id = block_id
        b.index = index
        b.text = text
        b.block_type = block_type
        return b

    def test_export_from_document_basic(self, tmp_path):
        """Lines 143-185: basic export."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(title="Test", authors=["Alice"], abstract="Abs.", keywords=["ai"])
        exporter = LaTeXExporter()
        result = exporter.export_from_document(doc, str(tmp_path))
        assert result == str(tmp_path / "manuscript.tex")
        content = Path(result).read_text(encoding="utf-8")
        assert r"\documentclass" in content
        assert r"\title{Test}" in content
        assert r"\author{Alice}" in content
        assert r"\begin{abstract}" in content
        assert r"\textbf{Keywords:}" in content
        assert r"\maketitle" in content
        assert r"\end{document}" in content

    def test_write_title_authors(self):
        """Lines 188-199: title, authors, date."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        lines = []
        doc = self._make_doc(title="My Paper", authors=["Alice", "Bob"], publication_date="2024-06-15")
        LaTeXExporter()._write_title_authors(lines, doc)
        text = "\n".join(lines)
        assert r"\title{My Paper}" in text
        assert r"\author{Alice\and Bob}" in text
        assert r"\date{2024-06-15}" in text
        assert r"\maketitle" in text

    def test_write_title_authors_no_date(self):
        """No publication date uses \today."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        lines = []
        doc = self._make_doc(title="Paper", authors=["Alice"])
        LaTeXExporter()._write_title_authors(lines, doc)
        text = "\n".join(lines)
        assert r"\date{\today}" in text

    def test_write_title_authors_no_authors(self):
        """No authors skips author field."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        lines = []
        doc = self._make_doc(title="Paper", authors=[])
        LaTeXExporter()._write_title_authors(lines, doc)
        text = "\n".join(lines)
        assert r"\title{Paper}" in text
        assert r"\author{" not in text

    def test_write_abstract(self):
        """Lines 202-210: abstract and keywords."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        lines = []
        doc = self._make_doc(abstract="Abstract here.", keywords=["ml", "nlp"])
        LaTeXExporter()._write_abstract(lines, doc)
        text = "\n".join(lines)
        assert r"\begin{abstract}" in text
        assert "Abstract here." in text
        assert r"\end{abstract}" in text
        assert r"\textbf{Keywords:} ml, nlp" in text

    def test_write_abstract_no_keywords(self):
        """No keywords skips keywords line."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        lines = []
        doc = self._make_doc(abstract="Abstract here.")
        LaTeXExporter()._write_abstract(lines, doc)
        text = "\n".join(lines)
        assert r"\begin{abstract}" in text
        assert r"\textbf{Keywords:}" not in text

    def test_write_abstract_no_abstract(self):
        """No abstract output."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        lines = []
        doc = self._make_doc(abstract=None)
        LaTeXExporter()._write_abstract(lines, doc)
        assert len(lines) == 0

    def test_write_sections(self):
        """Lines 213-231: heading_1, heading_2, body."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b1 = self._block(index=0, text="Intro", block_type="heading_1")
        b2 = self._block(index=1, text="Sub", block_type="heading_2")
        b3 = self._block(index=2, text="Body text", block_type="body")
        doc = self._make_doc(blocks=[b1, b2, b3])
        lines = []
        LaTeXExporter()._write_sections(lines, doc)
        text = "\n".join(lines)
        assert r"\section{Intro}" in text
        assert r"\subsection{Sub}" in text
        assert "Body text" in text

    def test_write_sections_with_filtered_types(self):
        """reference_entry and figure types skipped."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b1 = self._block(index=0, text="Refs", block_type="heading_1")
        b2 = self._block(index=1, text="[1] Ref", block_type="reference_entry")
        b3 = self._block(index=2, text="Fig caption", block_type="figure")
        doc = self._make_doc(blocks=[b1, b2, b3])
        lines = []
        LaTeXExporter()._write_sections(lines, doc)
        text = "\n".join(lines)
        assert r"\section{Refs}" in text
        assert "[1] Ref" not in text
        assert "Fig caption" not in text

    def test_write_sections_heading_3(self):
        """heading_3 creates subsubsection."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = self._block(index=0, text="Detail", block_type="heading_3")
        doc = self._make_doc(blocks=[b])
        lines = []
        LaTeXExporter()._write_sections(lines, doc)
        text = "\n".join(lines)
        assert r"\subsubsection{Detail}" in text

    def test_write_sections_empty_text_skipped(self):
        """Blocks with empty text are skipped."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        b = self._block(index=0, text="", block_type="body")
        doc = self._make_doc(blocks=[b])
        lines = []
        LaTeXExporter()._write_sections(lines, doc)
        assert len(lines) == 0

    def test_write_figures_with_image_data(self, tmp_path):
        """Lines 234-248: figure with image data."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        fig = MagicMock(index=0, caption_text="Fig 1. Results", image_data=b"pngdata",
                        image_format="png", label="fig:results")
        doc = self._make_doc(figures=[fig])
        lines = []
        LaTeXExporter()._write_figures(lines, doc, out_dir=tmp_path)
        text = "\n".join(lines)
        assert r"\begin{figure}" in text
        assert r"\includegraphics" in text
        assert r"\caption{Fig 1. Results}" in text
        assert r"\label{fig:results}" in text
        assert r"\end{figure}" in text
        assert (tmp_path / "fig_0.png").exists()

    def test_write_figures_no_image_data(self):
        """Figure without image_data, no includegraphics."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        fig = MagicMock(index=0, caption_text="Fig 1.", image_data=None, label=None)
        doc = self._make_doc(figures=[fig])
        lines = []
        LaTeXExporter()._write_figures(lines, doc, out_dir=None)
        text = "\n".join(lines)
        assert r"\begin{figure}" in text
        assert r"\includegraphics" not in text
        assert r"\caption{Fig 1.}" in text

    def test_write_figures_no_caption(self):
        """Figure without caption uses 'Figure' as default."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        fig = MagicMock(index=0, caption_text=None, image_data=None, label=None)
        doc = self._make_doc(figures=[fig])
        lines = []
        LaTeXExporter()._write_figures(lines, doc, out_dir=None)
        text = "\n".join(lines)
        assert r"\caption{Figure}" in text

    def test_write_figures_no_label(self):
        """Figure without label skips label line."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        fig = MagicMock(index=0, caption_text="Fig 1.", image_data=None, label=None)
        doc = self._make_doc(figures=[fig])
        lines = []
        LaTeXExporter()._write_figures(lines, doc, out_dir=None)
        text = "\n".join(lines)
        assert r"\label" not in text

    def test_write_tables_with_rows(self, tmp_path):
        """Lines 251-269: table with rows, header, caption."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        tbl = Table(table_id="t1", num_rows=2, num_cols=2, index=0, block_index=0,
                    caption_text="Table 1. Data",
                    data=[["A", "B"], ["1", "2"]],
                    rows=[["A", "B"], ["1", "2"]])
        doc = self._make_doc(tables=[tbl])
        lines = []
        LaTeXExporter()._write_tables(lines, doc)
        text = "\n".join(lines)
        assert r"\begin{table}" in text
        assert r"\centering" in text
        assert r"\begin{tabular}" in text
        assert r"\hline" in text
        assert "A & B" in text
        assert r"\caption{Table 1. Data}" in text

    def test_write_tables_no_rows(self, tmp_path):
        """Table without rows still produces table shell."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        tbl = Table(table_id="t1", num_rows=0, num_cols=0, index=0, block_index=0,
                    caption_text="T1", data=[], rows=[])
        doc = self._make_doc(tables=[tbl])
        lines = []
        LaTeXExporter()._write_tables(lines, doc)
        text = "\n".join(lines)
        assert r"\begin{table}" in text
        assert r"\caption{T1}" in text

    def test_write_tables_no_caption(self):
        """Table without caption uses 'Table' as default."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        tbl = Table(table_id="t1", num_rows=0, num_cols=0, index=0, block_index=0,
                    caption_text=None, data=[], rows=[])
        doc = self._make_doc(tables=[tbl])
        lines = []
        LaTeXExporter()._write_tables(lines, doc)
        text = "\n".join(lines)
        assert r"\caption{Table}" in text

    def test_write_equations(self):
        """Lines 272-282: equations."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        eq1 = Equation(equation_id="e1", index=0, text=r"\begin{equation}E=mc^2\end{equation}", mathml=None, omml=None, is_block=True)
        eq2 = Equation(equation_id="e2", index=1, text="x+y", mathml=None, omml=None, is_block=True)
        doc = self._make_doc(equations=[eq1, eq2])
        lines = []
        LaTeXExporter()._write_equations(lines, doc)
        text = "\n".join(lines)
        assert r"\begin{equation}E=mc^2\end{equation}" in text
        assert r"\begin{equation}" in text
        assert "x+y" in text
        assert text.count(r"\end{equation}") == 2

    def test_write_equations_empty_text_skipped(self):
        """Equation with empty text skipped."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        eq = Equation(equation_id="e1", index=0, text="", mathml=None, omml=None, is_block=True)
        doc = self._make_doc(equations=[eq])
        lines = []
        LaTeXExporter()._write_equations(lines, doc)
        assert len(lines) == 0

    def test_write_equations_align(self):
        """Equation starting with \begin{align} is passed through."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        eq = Equation(equation_id="e1", index=0, text=r"\begin{align}x+y\end{align}", is_block=True)
        doc = self._make_doc(equations=[eq])
        lines = []
        LaTeXExporter()._write_equations(lines, doc)
        text = "\n".join(lines)
        assert r"\begin{align}" in text
        assert r"\begin{equation}" not in text

    def test_write_bibtex_no_references(self):
        """Line 285-286: no references, return."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(references=[])
        exporter = LaTeXExporter()
        result = exporter._write_bibtex(doc, Path("/tmp/refs.bib"))
        assert result is None

    def test_write_bibtex_with_metadata(self, tmp_path):
        """Lines 287-321: full bibtex with metadata."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = Reference(reference_id="r1", citation_key="R1", raw_text="Smith 2023",
                        index=0, year=2023, authors=["Smith"], title="Paper",
                        metadata={"authors": "Smith, J.", "title": "Paper Title",
                                  "year": 2023, "journal": "JMLR", "doi": "10.1234/abc"})
        doc = self._make_doc(references=[ref])
        bib_path = tmp_path / "refs.bib"
        LaTeXExporter()._write_bibtex(doc, bib_path)
        content = bib_path.read_text(encoding="utf-8")
        assert "@article{ref_1," in content
        assert "author = {Smith, J.}" in content
        assert "title = {Paper Title}" in content
        assert "journal = {JMLR}" in content
        assert "year = {2023}" in content
        assert "doi = {10.1234/abc}" in content

    def test_write_bibtex_without_title(self, tmp_path):
        """Lines 317-318: no title, use @misc with note."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = Reference(reference_id="r1", citation_key="R1", raw_text="Smith 2023",
                        index=0, year=2023, authors=["Smith"], title=None, metadata={})
        doc = self._make_doc(references=[ref])
        bib_path = tmp_path / "refs.bib"
        LaTeXExporter()._write_bibtex(doc, bib_path)
        content = bib_path.read_text(encoding="utf-8")
        assert "@misc{ref_1," in content
        assert "note = {Smith 2023}" in content

    def test_write_bibtex_multiple_entries(self, tmp_path):
        """Multiple references produce multiple bib entries."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        r1 = Reference(reference_id="r1", citation_key="R1", raw_text="First", index=0,
                       title="Paper A", metadata={"title": "Paper A", "authors": "Alice"})
        r2 = Reference(reference_id="r2", citation_key="R2", raw_text="Second", index=1,
                       title=None, metadata={})
        doc = self._make_doc(references=[r1, r2])
        bib_path = tmp_path / "refs.bib"
        LaTeXExporter()._write_bibtex(doc, bib_path)
        content = bib_path.read_text(encoding="utf-8")
        assert "@article{ref_1," in content
        assert "@misc{ref_2," in content

    def test_write_bibtex_empty_raw_text_skipped(self, tmp_path):
        """Reference with empty raw text is skipped, no file created."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = Reference(reference_id="r1", citation_key="R1", raw_text="", index=0, metadata={})
        doc = self._make_doc(references=[ref])
        bib_path = tmp_path / "refs.bib"
        LaTeXExporter()._write_bibtex(doc, bib_path)
        assert not bib_path.exists()

    def test_export_from_document_with_references(self, tmp_path):
        """export_from_document with references includes bibliography."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = Reference(reference_id="r1", citation_key="R1", raw_text="Smith 2023",
                        index=0, title="Paper", metadata={"title": "Paper"})
        doc = self._make_doc(title="Test", references=[ref])
        exporter = LaTeXExporter()
        result = exporter.export_from_document(doc, str(tmp_path))
        content = Path(result).read_text(encoding="utf-8")
        assert r"\printbibliography" in content or r"\bibliography" in content

    def test_export_from_document_ieee_template_with_refs(self, tmp_path):
        """IEEE template uses bibliography command."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        ref = Reference(reference_id="r1", citation_key="R1", raw_text="Smith 2023",
                        index=0, title="Paper", metadata={"title": "Paper"})
        doc = self._make_doc(title="Test", template_name="ieee", references=[ref])
        exporter = LaTeXExporter()
        result = exporter.export_from_document(doc, str(tmp_path))
        content = Path(result).read_text(encoding="utf-8")
        assert r"\bibliography{manuscript}" in content

    def test_export_from_document_none_template(self, tmp_path):
        """Document with template=None uses default template."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = self._make_doc(title="Test", template_name=None)
        exporter = LaTeXExporter()
        result = exporter.export_from_document(doc, str(tmp_path))
        content = Path(result).read_text(encoding="utf-8")
        assert r"\documentclass[11pt,a4paper]{article}" in content

# ===========================================================================
# pdf_exporter.py gap coverage
# ===========================================================================

class TestPDFExporterGaps:
    """Cover uncovered lines in pdf_exporter.py."""

    def test_weasyprint_with_paragraphs(self, tmp_path):
        """Lines 54-56: paragraphs built from docx paragraphs."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import types
        wp_mod = types.ModuleType("weasyprint")
        wp_mod.HTML = MagicMock()
        docx_mod = types.ModuleType("docx")
        para1 = MagicMock()
        para1.text = "First paragraph"
        para2 = MagicMock()
        para2.text = "Second paragraph"
        docx_mod.Document = MagicMock()
        docx_mod.Document.return_value.paragraphs = [para1, para2]
        pdf = str(tmp_path / "o.pdf")
        with patch.dict("sys.modules", {"weasyprint": wp_mod, "docx": docx_mod}):
            with patch("os.path.exists", return_value=True):
                r = PDFExporter()._weasyprint_fallback("/in.docx", pdf)
                assert r == pdf

    def test_weasyprint_empty_paragraphs(self, tmp_path):
        """Lines 58-61: empty paragraphs add empty <p>."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import types
        wp_mod = types.ModuleType("weasyprint")
        wp_mod.HTML = MagicMock()
        docx_mod = types.ModuleType("docx")
        para = MagicMock()
        para.text = ""
        docx_mod.Document = MagicMock()
        docx_mod.Document.return_value.paragraphs = [para]
        pdf = str(tmp_path / "o.pdf")
        with patch.dict("sys.modules", {"weasyprint": wp_mod, "docx": docx_mod}):
            with patch("os.path.exists", return_value=True):
                r = PDFExporter()._weasyprint_fallback("/in.docx", pdf)
                assert r == pdf

    def test_weasyprint_no_paragraphs(self, tmp_path):
        """No paragraphs at all."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import types
        wp_mod = types.ModuleType("weasyprint")
        wp_mod.HTML = MagicMock()
        docx_mod = types.ModuleType("docx")
        docx_mod.Document = MagicMock()
        docx_mod.Document.return_value.paragraphs = []
        pdf = str(tmp_path / "o.pdf")
        with patch.dict("sys.modules", {"weasyprint": wp_mod, "docx": docx_mod}):
            with patch("os.path.exists", return_value=True):
                r = PDFExporter()._weasyprint_fallback("/in.docx", pdf)
                assert r == pdf

    def test_weasyprint_pdf_not_created_returns_none(self, tmp_path):
        """Line 72: PDF not created returns None."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import types
        wp_mod = types.ModuleType("weasyprint")
        wp_mod.HTML = MagicMock()
        docx_mod = types.ModuleType("docx")
        docx_mod.Document = MagicMock()
        docx_mod.Document.return_value.paragraphs = []
        pdf = str(tmp_path / "o.pdf")
        with patch.dict("sys.modules", {"weasyprint": wp_mod, "docx": docx_mod}):
            with patch("os.path.exists", return_value=False):
                r = PDFExporter()._weasyprint_fallback("/in.docx", pdf)
                assert r is None

    def test_libreoffice_not_found_logging(self, tmp_path):
        """Line 116: libreoffice not found message."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        f = tmp_path / "in.docx"
        f.write_text("d")
        pdf = str(tmp_path / "in.pdf")
        with patch.object(PDFExporter, "_weasyprint_fallback", return_value=pdf):
            with patch.object(PDFExporter, "_find_libreoffice", return_value=None):
                with patch("app.pipeline.export.pdf_exporter.settings.LIBREOFFICE_PATH", None):
                    with patch("app.pipeline.export.pdf_exporter.logger.warning") as mock_log:
                        result = PDFExporter(libreoffice_path=None).convert_to_pdf(str(f), str(tmp_path))
                        mock_log.assert_called_once()
                        assert "LibreOffice not found" in mock_log.call_args[0][0]

    def test_docx2pdf_fallback_success(self, tmp_path):
        """Lines 127-129: docx2pdf fallback succeeds."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import types
        d2p_mod = types.ModuleType("docx2pdf")
        d2p_mod.convert = MagicMock()
        f = tmp_path / "in.docx"
        f.write_text("d")
        pdf_path = str(tmp_path / "in.pdf")
        r = MagicMock(returncode=1, stderr="e", stdout="")
        docx_path = str(f)
        with patch("app.pipeline.export.pdf_exporter.subprocess.run", return_value=r):
            with patch.object(PDFExporter, "_weasyprint_fallback", return_value=None):
                with patch.dict("sys.modules", {"docx2pdf": d2p_mod}):
                    with patch("os.path.exists", side_effect=lambda p: p == docx_path or p == pdf_path):
                        with patch("os.path.abspath", side_effect=lambda p: p):
                            result = PDFExporter("/soffice").convert_to_pdf(docx_path, str(tmp_path))
                            assert result == pdf_path

    def test_docx2pdf_fallback_fails_raises(self, tmp_path):
        """Line 130-133: docx2pdf fails, RuntimeError raised."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import types
        d2p_mod = types.ModuleType("docx2pdf")
        d2p_mod.convert = MagicMock(side_effect=Exception("docx2pdf error"))
        f = tmp_path / "in.docx"
        f.write_text("d")
        docx_path = str(f)
        r = MagicMock(returncode=1, stderr="e", stdout="")
        with patch("app.pipeline.export.pdf_exporter.subprocess.run", return_value=r):
            with patch.object(PDFExporter, "_weasyprint_fallback", return_value=None):
                with patch.dict("sys.modules", {"docx2pdf": d2p_mod}):
                    with patch("os.path.exists", side_effect=lambda p: p == docx_path):
                        with pytest.raises(RuntimeError, match="Both PDF export engines failed"):
                            PDFExporter("/soffice").convert_to_pdf(docx_path, str(tmp_path))

    def test_docx2pdf_fallback_pdf_not_found_raises(self, tmp_path):
        """Line 130: PDF not found after docx2pdf conversion."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import types
        d2p_mod = types.ModuleType("docx2pdf")
        d2p_mod.convert = MagicMock()
        f = tmp_path / "in.docx"
        f.write_text("d")
        docx_path = str(f)
        r = MagicMock(returncode=1, stderr="e", stdout="")
        with patch("app.pipeline.export.pdf_exporter.subprocess.run", return_value=r):
            with patch.object(PDFExporter, "_weasyprint_fallback", return_value=None):
                with patch.dict("sys.modules", {"docx2pdf": d2p_mod}):
                    with patch("os.path.exists", side_effect=lambda p: p == docx_path):
                        with patch("os.path.abspath", side_effect=lambda p: p):
                            with pytest.raises(RuntimeError, match="generated PDF not found"):
                                PDFExporter("/soffice").convert_to_pdf(docx_path, str(tmp_path))
