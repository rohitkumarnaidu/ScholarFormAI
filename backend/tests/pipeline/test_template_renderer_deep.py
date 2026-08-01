# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep coverage tests for TemplateRenderer — exercises error paths, fallbacks,
edge cases, and uncovered branches to raise coverage from 54.86% to >=80%.
"""

from app.models import PipelineDocument, Block, BlockType, Reference, DocumentMetadata
from app.models import PipelineDocument, Block, BlockType, Reference, DocumentMetadata
from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.models import Block, BlockType, Reference, DocumentMetadata
import pytest

from app.pipeline.formatting.template_renderer import TemplateRenderer


@pytest.fixture
def renderer():

    return TemplateRenderer(templates_dir="app/templates")


def _make_block(block_id, index, block_type, text="", metadata=None):
    return Block(
        block_id=block_id,
        index=index,
        block_type=block_type,
        text=text,
        metadata=metadata or {},
    )


def _make_ref(reference_id, index, citation_key="cit1", raw_text="Raw", formatted_text="Formatted"):
    return Reference(
        reference_id=reference_id,
        index=index,
        citation_key=citation_key,
        raw_text=raw_text,
        formatted_text=formatted_text,
    )


def _make_doc(blocks=None, references=None, metadata=None, formatting_options=None, original_filename="manuscript.pdf"):
    return PipelineDocument(
        document_id="test_doc",
        blocks=blocks or [],
        references=references or [],
        metadata=metadata or DocumentMetadata(),
        formatting_options=formatting_options or {},
        original_filename=original_filename,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. docxtpl not available
# ══════════════════════════════════════════════════════════════════════════════

class TestDocxTplNotAvailable:
    """render() must raise ImportError when _DOCXTPL_AVAILABLE = False."""

    def test_render_raises_import_error(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        with patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", False):
            with pytest.raises(ImportError, match="docxtpl is not installed"):
                renderer.render(document=doc)

    def test_render_raises_import_error_with_none_doc(self, renderer):
        with patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", False):
            with pytest.raises(ImportError, match="docxtpl is not installed"):
                renderer.render(document=None)

    def test_render_no_docxtpl_never_checks_document(self, renderer):
        with patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", False):
            with pytest.raises(ImportError):
                renderer.render(document=None)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Render edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestRenderEdgeCases:
    """Edge cases in render() beyond docxtpl availability."""

    def test_render_document_none_raises_value_error(self, renderer):
        with patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True):
            with pytest.raises(ValueError, match="document must not be None"):
                renderer.render(document=None)

    def test_render_empty_template_name_defaults_to_ieee(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        doc.metadata = DocumentMetadata()
        doc.blocks = []
        doc.references = []
        doc.formatting_options = {}
        doc.original_filename = None
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(renderer, "_resolve_template_path", return_value=Path("dummy.docx")),
            patch.object(renderer, "build_context", return_value={}),
            patch("app.pipeline.formatting.template_renderer.DocxTemplate") as mock_dt,
        ):
            mock_instance = MagicMock()
            mock_dt.return_value = mock_instance
            result = renderer.render(document=doc, template_name="")
        mock_dt.assert_called_once()
        assert result is mock_instance

    def test_render_exception_is_re_raised(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        doc.metadata = DocumentMetadata()
        doc.blocks = []
        doc.references = []
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(renderer, "_resolve_template_path", side_effect=Exception("boom")),
        ):
            with pytest.raises(Exception, match="boom"):
                renderer.render(document=doc)

    def test_render_with_whitespace_template_name(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        doc.metadata = DocumentMetadata()
        doc.blocks = []
        doc.references = []
        doc.formatting_options = {}
        doc.original_filename = None
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(renderer, "_resolve_template_path", return_value=Path("dummy.docx")),
            patch.object(renderer, "build_context", return_value={}),
            patch("app.pipeline.formatting.template_renderer.DocxTemplate") as mock_dt,
        ):
            mock_instance = MagicMock()
            mock_dt.return_value = mock_instance
            result = renderer.render(document=doc, template_name="   ")
        assert result is mock_instance


# ══════════════════════════════════════════════════════════════════════════════
# 3. has_renderable_template
# ══════════════════════════════════════════════════════════════════════════════

class TestHasRenderableTemplate:
    """has_renderable_template must detect Jinja2 source or marker-bearing DOCX."""

    def test_jinja_source_exists(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        (style_dir / "template.jinja2").write_text("{{ title }}")
        assert renderer.has_renderable_template("ieee") is True

    def test_docx_with_markers(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        docx_path = style_dir / "template.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>{{ title }}</w:document>")
        assert renderer.has_renderable_template("ieee") is True

    def test_docx_without_markers(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        docx_path = style_dir / "template.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>No markers here</w:document>")
        assert renderer.has_renderable_template("ieee") is False

    def test_no_template_dir_returns_false(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path / "nonexistent"
        assert renderer.has_renderable_template("ieee") is False


# ══════════════════════════════════════════════════════════════════════════════
# 4. build_context edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildContext:
    """build_context fallback and edge case paths."""

    def test_abstract_fallback_to_block(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(abstract=None),
            blocks=[_make_block("b1", 0, "abstract_body", "Abstract text from block")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["abstract"] == "Abstract text from block"

    def test_abstract_uses_metadata_when_present(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(abstract="Metadata abstract"),
            blocks=[_make_block("b1", 0, "abstract_body", "Block abstract")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["abstract"] == "Metadata abstract"

    def test_keywords_fallback_to_block_split_by_comma(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(keywords=[]),
            blocks=[_make_block("b1", 0, "keywords_body", "kw1, kw2, kw3")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["keywords"] == ["kw1", "kw2", "kw3"]

    def test_keywords_fallback_empty_raw_returns_empty_list(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(keywords=[]),
            blocks=[_make_block("b1", 0, "keywords_body", "")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["keywords"] == []

    def test_keywords_uses_metadata_when_present(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(keywords=["kw1", "kw2"]),
            blocks=[_make_block("b1", 0, "keywords_body", "block_kw")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["keywords"] == ["kw1", "kw2"]

    def test_authors_fallback_to_blocks(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(authors=[]),
            blocks=[
                _make_block("b1", 0, "author", "Alice"),
                _make_block("b2", 1, "author", "Bob"),
            ],
        )
        ctx = renderer.build_context(doc)
        assert ctx["authors"] == ["Alice", "Bob"]

    def test_authors_uses_metadata_when_present(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(authors=["Meta Author"]),
            blocks=[_make_block("b1", 0, "author", "Block Author")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["authors"] == ["Meta Author"]

    def test_affiliations_fallback_to_blocks(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(affiliations=[]),
            blocks=[
                _make_block("b1", 0, "affiliation", "Univ A"),
                _make_block("b2", 1, "affiliation", "Univ B"),
            ],
        )
        ctx = renderer.build_context(doc)
        assert ctx["affiliations"] == ["Univ A", "Univ B"]

    def test_affiliations_uses_metadata_when_present(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(affiliations=["Meta Affil"]),
            blocks=[_make_block("b1", 0, "affiliation", "Block Affil")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["affiliations"] == ["Meta Affil"]

    def test_title_fallback_to_block(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(title=None),
            blocks=[_make_block("b1", 0, "title", "My Title")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["title"] == "My Title"

    def test_title_fallback_to_original_filename(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(title=None),
            blocks=[],
        )
        ctx = renderer.build_context(doc)
        assert ctx["title"] == "manuscript.pdf"

    def test_title_fallback_to_untitled(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(title=None),
            blocks=[],
            original_filename=None,
        )
        ctx = renderer.build_context(doc)
        assert ctx["title"] == "Untitled Manuscript"

    def test_formatting_options_cover_page_false(self, renderer):
        doc = _make_doc(formatting_options={"cover_page": False})
        ctx = renderer.build_context(doc)
        assert ctx["cover_page"] is False

    def test_formatting_options_toc_true(self, renderer):
        doc = _make_doc(formatting_options={"toc": True})
        ctx = renderer.build_context(doc)
        assert ctx["toc"] is True

    def test_formatting_options_page_numbers_false(self, renderer):
        doc = _make_doc(formatting_options={"page_numbers": False})
        ctx = renderer.build_context(doc)
        assert ctx["page_numbers"] is False

    def test_formatting_options_add_cover_page_key(self, renderer):
        doc = _make_doc(formatting_options={"add_cover_page": False})
        ctx = renderer.build_context(doc)
        assert ctx["cover_page"] is False

    def test_formatting_options_generate_toc_key(self, renderer):
        doc = _make_doc(formatting_options={"generate_toc": True})
        ctx = renderer.build_context(doc)
        assert ctx["toc"] is True

    def test_formatting_options_add_page_numbers_key(self, renderer):
        doc = _make_doc(formatting_options={"add_page_numbers": False})
        ctx = renderer.build_context(doc)
        assert ctx["page_numbers"] is False

    def test_formatting_options_page_number_value(self, renderer):
        doc = _make_doc(formatting_options={"page_number": "3"})
        ctx = renderer.build_context(doc)
        assert ctx["page_number"] == "3"

    def test_formatting_options_defaults(self, renderer):
        doc = _make_doc(formatting_options={})
        ctx = renderer.build_context(doc)
        assert ctx["cover_page"] is True
        assert ctx["toc"] is False
        assert ctx["page_numbers"] is True
        assert ctx["page_number"] == "1"

    def test_exception_re_raised(self, renderer):
        doc = _make_doc()
        # Simulate a failure during context building by making a block sorting raise
        doc.blocks = _make_block("b1", 0, "abstract_body", "test")
        # Monkey-patch sorted to raise when called with blocks
        with patch("app.pipeline.formatting.template_renderer.sorted", side_effect=Exception("ctx fail")):
            with pytest.raises(Exception, match="ctx fail"):
                renderer.build_context(doc)


# ══════════════════════════════════════════════════════════════════════════════
# 5. _build_template_from_jinja_source
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildTemplateFromJinjaSource:
    """Wrap plain-text Jinja2 source in a minimal DOCX container."""

    def test_build_success(self, renderer, tmp_path):
        source = tmp_path / "template.jinja2"
        source.write_text("{{ title }}\n{{ abstract }}")
        fake_docx = tmp_path / "out.docx"
        with (
            patch("app.pipeline.formatting.template_renderer.tempfile.NamedTemporaryFile") as mock_ntf,
            patch("app.pipeline.formatting.template_renderer.WordDocument") as mock_wd_cls,
        ):
            mock_file = MagicMock()
            mock_file.name = str(fake_docx)
            mock_ntf.return_value.__enter__.return_value = mock_file
            mock_doc = MagicMock()
            mock_wd_cls.return_value = mock_doc
            result = renderer._build_template_from_jinja_source(source)
        assert result == fake_docx
        assert mock_doc.add_paragraph.call_count == 2
        mock_doc.save.assert_called_once_with(str(fake_docx))

    def test_build_failure_falls_back(self, renderer, tmp_path):
        source = tmp_path / "template.jinja2"
        source.write_text("{{ title }}")
        with (
            patch("app.pipeline.formatting.template_renderer.tempfile.NamedTemporaryFile", side_effect=Exception("temp fail")),
            patch.object(renderer, "_build_fallback_template", return_value=Path("fallback.docx")),
        ):
            result = renderer._build_template_from_jinja_source(source)
        assert result == Path("fallback.docx")

    def test_build_source_read_error_falls_back(self, renderer, tmp_path):
        source = tmp_path / "template.jinja2"
        with (
            patch.object(Path, "read_text", side_effect=OSError("read error")),
            patch.object(renderer, "_build_fallback_template", return_value=Path("fallback.docx")),
        ):
            result = renderer._build_template_from_jinja_source(source)
        assert result == Path("fallback.docx")


# ══════════════════════════════════════════════════════════════════════════════
# 6. _has_template_markers
# ══════════════════════════════════════════════════════════════════════════════

class TestHasTemplateMarkers:
    """Detect Jinja2 markers {{ }} and {% %} inside DOCX XML."""

    def test_markers_in_raw_xml(self, renderer, tmp_path):
        docx_path = tmp_path / "test.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>{{ title }}</w:document>")
        assert renderer._has_template_markers(docx_path) is True

    def test_markers_in_stripped_text_only(self, renderer, tmp_path):
        docx_path = tmp_path / "test.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:p><w:r><w:t>{{ title }}</w:t></w:r></w:p>")
        assert renderer._has_template_markers(docx_path) is True

    def test_block_marker_in_stripped_text(self, renderer, tmp_path):
        docx_path = tmp_path / "test.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:p><w:r><w:t>{% for x in items %}</w:t></w:r></w:p>")
        assert renderer._has_template_markers(docx_path) is True

    def test_no_markers_returns_false(self, renderer, tmp_path):
        docx_path = tmp_path / "test.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>Plain text; no markers</w:document>")
        assert renderer._has_template_markers(docx_path) is False

    def test_exception_during_zip_read_returns_false(self, renderer):
        fake_path = Path("/nonexistent/template.docx")
        result = renderer._has_template_markers(fake_path)
        assert result is False

    def test_cache_used_on_second_call(self, renderer, tmp_path):
        docx_path = tmp_path / "test.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>No markers</w:document>")
        assert renderer._has_template_markers(docx_path) is False
        assert renderer._template_marker_cache[docx_path] is False
        assert renderer._has_template_markers(docx_path) is False

    def test_cache_true_value(self, renderer, tmp_path):
        docx_path = tmp_path / "test.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>{% for x in items %}{{ x }}{% endfor %}</w:document>")
        assert renderer._has_template_markers(docx_path) is True
        assert renderer._template_marker_cache[docx_path] is True
        assert renderer._has_template_markers(docx_path) is True

    def test_non_word_xml_ignored(self, renderer, tmp_path):
        docx_path = tmp_path / "test.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>Plain</w:document>")
            zf.writestr("docProps/app.xml", "{{ should_be_ignored }}")
        assert renderer._has_template_markers(docx_path) is False


# ══════════════════════════════════════════════════════════════════════════════
# 7. _build_fallback_template
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildFallbackTemplate:
    """Create a minimal DOCX with all expected Jinja2 markers."""

    def test_creates_temp_docx(self, renderer, tmp_path):
        fake_docx = tmp_path / "fallback_xxx.docx"
        with (
            patch("app.pipeline.formatting.template_renderer.tempfile.NamedTemporaryFile") as mock_ntf,
            patch("app.pipeline.formatting.template_renderer.WordDocument") as mock_wd_cls,
        ):
            mock_file = MagicMock()
            mock_file.name = str(fake_docx)
            mock_ntf.return_value.__enter__.return_value = mock_file
            mock_doc = MagicMock()
            mock_wd_cls.return_value = mock_doc
            result = renderer._build_fallback_template()
        assert result == fake_docx
        mock_doc.save.assert_called_once_with(str(fake_docx))
        # Verify expected paragraph patterns were added
        title_calls = [c for c in mock_doc.add_paragraph.call_args_list if c[0][0] == "{{ title }}"]
        assert len(title_calls) == 1

    def test_exception_raised(self, renderer):
        with (
            patch("app.pipeline.formatting.template_renderer.tempfile.NamedTemporaryFile", side_effect=Exception("no temp")),
        ):
            with pytest.raises(Exception, match="no temp"):
                renderer._build_fallback_template()


# ══════════════════════════════════════════════════════════════════════════════
# 8. _collect_sections
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectSections:
    """Group non-reference content into heading sections."""

    def test_multiple_sections_with_paragraphs(self, renderer):
        blocks = [
            _make_block("b1", 0, "heading_1", "Introduction"),
            _make_block("b2", 1, "body", "Intro paragraph 1"),
            _make_block("b3", 2, "body", "Intro paragraph 2"),
            _make_block("b4", 3, "heading_1", "Methods"),
            _make_block("b5", 4, "body", "Methods paragraph"),
        ]
        sections = renderer._collect_sections(blocks)
        assert len(sections) == 2
        assert sections[0]["heading"] == "Introduction"
        assert sections[0]["paragraphs"] == ["Intro paragraph 1", "Intro paragraph 2"]
        assert sections[1]["heading"] == "Methods"
        assert sections[1]["paragraphs"] == ["Methods paragraph"]

    def test_all_skip_types_filtered_out(self, renderer):
        blocks = [
            _make_block("b1", 0, "title", "Paper Title"),
            _make_block("b2", 1, "author", "Alice"),
            _make_block("b3", 2, "affiliation", "Univ A"),
            _make_block("b4", 3, "abstract_heading", "Abstract"),
            _make_block("b5", 4, "abstract_body", "Abstract text"),
            _make_block("b6", 5, "keywords_heading", "Keywords"),
            _make_block("b7", 6, "keywords_body", "kw1, kw2"),
            _make_block("b8", 7, "references_heading", "References"),
            _make_block("b9", 8, "reference_entry", "[1] Ref"),
            _make_block("b10", 9, "figure_caption", "Fig 1"),
            _make_block("b11", 10, "table_caption", "Table 1"),
            _make_block("b12", 11, "footnote", "A note"),
            _make_block("b13", 12, "heading_1", "Introduction"),
            _make_block("b14", 13, "body", "Real content"),
        ]
        sections = renderer._collect_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Introduction"
        assert sections[0]["paragraphs"] == ["Real content"]

    def test_footnote_endnote_metadata_skipped(self, renderer):
        blocks = [
            _make_block("b1", 0, "heading_1", "Introduction"),
            _make_block("b2", 1, "body", "Some text"),
            _make_block("b3", 2, "body", "Footnote text", metadata={"is_footnote": True}),
            _make_block("b4", 3, "body", "Endnote text", metadata={"is_endnote": True}),
            _make_block("b5", 4, "body", "More text"),
        ]
        sections = renderer._collect_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["paragraphs"] == ["Some text", "More text"]

    def test_empty_text_blocks_skipped(self, renderer):
        blocks = [
            _make_block("b1", 0, "heading_1", "Intro"),
            _make_block("b2", 1, "body", ""),
            _make_block("b3", 2, "body", "   "),
            _make_block("b4", 3, "body", "Actual"),
        ]
        sections = renderer._collect_sections(blocks)
        assert sections[0]["paragraphs"] == ["Actual"]

    def test_no_blocks_returns_empty_list(self, renderer):
        sections = renderer._collect_sections([])
        assert sections == []

    def test_consecutive_headings(self, renderer):
        blocks = [
            _make_block("b1", 0, "heading_1", "Intro"),
            _make_block("b2", 1, "heading_1", "Methods"),
            _make_block("b3", 2, "body", "Methods paragraph"),
        ]
        sections = renderer._collect_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Methods"
        assert sections[0]["paragraphs"] == ["Methods paragraph"]

    def test_heading_at_end_no_paragraphs(self, renderer):
        blocks = [
            _make_block("b1", 0, "body", "Some content"),
            _make_block("b2", 1, "heading_1", "Conclusion"),
        ]
        sections = renderer._collect_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Body"
        assert sections[0]["paragraphs"] == ["Some content"]


# ══════════════════════════════════════════════════════════════════════════════
# 9. _collect_references
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectReferences:
    """Collect and sort references from the document."""

    def test_sorted_references_with_formatted_text(self, renderer):
        refs = [
            _make_ref("r2", 2, formatted_text="Ref B"),
            _make_ref("r1", 1, formatted_text="Ref A"),
        ]
        doc = _make_doc(references=refs)
        result = renderer._collect_references(doc)
        assert result == ["Ref A", "Ref B"]

    def test_references_only_raw_text(self, renderer):
        refs = [
            _make_ref("r1", 1, formatted_text=None, raw_text="Raw Ref"),
        ]
        doc = _make_doc(references=refs)
        result = renderer._collect_references(doc)
        assert result == ["Raw Ref"]

    def test_references_empty_formatted_and_raw_skipped(self, renderer):
        refs = [
            _make_ref("r1", 1, formatted_text="", raw_text="   "),
            _make_ref("r2", 2, formatted_text="Real", raw_text="Raw"),
        ]
        doc = _make_doc(references=refs)
        result = renderer._collect_references(doc)
        assert result == ["Real"]

    def test_fallback_to_reference_blocks(self, renderer):
        blocks = [
            _make_block("b1", 0, "reference_entry", "[1] Block ref"),
            _make_block("b2", 1, "reference_entry", "[2] Another ref"),
        ]
        doc = _make_doc(references=[], blocks=blocks)
        result = renderer._collect_references(doc)
        assert result == ["[1] Block ref", "[2] Another ref"]

    def test_fallback_empty_blocks(self, renderer):
        doc = _make_doc(references=[], blocks=[])
        result = renderer._collect_references(doc)
        assert result == []

    def test_fallback_skips_empty_block_text(self, renderer):
        blocks = [
            _make_block("b1", 0, "reference_entry", "[1] Real"),
            _make_block("b2", 1, "reference_entry", ""),
            _make_block("b3", 2, "reference_entry", "   "),
        ]
        doc = _make_doc(references=[], blocks=blocks)
        result = renderer._collect_references(doc)
        assert result == ["[1] Real"]

    def test_references_all_empty_falls_back_to_blocks(self, renderer):
        """When all reference objects have empty text, fall back to blocks."""
        refs = [
            _make_ref("r1", 1, formatted_text="", raw_text="   "),
            _make_ref("r2", 2, formatted_text=None, raw_text=""),
        ]
        blocks = [
            _make_block("b1", 0, "reference_entry", "[1] Block ref"),
        ]
        doc = _make_doc(references=refs, blocks=blocks)
        result = renderer._collect_references(doc)
        assert result == ["[1] Block ref"]


# ══════════════════════════════════════════════════════════════════════════════
# 10. _resolve_template_path
# ══════════════════════════════════════════════════════════════════════════════

class TestResolveTemplatePath:
    """Resolve the best available template path."""

    def test_jinja_source_exists(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        jinja = style_dir / "template.jinja2"
        jinja.write_text("{{ title }}")
        fake_docx = tmp_path / "output.docx"
        with (
            patch("app.pipeline.formatting.template_renderer.tempfile.NamedTemporaryFile") as mock_ntf,
            patch("app.pipeline.formatting.template_renderer.WordDocument") as mock_wd_cls,
        ):
            mock_file = MagicMock()
            mock_file.name = str(fake_docx)
            mock_ntf.return_value.__enter__.return_value = mock_file
            mock_doc = MagicMock()
            mock_wd_cls.return_value = mock_doc
            result = renderer._resolve_template_path("ieee")
        assert result == fake_docx

    def test_docx_with_markers_returned_directly(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        docx_path = style_dir / "template.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>{{ title }}</w:document>")
        result = renderer._resolve_template_path("ieee")
        assert result == docx_path

    def test_docx_without_markers_falls_back(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        docx_path = style_dir / "template.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>No markers</w:document>")
        fake_fallback = tmp_path / "fallback.docx"
        with patch.object(renderer, "_build_fallback_template", return_value=fake_fallback):
            result = renderer._resolve_template_path("ieee")
        assert result == fake_fallback

    def test_no_template_file_falls_back(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        fake_fallback = tmp_path / "fallback.docx"
        with patch.object(renderer, "_build_fallback_template", return_value=fake_fallback):
            result = renderer._resolve_template_path("ieee")
        assert result == fake_fallback

    def test_empty_template_name_defaults(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        fake_fallback = tmp_path / "fallback.docx"
        with patch.object(renderer, "_build_fallback_template", return_value=fake_fallback):
            result = renderer._resolve_template_path("")
        assert result == fake_fallback


# ══════════════════════════════════════════════════════════════════════════════
# 11. _resolve_bool_option
# ══════════════════════════════════════════════════════════════════════════════

class TestResolveBoolOption:
    """Resolve boolean option from dict with fallback key list."""

    def test_first_key_matches(self, renderer):
        options = {"cover_page": False, "add_cover_page": True}
        result = renderer._resolve_bool_option(options, ["cover_page", "add_cover_page"], True)
        assert result is False

    def test_second_key_matches(self, renderer):
        options = {"add_cover_page": True}
        result = renderer._resolve_bool_option(options, ["cover_page", "add_cover_page"], False)
        assert result is True

    def test_no_key_matches_returns_default(self, renderer):
        options = {"other_key": True}
        result = renderer._resolve_bool_option(options, ["cover_page", "add_cover_page"], False)
        assert result is False

    def test_coerces_value_through_coerce_bool(self, renderer):
        options = {"toc": 1}
        result = renderer._resolve_bool_option(options, ["toc", "generate_toc"], False)
        assert result is True

    def test_string_true_value(self, renderer):
        options = {"toc": "yes"}
        result = renderer._resolve_bool_option(options, ["toc", "generate_toc"], False)
        assert result is True


# ══════════════════════════════════════════════════════════════════════════════
# 12. _coerce_bool (additional edge cases)
# ══════════════════════════════════════════════════════════════════════════════

class TestCoerceBool:
    """Edge cases for the static _coerce_bool helper."""

    def test_float_zero_point_zero(self, renderer):
        assert renderer._coerce_bool(0.0, True) is False

    def test_float_zero_point_five(self, renderer):
        assert renderer._coerce_bool(0.5, False) is True

    def test_empty_string(self, renderer):
        assert renderer._coerce_bool("", True) is False
        assert renderer._coerce_bool("", False) is False

    def test_unknown_string_defaults_to_bool(self, renderer):
        assert renderer._coerce_bool("random", True) is True
        assert renderer._coerce_bool("random", False) is True

    def test_none_value(self, renderer):
        assert renderer._coerce_bool(None, True) is True
        assert renderer._coerce_bool(None, False) is False


# ══════════════════════════════════════════════════════════════════════════════
# 13. _block_type_token
# ══════════════════════════════════════════════════════════════════════════════

class TestBlockTypeToken:
    """Static helper that normalises block type to lowercase string."""

    def test_string_block_type(self, renderer):
        block = MagicMock()
        block.block_type = "ABSTRACT_BODY"
        assert renderer._block_type_token(block) == "abstract_body"

    def test_enum_block_type(self, renderer):
        block = MagicMock()
        block.block_type = BlockType.ABSTRACT_BODY
        assert renderer._block_type_token(block) == "abstract_body"

    def test_missing_block_type_defaults_empty(self, renderer):
        block = MagicMock(spec=[])
        del block.block_type
        assert renderer._block_type_token(block) == ""

    def test_padded_string(self, renderer):
        block = MagicMock()
        block.block_type = "  Heading_1  "
        assert renderer._block_type_token(block) == "heading_1"


# ══════════════════════════════════════════════════════════════════════════════
# 14. _first_block_text / _all_block_text (helpers for build_context)
# ══════════════════════════════════════════════════════════════════════════════

class TestFirstBlockText:
    def test_finds_matching_block(self, renderer):
        blocks = [
            _make_block("b1", 0, "abstract_body", "Abstract text"),
            _make_block("b2", 1, "body", "Other text"),
        ]
        assert renderer._first_block_text(blocks, "abstract_body") == "Abstract text"

    def test_returns_first_by_index(self, renderer):
        blocks = [
            _make_block("b1", 1, "abstract_body", "Second"),
            _make_block("b2", 0, "abstract_body", "First"),
        ]
        assert renderer._first_block_text(blocks, "abstract_body") == "First"

    def test_empty_when_no_match(self, renderer):
        blocks = [_make_block("b1", 0, "body", "Text")]
        assert renderer._first_block_text(blocks, "abstract_body") == ""

    def test_skips_empty_text(self, renderer):
        blocks = [
            _make_block("b1", 0, "abstract_body", ""),
            _make_block("b2", 1, "abstract_body", "Real"),
        ]
        assert renderer._first_block_text(blocks, "abstract_body") == "Real"


class TestAllBlockText:
    def test_collects_all_matching(self, renderer):
        blocks = [
            _make_block("b1", 0, "author", "Alice"),
            _make_block("b2", 1, "author", "Bob"),
            _make_block("b3", 2, "body", "Not author"),
        ]
        assert renderer._all_block_text(blocks, "author") == ["Alice", "Bob"]

    def test_returns_sorted_by_index(self, renderer):
        blocks = [
            _make_block("b1", 1, "author", "Second"),
            _make_block("b2", 0, "author", "First"),
        ]
        assert renderer._all_block_text(blocks, "author") == ["First", "Second"]

    def test_empty_when_no_match(self, renderer):
        blocks = [_make_block("b1", 0, "body", "Text")]
        assert renderer._all_block_text(blocks, "affiliation") == []

    def test_skips_empty_text_entries(self, renderer):
        blocks = [
            _make_block("b1", 0, "affiliation", ""),
            _make_block("b2", 1, "affiliation", "Real"),
        ]
        assert renderer._all_block_text(blocks, "affiliation") == ["Real"]
