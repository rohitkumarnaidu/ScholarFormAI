# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock, ANY, call
from pathlib import Path
import pytest

# ══════════════════════════════════════════════════════════════════════════════
# formatting/template_renderer.py — MAJOR GAP (~0% coverage on main methods)
# ══════════════════════════════════════════════════════════════════════════════

class TestTemplateRendererInit:
    def test_init_defaults(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        assert str(tr.templates_dir).replace("\\", "/").endswith("app/templates")

    def test_init_custom_dir(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir="/tmp/custom")
        assert "tmp" in str(tr.templates_dir).replace("\\", "/")
        assert "custom" in str(tr.templates_dir).replace("\\", "/")

class TestTemplateRendererCoerceBool:
    def test_int_float_values(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(1, False) is True
        assert TemplateRenderer._coerce_bool(0, True) is False
        assert TemplateRenderer._coerce_bool(3.14, False) is True
        assert TemplateRenderer._coerce_bool(0.0, True) is False

    def test_unknown_string(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool("maybe", False) is True

    def test_off_values(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool("off", True) is False

    def test_empty_string_false(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool("", True) is False

class TestTemplateRendererResolveBoolOption:
    def test_resolve_first_key(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        assert tr._resolve_bool_option({"key_a": True, "key_b": False}, ["key_a", "key_b"], False) is True

    def test_resolve_second_key(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        assert tr._resolve_bool_option({"key_b": True}, ["key_a", "key_b"], False) is True

    def test_resolve_default(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        assert tr._resolve_bool_option({}, ["key_a"], True) is True

class TestTemplateRendererRender:
    def test_render_success(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.formatting_options = {}
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch("app.pipeline.formatting.template_renderer.DocxTemplate") as mock_dt,
            patch.object(tr, "_resolve_template_path", return_value=Path("/tmp/test.docx")),
            patch.object(tr, "build_context", return_value={"title": "Test"}),
        ):
            mock_tpl = MagicMock()
            mock_dt.return_value = mock_tpl
            result = tr.render(doc, "ieee")
            assert result is mock_tpl
            mock_tpl.render.assert_called_once_with({"title": "Test"})

    def test_render_no_docxtpl(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", False),
        ):
            with pytest.raises(ImportError):
                tr.render(MagicMock(), "ieee")

    def test_render_none_document(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
        ):
            with pytest.raises(ValueError):
                tr.render(None, "ieee")

    def test_render_error_logged(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.formatting_options = {}
        with (
            patch("app.pipeline.formatting.template_renderer._DOCXTPL_AVAILABLE", True),
            patch.object(tr, "_resolve_template_path", side_effect=OSError("no such file")),
            patch("app.pipeline.formatting.template_renderer.logger") as mock_log,
        ):
            with pytest.raises(OSError):
                tr.render(doc, "ieee")
            mock_log.error.assert_called()

class TestTemplateRendererHasRenderable:
    def test_jinja2_source_exists(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        mock_dir = MagicMock()
        mock_dir.__truediv__.return_value.__truediv__.return_value.is_file.return_value = True
        tr.templates_dir = mock_dir
        assert tr.has_renderable_template("ieee") is True

    def test_docx_with_markers(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        mock_dir = MagicMock()
        tr.templates_dir = mock_dir
        jinja_check = MagicMock()
        jinja_check.is_file.return_value = False
        docx_check = MagicMock()
        docx_check.is_file.return_value = True
        mock_dir.__truediv__.return_value.__truediv__.side_effect = [jinja_check, docx_check]
        with patch.object(tr, "_has_template_markers", return_value=True):
            assert tr.has_renderable_template("ieee") is True

    def test_docx_no_markers(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        mock_dir = MagicMock()
        tr.templates_dir = mock_dir
        jinja_check = MagicMock()
        jinja_check.is_file.return_value = False
        docx_check = MagicMock()
        docx_check.is_file.return_value = True
        mock_dir.__truediv__.return_value.__truediv__.side_effect = [jinja_check, docx_check]
        with patch.object(tr, "_has_template_markers", return_value=False):
            assert tr.has_renderable_template("ieee") is False

    def test_no_template_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        tr.templates_dir = MagicMock()
        tr.templates_dir.__truediv__.return_value.__truediv__.return_value.is_file.return_value = False
        assert tr.has_renderable_template("unknown") is False

class TestTemplateRendererBuildContext:
    def test_full_metadata(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.blocks = []
        doc.metadata.title = "Full Title"
        doc.metadata.authors = ["Alice", "Bob"]
        doc.metadata.affiliations = ["Univ A"]
        doc.metadata.abstract = "Abstract text"
        doc.metadata.keywords = ["kw1", "kw2"]
        doc.formatting_options = {}
        doc.original_filename = ""
        with patch.object(tr, "_collect_references", return_value=["[1] Ref"]):
            with patch.object(tr, "_collect_sections", return_value=[{"heading": "Intro", "paragraphs": ["Body"]}]):
                ctx = tr.build_context(doc)
        assert ctx["title"] == "Full Title"
        assert ctx["authors"] == ["Alice", "Bob"]
        assert ctx["affiliations"] == ["Univ A"]
        assert ctx["abstract"] == "Abstract text"
        assert ctx["keywords"] == ["kw1", "kw2"]
        assert ctx["cover_page"] is True
        assert ctx["toc"] is False
        assert ctx["page_numbers"] is True

    def test_metadata_falls_back_to_blocks(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.metadata.title = ""
        doc.metadata.authors = []
        doc.metadata.affiliations = []
        doc.metadata.abstract = ""
        doc.metadata.keywords = []
        doc.original_filename = "my_paper.docx"
        doc.formatting_options = {}
        b1 = MagicMock(); b1.text = "Fallback Title"; b1.index = 0
        b2 = MagicMock(); b2.text = "Alice"; b2.index = 1
        b3 = MagicMock(); b3.text = "Univ B"; b3.index = 2
        b4 = MagicMock(); b4.text = "abstract body text"; b4.index = 3
        b5 = MagicMock(); b5.text = "kw1, kw2"; b5.index = 4
        doc.blocks = [b1, b2, b3, b4, b5]
        with patch.object(tr, "_first_block_text") as mock_fbt:
            mock_fbt.side_effect = ["abstract body text", "", "Fallback Title"]
            with patch.object(tr, "_all_block_text") as mock_abt:
                mock_abt.side_effect = [["Alice"], ["Univ B"]]
                with patch.object(tr, "_collect_references", return_value=[]):
                    with patch.object(tr, "_collect_sections", return_value=[]):
                        with patch.object(tr, "_resolve_bool_option", return_value=True):
                            ctx = tr.build_context(doc)
        assert ctx["title"] == "Fallback Title"
        assert "Alice" in ctx["authors"]
        assert ctx["abstract"] == "abstract body text"

    def test_keywords_from_block_csv(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.metadata.title = "Title"
        doc.metadata.authors = ["A"]
        doc.metadata.affiliations = []
        doc.metadata.abstract = ""
        doc.metadata.keywords = []
        doc.formatting_options = {}
        doc.original_filename = ""
        b = MagicMock(); b.text = "machine learning, nlp, ai"; b.index = 0
        doc.blocks = [b]
        with patch.object(tr, "_first_block_text", side_effect=["", "machine learning, nlp, ai"]):
            with patch.object(tr, "_all_block_text", return_value=["A"]):
                with patch.object(tr, "_collect_references", return_value=[]):
                    with patch.object(tr, "_collect_sections", return_value=[]):
                        ctx = tr.build_context(doc)
        assert ctx["keywords"] == ["machine learning", "nlp", "ai"]

    def test_untitled_uses_filename(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.metadata.title = ""
        doc.metadata.authors = []
        doc.metadata.affiliations = []
        doc.metadata.abstract = ""
        doc.metadata.keywords = []
        doc.formatting_options = {}
        doc.original_filename = "manuscript.docx"
        doc.blocks = []
        with patch.object(tr, "_first_block_text", return_value=""):
            with patch.object(tr, "_all_block_text", return_value=[]):
                with patch.object(tr, "_collect_references", return_value=[]):
                    with patch.object(tr, "_collect_sections", return_value=[]):
                        ctx = tr.build_context(doc)
        assert ctx["title"] == "manuscript.docx"

    def test_error_raises(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.metadata = MagicMock()
        doc.metadata.title = ""
        doc.metadata.authors = []
        doc.metadata.affiliations = []
        doc.metadata.abstract = ""
        doc.metadata.keywords = []
        doc.formatting_options = {}
        doc.original_filename = ""
        doc.blocks = []
        with patch.object(tr, "_collect_references", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                tr.build_context(doc)

class TestTemplateRendererResolveTemplatePath:
    def test_jinja_source_path(self, tmp_path):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=str(tmp_path))
        ieee_dir = tmp_path / "ieee"
        ieee_dir.mkdir()
        (ieee_dir / "template.jinja2").write_text("{{ title }}")
        expected = Path("/tmp/built.docx")
        with patch.object(tr, "_build_template_from_jinja_source", return_value=expected):
            result = tr._resolve_template_path("ieee")
            assert result.name == expected.name

    def test_jinja_source_fails_then_docx(self, tmp_path):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=str(tmp_path))
        ieee_dir = tmp_path / "ieee"
        ieee_dir.mkdir()
        (ieee_dir / "template.jinja2").write_text("{{ title }}")
        (ieee_dir / "template.docx").write_bytes(b"PK")
        with patch.object(tr, "_build_template_from_jinja_source", side_effect=Exception("build failed")):
            with patch.object(tr, "_has_template_markers", return_value=True):
                result = tr._resolve_template_path("ieee")
                assert str(result).endswith(".docx")

    def test_docx_no_markers_fallback(self, tmp_path):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=str(tmp_path))
        ieee_dir = tmp_path / "ieee"
        ieee_dir.mkdir()
        (ieee_dir / "template.docx").write_bytes(b"PK")
        expected = Path("/tmp/fallback.docx")
        with patch.object(tr, "_has_template_markers", return_value=False):
            with patch.object(tr, "_build_fallback_template", return_value=expected):
                result = tr._resolve_template_path("ieee")
                assert result.name == expected.name

    def test_no_files_fallback(self, tmp_path):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=str(tmp_path))
        expected = Path("/tmp/fallback.docx")
        with patch.object(tr, "_build_fallback_template", return_value=expected):
            result = tr._resolve_template_path("ieee")
            assert result.name == expected.name

class TestTemplateRendererBuildFromJinja:
    def test_build_success(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        source = MagicMock()
        source.read_text.return_value = "{{ title }}\n{{ author }}"
        with (
            patch("app.pipeline.formatting.template_renderer.WordDocument") as mock_wd,
            patch("tempfile.NamedTemporaryFile") as mock_tmp,
        ):
            mock_tmp.return_value.__enter__.return_value.name = "/tmp/tmpXXXX.docx"
            mock_doc = MagicMock()
            mock_wd.return_value = mock_doc
            result = tr._build_template_from_jinja_source(source)
            assert "tmpXXXX" in result.name
            mock_doc.add_paragraph.assert_any_call("{{ title }}")
            mock_doc.add_paragraph.assert_any_call("{{ author }}")

    def test_build_fallback_on_error(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        source = MagicMock()
        source.read_text.side_effect = PermissionError("denied")
        with (
            patch.object(tr, "_build_fallback_template", return_value=Path("/tmp/fallback.docx")),
        ):
            result = tr._build_template_from_jinja_source(source)
            assert result == Path("/tmp/fallback.docx")

class TestTemplateRendererHasTemplateMarkers:
    def test_markers_in_xml(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        p = Path("/fake/test.docx")
        with (
            patch("app.pipeline.formatting.template_renderer.ZipFile") as mock_zf,
        ):
            mock_zf.return_value.__enter__.return_value.namelist.return_value = ["word/document.xml"]
            mock_zf.return_value.__enter__.return_value.read.return_value = b'<w:p>{{ title }}</w:p>'
            assert tr._has_template_markers(p) is True

    def test_markers_in_stripped_text(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        p = Path("/fake/test.docx")
        with (
            patch("app.pipeline.formatting.template_renderer.ZipFile") as mock_zf,
        ):
            mock_zf.return_value.__enter__.return_value.namelist.return_value = ["word/document.xml"]
            xml = b'<w:p><w:r><w:t>{% if cover_page %}</w:t></w:r></w:p>'
            mock_zf.return_value.__enter__.return_value.read.return_value = xml
            assert tr._has_template_markers(p) is True

    def test_no_markers(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        p = Path("/fake/test.docx")
        with (
            patch("app.pipeline.formatting.template_renderer.ZipFile") as mock_zf,
        ):
            mock_zf.return_value.__enter__.return_value.namelist.return_value = ["word/document.xml"]
            mock_zf.return_value.__enter__.return_value.read.return_value = b'<w:p>Just text</w:p>'
            assert tr._has_template_markers(p) is False

    def test_zip_error_false(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        p = Path("/fake/bad.docx")
        with (
            patch("app.pipeline.formatting.template_renderer.ZipFile", side_effect=Exception("corrupt")),
            patch("app.pipeline.formatting.template_renderer.logger"),
        ):
            assert tr._has_template_markers(p) is False

class TestTemplateRendererBuildFallback:
    def test_fallback_creates_docx(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        with (
            patch("app.pipeline.formatting.template_renderer.WordDocument") as mock_wd,
            patch("tempfile.NamedTemporaryFile") as mock_tmp,
        ):
            mock_tmp.return_value.__enter__.return_value.name = "/tmp/fallbackXXXX.docx"
            mock_doc = MagicMock()
            mock_wd.return_value = mock_doc
            result = tr._build_fallback_template()
            assert ".docx" in result.suffix
            mock_doc.add_paragraph.assert_any_call("{{ title }}", style="Title")
            mock_doc.save.assert_called_once()

    def test_fallback_error_raises(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        with (
            patch("app.pipeline.formatting.template_renderer.WordDocument", side_effect=MemoryError("oom")),
        ):
            with pytest.raises(MemoryError):
                tr._build_fallback_template()

class TestTemplateRendererCollectReferences:
    def test_from_document_references(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        ref1 = MagicMock(); ref1.index = 1; ref1.formatted_text = "[1] Ref A"; ref1.raw_text = ""
        ref2 = MagicMock(); ref2.index = 2; ref2.formatted_text = ""; ref2.raw_text = "[2] Ref B"
        doc.references = [ref1, ref2]
        doc.blocks = []
        result = tr._collect_references(doc)
        assert "[1] Ref A" in result
        assert "[2] Ref B" in result

    def test_falls_back_to_blocks(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.references = []
        b1 = MagicMock(); b1.text = "[1] Ref A"; b1.index = 1
        b2 = MagicMock(); b2.text = ""; b2.index = 2
        b3 = MagicMock(); b3.text = "[2] Ref B"; b3.index = 3
        b1.block_type = "REFERENCE_ENTRY"; b2.block_type = "BODY"; b3.block_type = "REFERENCE_ENTRY"
        doc.blocks = [b1, b2, b3]
        result = tr._collect_references(doc)
        assert "[1] Ref A" in result
        assert "[2] Ref B" in result

    def test_no_references(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.references = []
        doc.blocks = []
        result = tr._collect_references(doc)
        assert result == []

class TestTemplateRendererCollectSections:
    def test_basic_sections(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        b1 = MagicMock(); b1.text = "Introduction"; b1.index = 1; b1.metadata = {}
        b1.block_type = "HEADING_1"
        b2 = MagicMock(); b2.text = "Body text"; b2.index = 2; b2.metadata = {}
        b2.block_type = "BODY"
        blocks = [b1, b2]
        result = tr._collect_sections(blocks)
        assert len(result) >= 1

    def test_skips_special_types(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        blocks = []
        for bt in ["title", "author", "affiliation", "abstract_heading", "abstract_body",
                     "keywords_heading", "keywords_body", "references_heading", "reference_entry",
                     "figure_caption", "table_caption", "footnote", "endnote"]:
            b = MagicMock(); b.text = "skip"; b.index = len(blocks); b.metadata = {}
            b.block_type = bt.upper()
            blocks.append(b)
        b_ok = MagicMock(); b_ok.text = "Real content"; b_ok.index = 99; b_ok.metadata = {}
        b_ok.block_type = "BODY"
        blocks.append(b_ok)
        result = tr._collect_sections(blocks)
        assert len(result) >= 1

    def test_empty_text_skipped(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        b = MagicMock(); b.text = ""; b.index = 0; b.metadata = {}
        b.block_type = "BODY"
        result = tr._collect_sections([b])
        assert len(result) == 0

    def test_metadata_footnote_skipped(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        b = MagicMock(); b.text = "note"; b.index = 0; b.metadata = {"is_footnote": True}
        b.block_type = "BODY"
        result = tr._collect_sections([b])
        assert len(result) == 0

class TestTemplateRendererBlockHelpers:
    def test_first_block_text_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        b1 = MagicMock(); b1.text = "Title Here"; b1.index = 0
        b1.block_type = "TITLE"
        b2 = MagicMock(); b2.text = ""; b2.index = 1
        b2.block_type = "TITLE"
        assert tr._first_block_text([b1, b2], "title") == "Title Here"

    def test_all_block_text_multiple(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        b1 = MagicMock(); b1.text = "Alice"; b1.index = 0
        b1.block_type = "AUTHOR"
        b2 = MagicMock(); b2.text = "Bob"; b2.index = 1
        b2.block_type = "AUTHOR"
        b3 = MagicMock(); b3.text = ""; b3.index = 2
        b3.block_type = "AUTHOR"
        assert tr._all_block_text([b1, b2, b3], "author") == ["Alice", "Bob"]

    def test_block_type_token_with_enum_value(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        mock_block = MagicMock()
        mock_block.block_type = MagicMock()
        mock_block.block_type.value = "TITLE"
        result = TemplateRenderer._block_type_token(mock_block)
        assert result == "title"


# ══════════════════════════════════════════════════════════════════════════════
# formatting/reference_formatter.py — citeproc integration & CSL gaps
# ══════════════════════════════════════════════════════════════════════════════

class TestReferenceTypeToCsl:
    def test_all_mappings(self):
        from app.pipeline.formatting.reference_formatter import _reference_type_to_csl
        ref = MagicMock()
        for rt, expected in [
            ("journal_article", "article-journal"),
            ("conference_paper", "paper-conference"),
            ("book", "book"),
            ("book_chapter", "chapter"),
            ("thesis", "thesis"),
            ("technical_report", "report"),
            ("patent", "patent"),
            ("web_page", "webpage"),
            ("preprint", "article"),
        ]:
            ref.reference_type = rt
            assert _reference_type_to_csl(ref) == expected

    def test_unknown_type_defaults_to_article(self):
        from app.pipeline.formatting.reference_formatter import _reference_type_to_csl
        ref = MagicMock()
        ref.reference_type = "unknown_type"
        assert _reference_type_to_csl(ref) == "article"

class TestReferenceToCslJson:
    def test_full_reference(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json
        ref = MagicMock()
        ref.reference_id = "ref1"
        ref.reference_type = "journal_article"
        ref.authors = ["Smith, J.", "Doe, A."]
        ref.title = "Test Title"
        ref.journal = "Test Journal"
        ref.publisher = "Test Publisher"
        ref.year = 2024
        ref.volume = "10"
        ref.issue = "2"
        ref.pages = "100-120"
        ref.doi = "10.1234/test"
        ref.isbn = "978-3-16-148410-0"
        ref.issn = "1234-5678"
        ref.url = "https://example.com"
        ref.edition = "2"
        ref.note = "A note"
        result = _reference_to_csl_json(ref)
        assert result["id"] == "ref1"
        assert result["type"] == "article-journal"
        assert result["author"] == [{"family": "Smith", "given": "J."}, {"family": "Doe", "given": "A."}]
        assert result["title"] == "Test Title"
        assert result["container-title"] == "Test Journal"
        assert result["publisher"] == "Test Publisher"
        assert result["issued"] == {"date-parts": [[2024]]}
        assert result["volume"] == "10"
        assert result["issue"] == "2"
        assert result["page"] == "100-120"
        assert result["DOI"] == "10.1234/test"
        assert result["ISBN"] == "978-3-16-148410-0"
        assert result["ISSN"] == "1234-5678"
        assert result["URL"] == "https://example.com"
        assert result["edition"] == "2"
        assert result["note"] == "A note"

    def test_minimal_reference(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json
        ref = MagicMock()
        ref.reference_id = "ref1"
        ref.reference_type = "unknown"
        ref.authors = []
        ref.title = ""
        ref.journal = ""
        ref.conference = ""
        ref.book_title = ""
        ref.publisher = ""
        ref.year = None
        ref.volume = ""
        ref.issue = ""
        ref.pages = ""
        ref.doi = ""
        ref.isbn = ""
        ref.issn = ""
        ref.url = ""
        ref.edition = ""
        ref.note = ""
        result = _reference_to_csl_json(ref)
        assert result["id"] == "ref1"
        assert result["type"] == "article"
        assert "author" not in result

    def test_uses_conference_fallback(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json
        ref = MagicMock()
        ref.reference_id = "r1"
        ref.reference_type = "conference_paper"
        ref.journal = ""
        ref.conference = "Test Conference"
        ref.book_title = ""
        ref.authors = ["Author"]
        ref.title = "Paper"
        result = _reference_to_csl_json(ref)
        assert result["container-title"] == "Test Conference"

    def test_uses_book_title_fallback(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json
        ref = MagicMock()
        ref.reference_id = "r1"
        ref.reference_type = "book_chapter"
        ref.journal = ""
        ref.conference = ""
        ref.book_title = "Book Title"
        ref.authors = ["Author"]
        ref.title = "Chapter"
        result = _reference_to_csl_json(ref)
        assert result["container-title"] == "Book Title"

class TestResolveCslPath:
    def test_path_found(self):
        with (
            patch("app.pipeline.formatting.reference_formatter.os.path.isfile", return_value=True),
            patch("app.pipeline.formatting.reference_formatter.os.path.normpath", return_value="/tmp/ieee/styles.csl"),
        ):
            from app.pipeline.formatting.reference_formatter import _resolve_csl_path
            result = _resolve_csl_path("IEEE")
            assert result is not None

    def test_path_not_found(self):
        with (
            patch("app.pipeline.formatting.reference_formatter.os.path.isfile", return_value=False),
        ):
            from app.pipeline.formatting.reference_formatter import _resolve_csl_path
            assert _resolve_csl_path("ieee") is None

    def test_whitespace_strip(self):
        with (
            patch("app.pipeline.formatting.reference_formatter.os.path.isfile", return_value=False),
        ):
            from app.pipeline.formatting.reference_formatter import _resolve_csl_path
            result = _resolve_csl_path("  IEEE  ")
            assert result is None

class TestReferenceFormatterCiteproc:
    def test_format_with_citeproc_success(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        ref = MagicMock()
        ref.reference_id = "r1"
        ref.reference_type = "journal_article"
        ref.authors = ["Smith, J."]
        ref.title = "Test"
        with (
            patch("app.pipeline.formatting.reference_formatter._resolve_csl_path", return_value="/tmp/ieee/styles.csl"),
            patch.object(rf, "_get_or_load_style", return_value=MagicMock()),
            patch("app.pipeline.formatting.reference_formatter.CiteProcJSON") as mock_cpj,
            patch("app.pipeline.formatting.reference_formatter.CitationStylesBibliography") as mock_csb,
            patch("app.pipeline.formatting.reference_formatter.Citation") as mock_cit,
            patch("app.pipeline.formatting.reference_formatter.CitationItem") as mock_ci,
        ):
            mock_bib = MagicMock()
            mock_bib.bibliography.return_value = ["[1] Smith, J., Test, 2024."]
            mock_csb.return_value = mock_bib
            result = rf._format_with_citeproc(ref, "ieee")
            assert result == "[1] Smith, J., Test, 2024."

    def test_format_with_citeproc_no_csl_path(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        ref = MagicMock()
        ref.reference_id = "r1"
        with patch("app.pipeline.formatting.reference_formatter._resolve_csl_path", return_value=None):
            assert rf._format_with_citeproc(ref, "ieee") is None

    def test_format_with_citeproc_style_is_none(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        ref = MagicMock()
        ref.reference_id = "r1"
        with (
            patch("app.pipeline.formatting.reference_formatter._resolve_csl_path", return_value="/tmp/s.csl"),
            patch.object(rf, "_get_or_load_style", return_value=None),
        ):
            assert rf._format_with_citeproc(ref, "ieee") is None

    def test_format_with_citeproc_empty_bibliography(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        ref = MagicMock()
        ref.reference_id = "r1"
        with (
            patch("app.pipeline.formatting.reference_formatter._resolve_csl_path", return_value="/tmp/s.csl"),
            patch.object(rf, "_get_or_load_style", return_value=MagicMock()),
            patch("app.pipeline.formatting.reference_formatter.CiteProcJSON"),
            patch("app.pipeline.formatting.reference_formatter.CitationStylesBibliography") as mock_csb,
            patch("app.pipeline.formatting.reference_formatter.Citation"),
        ):
            mock_bib = MagicMock()
            mock_bib.bibliography.return_value = []
            mock_csb.return_value = mock_bib
            assert rf._format_with_citeproc(ref, "ieee") is None

    def test_format_reference_citeproc_called_when_available(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        ref = MagicMock()
        ref.reference_id = "r1"
        ref.authors = []
        ref.title = ""
        ref.journal = ""
        ref.conference = ""
        ref.year = ""
        ref.number = 1
        ref.raw_text = "raw"
        with (
            patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", True),
            patch.object(rf, "_format_with_citeproc", return_value="[1] Formatted"),
            patch.object(rf, "_format_legacy", return_value="[1] Legacy"),
        ):
            result = rf.format_reference(ref, "ieee")
            assert result == "[1] Formatted"

    def test_format_reference_citeproc_fallback_on_error(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        ref = MagicMock()
        ref.reference_id = "r1"
        ref.authors = []
        ref.title = ""
        ref.journal = ""
        ref.conference = ""
        ref.year = ""
        ref.number = 1
        ref.raw_text = "raw"
        with (
            patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", True),
            patch.object(rf, "_format_with_citeproc", side_effect=Exception("citeproc error")),
            patch.object(rf, "_format_legacy", return_value="[1] Legacy"),
        ):
            result = rf.format_reference(ref, "ieee")
            assert result == "[1] Legacy"

    def test_get_or_load_style_miss(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        with (
            patch("app.pipeline.formatting.reference_formatter.CitationStylesStyle") as mock_css,
        ):
            mock_style = MagicMock()
            mock_css.return_value = mock_style
            with patch("app.pipeline.formatting.reference_formatter.logger"):
                result = rf._get_or_load_style("/tmp/test.csl")
            assert result is mock_style
            assert "/tmp/test.csl" in rf._style_cache

    def test_get_or_load_style_load_error(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        with (
            patch("app.pipeline.formatting.reference_formatter.CitationStylesStyle", side_effect=Exception("bad csl")),
        ):
            with patch("app.pipeline.formatting.reference_formatter.logger"):
                result = rf._get_or_load_style("/tmp/bad.csl")
            assert result is None
            assert rf._style_cache["/tmp/bad.csl"] is None

    def test_cached_style_returned(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        mock_style = MagicMock()
        rf._style_cache["/tmp/cached.csl"] = mock_style
        with patch("app.pipeline.formatting.reference_formatter.CitationStylesStyle") as mock_css:
            result = rf._get_or_load_style("/tmp/cached.csl")
            assert result is mock_style
            mock_css.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# formatting/numbering.py — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestNumberingEngineEdgeCases:
    def test_multi_level_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {}}
        h1 = MagicMock(); h1.is_heading.return_value = True; h1.level = 1; h1.text = "Intro"; h1.metadata = {}
        h2 = MagicMock(); h2.is_heading.return_value = True; h2.level = 2; h2.text = "Background"; h2.metadata = {}
        h3 = MagicMock(); h3.is_heading.return_value = True; h3.level = 3; h3.text = "Details"; h3.metadata = {}
        doc = MagicMock()
        doc.blocks = [h1, h2, h3]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert h1.metadata["number_string"] == "1"
        assert h2.metadata["number_string"] == "1.1"
        assert h3.metadata["number_string"] == "1.1.1"

    def test_level_reset_on_deeper_heading(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {}}
        h1 = MagicMock(); h1.is_heading.return_value = True; h1.level = 1; h1.text = "1. Intro"; h1.metadata = {}
        h2 = MagicMock(); h2.is_heading.return_value = True; h2.level = 1; h2.text = "Methods"; h2.metadata = {}
        doc = MagicMock()
        doc.blocks = [h1, h2]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert h1.metadata["number_string"] == "1"
        assert h1.text.startswith("1 ")
        assert h2.metadata["number_string"] == "2"
        assert h2.text.startswith("2 ")

    def test_level_4_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {}}
        h4 = MagicMock(); h4.is_heading.return_value = True; h4.level = 4; h4.text = "Details"; h4.metadata = {}
        doc = MagicMock()
        doc.blocks = [h4]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert h4.metadata["number_string"] == "0.0.0.1"

    def test_non_heading_skipped(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {}}
        b = MagicMock(); b.is_heading.return_value = False; b.text = "Body"; b.metadata = {}
        doc = MagicMock()
        doc.blocks = [b]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert "number_string" not in b.metadata

    def test_equation_numbered_without_brackets(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {"scope": "global", "brackets": ""}}
        eq = MagicMock()
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        doc.equations = [eq]
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert eq.number == "1"


# ══════════════════════════════════════════════════════════════════════════════
# formatting/section_ordering.py — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestSectionOrderValidatorEdgeCases:
    def test_no_expected_order_no_violations(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        loader = MagicMock()
        loader.load.return_value = {"sections": {"order": [], "required": []}}
        b = MagicMock(); b.is_heading.return_value = True; b.section_name = "Introduction"
        doc = MagicMock(); doc.blocks = [b]
        sv = SectionOrderValidator(loader)
        assert sv.validate_order(doc, "ieee") == []

    def test_duplicate_sections_not_reported_twice(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        loader = MagicMock()
        loader.load.return_value = {"sections": {"order": ["abstract", "introduction"], "required": ["abstract"]}}
        b1 = MagicMock(); b1.is_heading.return_value = True; b1.section_name = "Abstract"
        b2 = MagicMock(); b2.is_heading.return_value = True; b2.section_name = "Abstract"
        doc = MagicMock(); doc.blocks = [b1, b2]
        sv = SectionOrderValidator(loader)
        v = sv.validate_order(doc, "ieee")
        assert len(v) == 0

    def test_non_heading_blocks_ignored(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        loader = MagicMock()
        loader.load.return_value = {"sections": {"order": [], "required": ["abstract"]}}
        b = MagicMock(); b.is_heading.return_value = False; b.section_name = "Abstract"
        doc = MagicMock(); doc.blocks = [b]
        sv = SectionOrderValidator(loader)
        v = sv.validate_order(doc, "ieee")
        assert any("abstract" in vi.lower() for vi in v)

    def test_out_of_order_multiple(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        loader = MagicMock()
        loader.load.return_value = {"sections": {"order": ["abstract", "introduction", "methods", "conclusion"], "required": []}}
        b1 = MagicMock(); b1.is_heading.return_value = True; b1.section_name = "Conclusion"
        b2 = MagicMock(); b2.is_heading.return_value = True; b2.section_name = "Introduction"
        b3 = MagicMock(); b3.is_heading.return_value = True; b3.section_name = "Abstract"
        doc = MagicMock(); doc.blocks = [b1, b2, b3]
        sv = SectionOrderValidator(loader)
        v = sv.validate_order(doc, "ieee")
        assert len(v) >= 1
        assert any("out of order" in vi.lower() for vi in v)


# ══════════════════════════════════════════════════════════════════════════════
# formatting/style_mapper.py — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestStyleMapperEdgeCases:
    def test_empty_contract(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        loader = MagicMock()
        loader.load.return_value = {}
        sm = StyleMapper(loader)
        b = MagicMock(); b.block_type = "BODY"
        assert sm.get_style_name(b, "ieee") == "Normal"

    def test_empty_style_map(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        loader = MagicMock()
        loader.load.return_value = {"styles": {}}
        sm = StyleMapper(loader)
        b = MagicMock(); b.block_type = "BODY"
        assert sm.get_style_name(b, "ieee") == "Normal"

    def test_lowercase_block_type(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        loader = MagicMock()
        loader.load.return_value = {"styles": {"BLOCK_HEADING_1": "Heading 1"}}
        sm = StyleMapper(loader)
        b = MagicMock(); b.block_type = "heading_1"
        assert sm.get_style_name(b, "ieee") == "Heading 1"

    def test_missing_publisher(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        loader = MagicMock()
        loader.load.return_value = {"styles": {}}
        sm = StyleMapper(loader)
        b = MagicMock(); b.block_type = "BODY"
        assert sm.get_style_name(b, "") == "Normal"


# ══════════════════════════════════════════════════════════════════════════════
# formatting/formatter.py — remaining edge cases not in test_formatter.py
# ══════════════════════════════════════════════════════════════════════════════

class TestFormatterEdgeCases:
    def test_format_returns_none_on_safe_function_fallback(self):
        from app.pipeline.formatting.formatter import Formatter
        with (
            patch("app.pipeline.formatting.formatter.ContractLoader"),
            patch("app.pipeline.formatting.formatter.NumberingEngine"),
        ):
            f = Formatter(templates_dir=".", contracts_dir=".")
        doc = MagicMock()
        doc.formatting_options = {}
        doc.template = None
        f.numbering_engine.apply_numbering.side_effect = Exception("crash")
        result = f.format(doc, "ieee")
        assert result is None

    def test_format_with_none_template_name(self):
        from app.pipeline.formatting.formatter import Formatter
        with (
            patch("app.pipeline.formatting.formatter.ContractLoader"),
            patch("app.pipeline.formatting.formatter.NumberingEngine"),
        ):
            f = Formatter(templates_dir=".", contracts_dir=".")
        doc = MagicMock()
        doc.formatting_options = {}
        doc.template = MagicMock()
        doc.template.template_name = ""
        f.numbering_engine.apply_numbering.side_effect = lambda d, t: d
        with (
            patch.object(f, "_prepare_references"),
            patch("app.pipeline.formatting.formatter.WordDocument") as mock_wd,
            patch.object(f, "_load_contract", return_value={}),
            patch.object(f, "_apply_initial_layout"),
            patch.object(f, "_apply_page_size"),
            patch.object(f, "_install_post_save_hook"),
        ):
            mock_wd.return_value = MagicMock()
            result = f.format(doc, None)
            assert result is not None

    def test_format_empty_document(self):
        from app.pipeline.formatting.formatter import Formatter
        with (
            patch("app.pipeline.formatting.formatter.ContractLoader"),
            patch("app.pipeline.formatting.formatter.NumberingEngine"),
        ):
            f = Formatter(templates_dir=".", contracts_dir=".")
        doc = MagicMock()
        doc.formatting_options = {"template_engine": "legacy"}
        doc.template = MagicMock()
        doc.template.template_name = "ieee"
        doc.blocks = []
        doc.figures = []
        doc.equations = []
        doc.tables = []
        doc.references = []
        f.numbering_engine.apply_numbering.side_effect = lambda d, t: d
        with (
            patch.object(f, "_prepare_references"),
            patch.object(f, "_load_contract", return_value={}),
            patch.object(f, "_apply_initial_layout"),
            patch.object(f, "_apply_page_size"),
            patch.object(f, "_add_page_numbers"),
            patch.object(f, "_install_post_save_hook"),
            patch.object(f, "_apply_global_line_spacing"),
            patch.object(f, "_remove_static_page_number_placeholders"),
            patch("app.pipeline.formatting.formatter.WordDocument") as mock_wd,
        ):
            mock_wd.return_value = MagicMock()
            result = f.format(doc, "ieee")
            assert result is not None

    def test_format_legacy_path_reference_entry(self):
        from app.pipeline.formatting.formatter import Formatter
        with (
            patch("app.pipeline.formatting.formatter.ContractLoader"),
            patch("app.pipeline.formatting.formatter.NumberingEngine"),
        ):
            f = Formatter(templates_dir=".", contracts_dir=".")
        doc = MagicMock()
        doc.formatting_options = {"template_engine": "legacy"}
        doc.template = MagicMock()
        doc.template.template_name = "ieee"
        ref = MagicMock()
        ref.block_id = "b1"
        doc.references = [ref]
        b = MagicMock()
        b.block_type = MagicMock()
        b.block_type.value = "REFERENCE_ENTRY"
        b.block_id = "b1"
        b.index = 1
        b.text = "[1] Raw"
        b.metadata = {}
        doc.blocks = [b]
        doc.figures = []
        doc.equations = []
        doc.tables = []
        f.numbering_engine.apply_numbering.side_effect = lambda d, t: d
        with (
            patch.object(f, "_prepare_references"),
            patch.object(f, "_load_contract", return_value={}),
            patch.object(f, "_apply_initial_layout"),
            patch.object(f, "_apply_page_size"),
            patch.object(f, "_render_block"),
            patch.object(f, "_install_post_save_hook"),
            patch.object(f, "_apply_global_line_spacing"),
            patch.object(f, "_add_page_numbers"),
            patch.object(f, "_remove_static_page_number_placeholders"),
            patch.object(f, "_get_target_columns", return_value=1),
            patch.object(f.reference_formatter, "format_reference", return_value="[1] Formatted"),
            patch("app.pipeline.formatting.formatter.WordDocument") as mock_wd,
        ):
            mock_wd.return_value = MagicMock()
            result = f.format(doc, "ieee")
            assert result is not None

    def test_column_switching(self):
        from app.pipeline.formatting.formatter import Formatter
        with (
            patch("app.pipeline.formatting.formatter.ContractLoader"),
            patch("app.pipeline.formatting.formatter.NumberingEngine"),
        ):
            f = Formatter(templates_dir=".", contracts_dir=".")
        doc = MagicMock()
        doc.formatting_options = {"template_engine": "legacy"}
        doc.template = MagicMock()
        doc.template.template_name = "ieee"
        b1 = MagicMock(); b1.block_type = MagicMock(); b1.block_type.value = "BODY"
        b1.index = 1; b1.text = "Single column"; b1.metadata = {}; b1.section_name = "abstract"
        b2 = MagicMock(); b2.block_type = MagicMock(); b2.block_type.value = "BODY"
        b2.index = 2; b2.text = "Two columns"; b2.metadata = {}; b2.section_name = "body"
        doc.blocks = [b1, b2]
        doc.figures = []
        doc.equations = []
        doc.tables = []
        doc.references = []
        f.numbering_engine.apply_numbering.side_effect = lambda d, t: d
        with (
            patch.object(f, "_prepare_references"),
            patch.object(f, "_load_contract", return_value={}),
            patch.object(f, "_apply_initial_layout"),
            patch.object(f, "_apply_page_size"),
            patch.object(f, "_render_block"),
            patch.object(f, "_set_columns"),
            patch.object(f, "_install_post_save_hook"),
            patch.object(f, "_add_page_numbers"),
            patch.object(f, "_remove_static_page_number_placeholders"),
            patch.object(f, "_apply_global_line_spacing"),
            patch.object(f, "_get_target_columns", side_effect=[1, 2]),
            patch("app.pipeline.formatting.formatter.WordDocument") as mock_wd,
        ):
            mock_wd.return_value = MagicMock()
            result = f.format(doc, "ieee")
            assert result is not None

    def test_is_bullet_list_item_various(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter.__new__(Formatter)
        assert f._is_bullet_list_item("\u25e6 item") is True
        assert f._is_bullet_list_item("\u25aa item") is True
        assert f._is_bullet_list_item("\u25ab item") is True

    def test_is_numbered_list_item_roman(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter.__new__(Formatter)
        assert f._is_numbered_list_item("i. item") is True
        assert f._is_numbered_list_item("iv. item") is True
        assert f._is_numbered_list_item("x. item") is True

    def test_is_numbered_list_item_multi_digit(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter.__new__(Formatter)
        assert f._is_numbered_list_item("10. item") is True
        assert f._is_numbered_list_item("100. item") is True

    def test_is_numbered_list_item_none(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter.__new__(Formatter)
        assert f._is_numbered_list_item(None) is False

    def test_process_without_template(self):
        from app.pipeline.formatting.formatter import Formatter
        with patch("app.pipeline.formatting.formatter.ContractLoader"):
            f = Formatter(templates_dir=".", contracts_dir=".")
        doc = MagicMock()
        doc.template = None
        with patch.object(f, "format", return_value="rendered"):
            result = f.process(doc)
        assert result.generated_doc == "rendered"

    def test_apply_spacing_caption_figure(self):
        from app.pipeline.formatting.formatter import Formatter
        with patch("app.pipeline.formatting.formatter.ContractLoader"):
            f = Formatter(templates_dir=".", contracts_dir=".")
        para = MagicMock()
        block = MagicMock()
        block.is_heading.return_value = False
        block.block_type = MagicMock()
        block.block_type.value = "FIGURE_CAPTION"
        f.contract_loader.load.return_value = {
            "layout": {"spacing": {"figure": {"before": 6, "after": 12}}}
        }
        f._apply_spacing_from_contract(para, block, "ieee")
        para.paragraph_format.space_before = 6
        para.paragraph_format.space_after = 12

    def test_apply_spacing_references(self):
        from app.pipeline.formatting.formatter import Formatter
        with patch("app.pipeline.formatting.formatter.ContractLoader"):
            f = Formatter(templates_dir=".", contracts_dir=".")
        para = MagicMock()
        block = MagicMock()
        block.is_heading.return_value = False
        block.block_type = MagicMock()
        block.block_type.value = "REFERENCE_ENTRY"
        f.contract_loader.load.return_value = {
            "layout": {"spacing": {"references": {"before": 3, "after": 3}}}
        }
        f._apply_spacing_from_contract(para, block, "ieee")
        para.paragraph_format.space_before = 3
        para.paragraph_format.space_after = 3
