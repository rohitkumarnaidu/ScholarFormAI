# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Fills remaining coverage gaps in TemplateRenderer beyond test_template_renderer.py
and test_template_renderer_deep.py.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models import Block, BlockType, DocumentMetadata, PipelineDocument, Reference
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
# _coerce_bool — remaining edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestCoerceBoolGaps:
    def test_none_with_true_default(self, renderer):
        assert renderer._coerce_bool(None, True) is True

    def test_none_with_false_default(self, renderer):
        assert renderer._coerce_bool(None, False) is False

    def test_bool_true(self, renderer):
        assert renderer._coerce_bool(True, False) is True

    def test_bool_false(self, renderer):
        assert renderer._coerce_bool(False, True) is False

    def test_int_zero(self, renderer):
        assert renderer._coerce_bool(0, True) is False

    def test_int_nonzero(self, renderer):
        assert renderer._coerce_bool(1, False) is True
        assert renderer._coerce_bool(42, False) is True

    def test_float_zero(self, renderer):
        assert renderer._coerce_bool(0.0, True) is False

    def test_float_nonzero(self, renderer):
        assert renderer._coerce_bool(0.5, False) is True

    def test_string_true_variants(self, renderer):
        for v in ["1", "true", "True", "yes", "on"]:
            assert renderer._coerce_bool(v, False) is True

    def test_string_false_variants(self, renderer):
        for v in ["0", "false", "False", "no", "off", ""]:
            assert renderer._coerce_bool(v, True) is False

    def test_string_unknown(self, renderer):
        assert renderer._coerce_bool("maybe", True) is True
        assert renderer._coerce_bool("maybe", False) is True  # non-empty string → truthy


# ══════════════════════════════════════════════════════════════════════════════
# render — edge case: None template_name is stripped to ieee
# ══════════════════════════════════════════════════════════════════════════════


class TestRenderGaps:
    def test_none_template_name_defaults(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        doc.metadata = DocumentMetadata()
        doc.blocks = []
        doc.references = []
        doc.formatting_options = {}
        doc.original_filename = None
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(renderer, "_resolve_template_path_with_flag", return_value=(Path("dummy.docx"), False)),
            patch.object(renderer, "build_context", return_value={}),
            patch("app.pipeline.formatting.template_renderer.DocxTemplate") as mock_dt,
        ):
            mock_instance = MagicMock()
            mock_dt.return_value = mock_instance
            result = renderer.render(document=doc, template_name=None)
        assert result is mock_instance

    def test_template_name_whitespace_only_defaults(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        doc.metadata = DocumentMetadata()
        doc.blocks = []
        doc.references = []
        doc.formatting_options = {}
        doc.original_filename = None
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(renderer, "_resolve_template_path_with_flag", return_value=(Path("dummy.docx"), False)),
            patch.object(renderer, "build_context", return_value={}),
            patch("app.pipeline.formatting.template_renderer.DocxTemplate") as mock_dt,
        ):
            mock_instance = MagicMock()
            mock_dt.return_value = mock_instance
            result = renderer.render(document=doc, template_name="   ")
        assert result is mock_instance

    def test_render_raises_on_template_resolve_failure(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        doc.metadata = DocumentMetadata()
        doc.blocks = []
        doc.references = []
        doc.formatting_options = {}
        doc.original_filename = "test.pdf"
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(renderer, "_resolve_template_path_with_flag", side_effect=Exception("resolve error")),
        ):
            with pytest.raises(Exception, match="resolve error"):
                renderer.render(document=doc)

    def test_render_raises_on_build_context_failure(self, renderer):
        doc = MagicMock(spec=PipelineDocument)
        doc.metadata = DocumentMetadata()
        doc.blocks = []
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(renderer, "_resolve_template_path_with_flag", return_value=(Path("dummy.docx"), False)),
            patch.object(renderer, "build_context", side_effect=ValueError("ctx fail")),
        ):
            with pytest.raises(ValueError, match="ctx fail"):
                renderer.render(document=doc)


