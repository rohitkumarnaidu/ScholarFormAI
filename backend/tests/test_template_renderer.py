from unittest.mock import MagicMock, patch


class TestCoerceBool:
    def test_none_returns_default(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(None, True) is True
        assert TemplateRenderer._coerce_bool(None, False) is False

    def test_bool_values(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(True, False) is True
        assert TemplateRenderer._coerce_bool(False, True) is False

    def test_int_values(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(1, False) is True
        assert TemplateRenderer._coerce_bool(0, True) is False

    def test_string_true_values(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        for v in ["1", "true", "yes", "on"]:
            assert TemplateRenderer._coerce_bool(v, False) is True

    def test_string_false_values(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        for v in ["0", "false", "no", "off", ""]:
            assert TemplateRenderer._coerce_bool(v, True) is False


class TestResolveBoolOption:
    def test_first_key_wins(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        assert tr._resolve_bool_option({"a": True, "b": False}, ["a", "b"], False) is True

    def test_second_key_fallback(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        assert tr._resolve_bool_option({"b": True}, ["a", "b"], False) is True

    def test_no_match_returns_default(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        assert tr._resolve_bool_option({}, ["a"], True) is True


class TestBlockTypeToken:
    def test_enum_value(self):
        from app.models import BlockType
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        block = MagicMock()
        block.block_type = BlockType.HEADING_1
        assert TemplateRenderer._block_type_token(block) == "heading_1"

    def test_string_value(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        block = MagicMock()
        block.block_type = "TITLE"
        assert TemplateRenderer._block_type_token(block) == "title"


class TestFirstBlockText:
    def test_finds_first(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        block1 = MagicMock()
        block1.index = 0
        block1.text = ""
        block1.block_type = "TITLE"
        block2 = MagicMock()
        block2.index = 1
        block2.text = "My Title"
        block2.block_type = "TITLE"
        result = tr._first_block_text([block1, block2], "title")
        assert result == "My Title"

    def test_returns_empty_when_not_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        result = tr._first_block_text([], "title")
        assert result == ""


class TestAllBlockText:
    def test_finds_all(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        b1 = MagicMock()
        b1.index = 0
        b1.text = "Auth 1"
        b1.block_type = "AUTHOR"
        b2 = MagicMock()
        b2.index = 1
        b2.text = ""
        b2.block_type = "AUTHOR"
        b3 = MagicMock()
        b3.index = 2
        b3.text = "Auth 2"
        b3.block_type = "AUTHOR"
        result = tr._all_block_text([b1, b2, b3], "author")
        assert result == ["Auth 1", "Auth 2"]


class TestCollectSections:
    def test_skips_skipped_types(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        b = MagicMock()
        b.index = 0
        b.text = "Abstract text"
        b.block_type = "ABSTRACT_BODY"
        b.metadata = {}
        result = tr._collect_sections([b])
        assert len(result) == 0

    def test_merges_paragraphs_under_section(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        b1 = MagicMock()
        b1.index = 0
        b1.text = "Intro"
        b1.block_type = "HEADING_1"
        b1.metadata = {}
        b2 = MagicMock()
        b2.index = 1
        b2.text = "First para"
        b2.block_type = "BODY"
        b2.metadata = {}
        b3 = MagicMock()
        b3.index = 2
        b3.text = "Second para"
        b3.block_type = "BODY"
        b3.metadata = {}
        result = tr._collect_sections([b1, b2, b3])
        assert len(result) == 1
        assert result[0]["heading"] == "Intro"
        assert len(result[0]["paragraphs"]) == 2

    def test_skips_footnote_metadata(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        b = MagicMock()
        b.index = 0
        b.text = "Footnote text"
        b.block_type = "BODY"
        b.metadata = {"is_footnote": True}
        result = tr._collect_sections([b])
        assert len(result) == 0

    def test_captures_last_section(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        b = MagicMock()
        b.index = 0
        b.text = "Plain text"
        b.block_type = "BODY"
        b.metadata = {}
        result = tr._collect_sections([b])
        assert len(result) == 1
        assert result[0]["heading"] == "Body"


class TestCollectReferences:
    def test_uses_document_references(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        doc = MagicMock()
        ref1 = MagicMock()
        ref1.index = 1
        ref1.formatted_text = "Ref B"
        ref1.raw_text = ""
        ref2 = MagicMock()
        ref2.index = 0
        ref2.formatted_text = "Ref A"
        ref2.raw_text = ""
        doc.references = [ref1, ref2]
        doc.blocks = []
        result = tr._collect_references(doc)
        assert result == ["Ref A", "Ref B"]

    def test_falls_back_to_blocks(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        doc = MagicMock()
        doc.references = []
        b = MagicMock()
        b.index = 0
        b.text = "[1] Ref text"
        b.block_type = "REFERENCE_ENTRY"
        doc.blocks = [b]
        result = tr._collect_references(doc)
        assert "[1] Ref text" in result


class TestHasRenderableTemplate:
    @patch("app.pipeline.formatting.template_renderer.TemplateRenderer._has_template_markers")
    def test_missing_dir_returns_false(self, mock_markers):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir="/nonexistent")
        assert not tr.has_renderable_template("ieee")


class TestBuildContext:
    def test_includes_title_from_metadata(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        doc = MagicMock()
        doc.metadata.title = "My Paper"
        doc.metadata.abstract = "Abstract"
        doc.metadata.keywords = ["AI"]
        doc.metadata.authors = ["Alice"]
        doc.metadata.affiliations = ["MIT"]
        doc.blocks = []
        doc.references = []
        doc.formatting_options = {}
        context = tr.build_context(doc)
        assert context["title"] == "My Paper"
        assert context["abstract"] == "Abstract"
        assert context["keywords"] == ["AI"]
        assert context["authors"] == ["Alice"]

    def test_fallback_title_from_filename(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer()
        doc = MagicMock()
        doc.metadata.title = ""
        doc.metadata.abstract = ""
        doc.metadata.keywords = []
        doc.metadata.authors = []
        doc.metadata.affiliations = []
        doc.blocks = []
        doc.references = []
        doc.formatting_options = {}
        doc.original_filename = "paper.docx"
        context = tr.build_context(doc)
        assert context["title"] == "paper.docx"
