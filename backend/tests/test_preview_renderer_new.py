import time
from unittest.mock import patch

import pytest


@pytest.fixture
def renderer():
    with patch("app.services.preview_renderer.TEMPLATE_ROOT"), patch("app.services.preview_renderer.settings"):
        from app.services.preview_renderer import PreviewRenderer
        r = PreviewRenderer()
        r._redis = None
        r._redis_enabled = False
        r._template_names = {"ieee", "apa", "modern_blue"}
        r._css_cache = {}
        r._local_cache = {}
        return r


class TestNormalizeTemplate:
    def test_normalizes_lowercase(self, renderer):
        assert renderer._normalize_template("IEEE") == "ieee"

    def test_strips_whitespace(self, renderer):
        assert renderer._normalize_template("  Apa  ") == "apa"

    def test_replaces_spaces(self, renderer):
        assert renderer._normalize_template("Modern Blue") == "modern_blue"

    def test_empty_falls_to_default(self, renderer):
        with patch("app.services.preview_renderer.settings.DEFAULT_TEMPLATE", "IEEE"):
            assert renderer._normalize_template("") == "ieee"

    def test_none_falls_to_default(self, renderer):
        with patch("app.services.preview_renderer.settings.DEFAULT_TEMPLATE", "APA"):
            assert renderer._normalize_template(None) == "apa"


class TestRenderCacheKey:
    def test_returns_consistent_hash(self, renderer):
        k1 = renderer._render_cache_key("hello", "ieee")
        k2 = renderer._render_cache_key("hello", "ieee")
        assert k1 == k2

    def test_different_content_different_key(self, renderer):
        k1 = renderer._render_cache_key("hello", "ieee")
        k2 = renderer._render_cache_key("world", "ieee")
        assert k1 != k2


class TestSplitBlocks:
    def test_splits_paragraphs(self, renderer):
        blocks = renderer._split_blocks("Line one.\n\nLine two.")
        assert len(blocks) == 2
        assert blocks[0]["raw_type"] == "paragraph"
        assert blocks[1]["raw_type"] == "paragraph"

    def test_detects_list_items(self, renderer):
        blocks = renderer._split_blocks("- item one\n- item two")
        assert len(blocks) == 2
        assert blocks[0]["raw_type"] == "list_item"
        assert blocks[1]["raw_type"] == "list_item"

    def test_handles_empty_string(self, renderer):
        assert renderer._split_blocks("") == []

    def test_numbered_list_items(self, renderer):
        blocks = renderer._split_blocks("1. First\n2. Second")
        assert len(blocks) == 2
        assert blocks[0]["raw_type"] == "list_item"

    def test_accumulates_lines(self, renderer):
        blocks = renderer._split_blocks("This is a\nmulti-line paragraph.")
        assert len(blocks) == 1
        assert "multi-line" in blocks[0]["text"]


class TestIsListItem:
    def test_hyphen(self, renderer):
        assert renderer._is_list_item("- item") is True

    def test_asterisk(self, renderer):
        assert renderer._is_list_item("* item") is True

    def test_numbered(self, renderer):
        assert renderer._is_list_item("1. item") is True
        assert renderer._is_list_item("1) item") is True

    def test_plain_text_false(self, renderer):
        assert renderer._is_list_item("This is a paragraph") is False


class TestStripListMarker:
    def test_removes_hyphen(self, renderer):
        assert renderer._strip_list_marker("- hello") == "hello"

    def test_removes_number(self, renderer):
        assert renderer._strip_list_marker("1. hello") == "hello"
        assert renderer._strip_list_marker("10) hello") == "hello"


class TestIsCaption:
    def test_figure_numbered(self, renderer):
        assert renderer._is_caption("Figure 1: Results") is True

    def test_table_numbered(self, renderer):
        assert renderer._is_caption("Table 2: Data") is True

    def test_fig_abbreviated(self, renderer):
        assert renderer._is_caption("Fig. 3: Graph") is True

    def test_plain_text_false(self, renderer):
        assert renderer._is_caption("Introduction") is False


class TestIsHeading:
    def test_hash_heading(self, renderer):
        assert renderer._is_heading("## Introduction") is True

    def test_numeric_heading(self, renderer):
        assert renderer._is_heading("1.1 Results") is True

    def test_uppercase_short(self, renderer):
        assert renderer._is_heading("ABSTRACT") is True

    def test_long_text_false(self, renderer):
        assert renderer._is_heading("This is a very long paragraph" * 5) is False