# ══════════════════════════════════════════════════════════════════════════════
# has_renderable_template — edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestHasRenderableTemplateGaps:
    def test_none_template_name(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        (style_dir / "template.jinja2").write_text("{{ title }}")
        assert renderer.has_renderable_template(None) is True

    def test_no_dir_returns_false(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path / "nonexistent"
        assert renderer.has_renderable_template("ieee") is False

    def test_docx_exists_without_markers_no_jinja(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        docx_path = style_dir / "template.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>No markers</w:document>")
        assert renderer.has_renderable_template("ieee") is False

    def test_jinja_source_overrides_docx(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        (style_dir / "template.jinja2").write_text("{{ title }}")
        docx_path = style_dir / "template.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>{{ title }}</w:document>")
        assert renderer.has_renderable_template("ieee") is True


# ══════════════════════════════════════════════════════════════════════════════
# build_context — more edge paths
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildContextGaps:
    def test_abstract_from_metadata_empty_string(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(abstract=""), blocks=[_make_block("b1", 0, "abstract_body", "Block abstract")]
        )
        ctx = renderer.build_context(doc)
        assert ctx["abstract"] == "Block abstract"

    def test_keywords_raw_split_with_spaces(self, renderer):
        doc = _make_doc(
            metadata=DocumentMetadata(keywords=[]),
            blocks=[_make_block("b1", 0, "keywords_body", "  kw1  ,  kw2  ,  kw3  ")],
        )
        ctx = renderer.build_context(doc)
        assert ctx["keywords"] == ["kw1", "kw2", "kw3"]

    def test_title_fallback_chain_all_empty(self, renderer):
        doc = _make_doc(metadata=DocumentMetadata(title=""), blocks=[], original_filename=None)
        ctx = renderer.build_context(doc)
        assert ctx["title"] == "Untitled Manuscript"

    def test_cover_page_add_cover_page_key(self, renderer):
        doc = _make_doc(formatting_options={"add_cover_page": False})
        ctx = renderer.build_context(doc)
        assert ctx["cover_page"] is False

    def test_toc_generate_toc_key(self, renderer):
        doc = _make_doc(formatting_options={"generate_toc": True})
        ctx = renderer.build_context(doc)
        assert ctx["toc"] is True

    def test_page_numbers_add_page_numbers_key(self, renderer):
        doc = _make_doc(formatting_options={"add_page_numbers": False})
        ctx = renderer.build_context(doc)
        assert ctx["page_numbers"] is False

    def test_page_number_default(self, renderer):
        doc = _make_doc(formatting_options={})
        ctx = renderer.build_context(doc)
        assert ctx["page_number"] == "1"

    def test_references_sorted_by_index(self, renderer):
        refs = [
            _make_ref("r2", 2, formatted_text="Ref B"),
            _make_ref("r1", 1, formatted_text="Ref A"),
        ]
        doc = _make_doc(references=refs)
        ctx = renderer.build_context(doc)
        assert ctx["references"] == ["Ref A", "Ref B"]

    def test_references_all_empty_falls_to_blocks(self, renderer):
        refs = [
            _make_ref("r1", 1, formatted_text="", raw_text=""),
            _make_ref("r2", 2, formatted_text=None, raw_text=""),
        ]
        blocks = [
            _make_block("b1", 0, "reference_entry", "[1] Block Ref"),
        ]
        doc = _make_doc(references=refs, blocks=blocks)
        ctx = renderer.build_context(doc)
        assert ctx["references"] == ["[1] Block Ref"]

    def test_no_blocks_and_no_references(self, renderer):
        doc = _make_doc(references=[], blocks=[])
        ctx = renderer.build_context(doc)
        assert ctx["references"] == []

    def test_exception_building_context(self, renderer):
        doc = _make_doc()
        doc.blocks = _make_block("b1", 0, "abstract_body", "text")
        with patch("app.pipeline.formatting.template_renderer.sorted", side_effect=Exception("sort fail")):
            with pytest.raises(Exception, match="sort fail"):
                renderer.build_context(doc)


# ══════════════════════════════════════════════════════════════════════════════
# _resolve_template_path — edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestResolveTemplatePathGaps:
    def test_style_dir_does_not_exist(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        fake = tmp_path / "fallback.docx"
        with patch.object(renderer, "_build_fallback_template", return_value=fake):
            result = renderer._resolve_template_path("ieee")
        assert result == fake

    def test_jinja_source_build_failure_falls_back(self, renderer, tmp_path):
        renderer.templates_dir = tmp_path
        style_dir = tmp_path / "ieee"
        style_dir.mkdir()
        jinja = style_dir / "template.jinja2"
        jinja.write_text("{{ title }}")
        fake = tmp_path / "fallback.docx"
        with (
            patch.object(renderer, "_build_template_from_jinja_source", side_effect=Exception("build fail")),
            patch.object(renderer, "_build_fallback_template", return_value=fake),
        ):
            result = renderer._resolve_template_path("ieee")
        assert result == fake


# ══════════════════════════════════════════════════════════════════════════════
# _has_template_markers — additional edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestHasTemplateMarkersGaps:
    def test_zip_read_exception_returns_false(self, renderer):
        fake = Path("/nonexistent/missing.docx")
        assert renderer._has_template_markers(fake) is False

    def test_cache_hit_true(self, renderer, tmp_path):
        docx_path = tmp_path / "cached_true.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>{{ title }}</w:document>")
        renderer._template_marker_cache[docx_path] = True
        assert renderer._has_template_markers(docx_path) is True

    def test_cache_hit_false(self, renderer, tmp_path):
        docx_path = tmp_path / "cached_false.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:document>No markers</w:document>")
        renderer._template_marker_cache[docx_path] = False
        assert renderer._has_template_markers(docx_path) is False

    def test_no_word_xml_entries(self, renderer, tmp_path):
        docx_path = tmp_path / "no_word.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("docProps/app.xml", "{{ title }}")
        assert renderer._has_template_markers(docx_path) is False

    def test_markers_in_text_after_strip_only(self, renderer, tmp_path):
        docx_path = tmp_path / "markers_in_text.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:p><w:r><w:t>{{ title }}</w:t></w:r></w:p>")
        assert renderer._has_template_markers(docx_path) is True

    def test_block_markers_in_stripped_text(self, renderer, tmp_path):
        docx_path = tmp_path / "block_markers.docx"
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", "<w:p><w:r><w:t>{% for item in items %}</w:t></w:r></w:p>")
        assert renderer._has_template_markers(docx_path) is True


# ══════════════════════════════════════════════════════════════════════════════
# _build_fallback_template — error path
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildFallbackTemplateGaps:
    def test_name_error_during_save_raises(self, renderer):
        with (
            patch("app.pipeline.formatting.template_renderer.tempfile.NamedTemporaryFile") as mock_ntf,
            patch("app.pipeline.formatting.template_renderer.WordDocument") as mock_wd_cls,
        ):
            mock_file = MagicMock()
            mock_file.name = "/tmp/fallback.docx"
            mock_ntf.return_value.__enter__.return_value = mock_file
            mock_doc = MagicMock()
            mock_doc.save.side_effect = Exception("save failed")
            mock_wd_cls.return_value = mock_doc
            with pytest.raises(Exception, match="save failed"):
                renderer._build_fallback_template()


# ══════════════════════════════════════════════════════════════════════════════
# _collect_sections — edge: footnote/endnote in metadata, footnote/endnote as bool check
# ══════════════════════════════════════════════════════════════════════════════


class TestCollectSectionsGaps:
    def test_metadata_none_is_footnote(self, renderer):
        blocks = [
            _make_block("b1", 0, "heading_1", "Intro"),
            _make_block("b2", 1, "body", "note"),
        ]
        sections = renderer._collect_sections(blocks)
        # metadata is None so `block.metadata or {}` yields {} → get returns None → bool(None) is False → not filtered
        assert len(sections) == 1
        assert "note" in sections[0]["paragraphs"]

    def test_consecutive_headings_all_skipped_until_body(self, renderer):
        blocks = [
            _make_block("b1", 0, "heading_1", "Intro"),
            _make_block("b2", 1, "heading_1", "Background"),
            _make_block("b3", 2, "heading_1", "Methods"),
            _make_block("b4", 3, "body", "First real content"),
        ]
        sections = renderer._collect_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Methods"
        assert sections[0]["paragraphs"] == ["First real content"]

    def test_all_skipped_types_no_content(self, renderer):
        blocks = [
            _make_block("b1", 0, "title", "Title"),
            _make_block("b2", 1, "author", "Author"),
            _make_block("b3", 2, "affiliation", "Affil"),
        ]
        sections = renderer._collect_sections(blocks)
        assert sections == []

    def test_only_heading_no_body(self, renderer):
        blocks = [
            _make_block("b1", 0, "heading_1", "Intro"),
        ]
        sections = renderer._collect_sections(blocks)
        assert sections == []


# ══════════════════════════════════════════════════════════════════════════════
# _collect_references — additional edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestCollectReferencesGaps:
    def test_no_references_empty_blocks(self, renderer):
        doc = _make_doc(references=[], blocks=[])
        assert renderer._collect_references(doc) == []

    def test_uses_formatted_text_over_raw(self, renderer):
        refs = [_make_ref("r1", 1, formatted_text="Formatted", raw_text="Raw")]
        doc = _make_doc(references=refs)
        assert renderer._collect_references(doc) == ["Formatted"]

    def test_fallback_blocks_empty_text_skipped(self, renderer):
        blocks = [
            _make_block("b1", 0, "reference_entry", ""),
            _make_block("b2", 1, "reference_entry", "[1] Real"),
            _make_block("b3", 2, "reference_entry", "   "),
        ]
        doc = _make_doc(references=[], blocks=blocks)
        assert renderer._collect_references(doc) == ["[1] Real"]


# ══════════════════════════════════════════════════════════════════════════════
# _block_type_token — remaining edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestBlockTypeTokenGaps:
    def test_enum_value(self, renderer):
        block = MagicMock()
        block.block_type = BlockType.ABSTRACT_BODY
        assert renderer._block_type_token(block) == "abstract_body"

    def test_string_value(self, renderer):
        block = MagicMock()
        block.block_type = "ABSTRACT_BODY"
        assert renderer._block_type_token(block) == "abstract_body"

    def test_block_type_not_present(self, renderer):
        block = MagicMock(spec=[])
        del block.block_type
        assert renderer._block_type_token(block) == ""

    def test_case_insensitive_strip(self, renderer):
        block = MagicMock()
        block.block_type = "  Heading_1  "
        assert renderer._block_type_token(block) == "heading_1"