class TestHeadingLevel:
    def test_hash_level(self, renderer):
        assert renderer._heading_level("### Subsection") == 3

    def test_numeric_depth(self, renderer):
        assert renderer._heading_level("1.2.3 Subsection") == 4

    def test_uppercase_default(self, renderer):
        assert renderer._heading_level("ABSTRACT") == 2


class TestIsTitle:
    def test_first_block_short_no_period(self, renderer):
        assert renderer._is_title("My Paper Title", 0) is True

    def test_not_first_block(self, renderer):
        assert renderer._is_title("Title", 1) is False

    def test_too_long(self, renderer):
        assert renderer._is_title("A" * 200, 0) is False

    def test_ends_with_period(self, renderer):
        assert renderer._is_title("A title.", 0) is False


class TestClassifyBlocks:
    def test_title(self, renderer):
        blocks = renderer._classify_blocks([{"raw_type": "paragraph", "text": "My Title"}])
        assert blocks[0]["type"] == "title"

    def test_abstract_heading(self, renderer):
        blocks = renderer._classify_blocks([{"raw_type": "paragraph", "text": "Abstract"}])
        assert blocks[0]["type"] == "abstract_heading"

    def test_caption(self, renderer):
        blocks = renderer._classify_blocks([
            {"raw_type": "paragraph", "text": "Long enough to not be a title, ends with a period."},
            {"raw_type": "paragraph", "text": "Figure 1: Data"},
        ])
        assert blocks[1]["type"] == "caption"

    def test_heading(self, renderer):
        blocks = renderer._classify_blocks([
            {"raw_type": "paragraph", "text": "Title at index 0."},
            {"raw_type": "paragraph", "text": "## Introduction"},
        ])
        assert blocks[1]["type"] == "heading"

    def test_paragraph(self, renderer):
        blocks = renderer._classify_blocks([{"raw_type": "paragraph", "text": "Some text."}])
        assert blocks[0]["type"] == "paragraph"

    def test_list_item(self, renderer):
        blocks = renderer._classify_blocks([{"raw_type": "list_item", "text": "item"}])
        assert blocks[0]["type"] == "list_item"


class TestRenderBlocks:
    def test_title_html(self, renderer):
        html = renderer._render_blocks([{"type": "title", "text": "Title"}])
        assert 'class="doc-title"' in html
        assert "Title" in html

    def test_heading_html(self, renderer):
        html = renderer._render_blocks([{"type": "heading", "text": "Intro", "level": 2}])
        assert 'class="doc-heading"' in html

    def test_paragraph_html(self, renderer):
        html = renderer._render_blocks([{"type": "paragraph", "text": "Text."}])
        assert 'class="doc-paragraph"' in html

    def test_list_items_wrapped(self, renderer):
        html = renderer._render_blocks([
            {"type": "list_item", "text": "a"},
            {"type": "list_item", "text": "b"},
        ])
        assert "<ul" in html
        assert "</ul>" in html

    def test_escapes_html(self, renderer):
        html = renderer._render_blocks([{"type": "paragraph", "text": "<script>alert(1)</script>"}])
        assert "&lt;script&gt;" in html
        assert "<script>" not in html


class TestCache:
    def test_get_cached_miss(self, renderer):
        assert renderer._get_cached("missing") is None

    def test_set_and_get_cached(self, renderer):
        renderer._set_cached("k", {"data": 1}, ttl=60)
        result = renderer._get_cached("k")
        assert result == {"data": 1}

    def test_expired_entry(self, renderer):
        renderer._local_cache["k"] = __import__("app.services.preview_renderer").services.preview_renderer._CachedValue(
            expires_at=time.time() - 10, value={"data": 1}
        )
        assert renderer._get_cached("k") is None


class TestBuildFallbackCss:
    def test_returns_css_string(self, renderer):
        css = renderer._build_fallback_css("ieee", {})
        assert "preview-page" in css
        assert "font-family" in css

    def test_a4_page_width(self, renderer):
        css = renderer._build_fallback_css("ieee", {"layout": {"page_size": "A4"}})
        assert "8.27in" in css

    def test_sans_serif_templates(self, renderer):
        for t in ["modern_blue", "modern_gold", "resume"]:
            css = renderer._build_fallback_css(t, {})
            assert "sans-serif" in css
