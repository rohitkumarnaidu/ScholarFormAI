from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
import json


class TestPreviewRenderer:
    def _make_renderer(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer.__new__(PreviewRenderer)
        renderer._redis = None
        renderer._redis_enabled = False
        renderer._redis_warning_logged = False
        renderer._local_cache = {}
        renderer._css_cache = {}
        renderer._template_names = set()
        return renderer

    def test_init_redis_disabled(self):
        from app.services.preview_renderer import PreviewRenderer
        with patch("app.services.preview_renderer.settings.REDIS_ENABLED", False):
            renderer = PreviewRenderer()
            assert renderer._redis is None

    def test_init_redis_enabled_fails_gracefully(self):
        from app.services.preview_renderer import PreviewRenderer
        with patch("app.services.preview_renderer.settings.REDIS_ENABLED", True):
            with patch("app.services.preview_renderer.redis.from_url", side_effect=Exception("no redis")):
                with patch("app.services.preview_renderer.settings.REDIS_URL", "redis://localhost"):
                    renderer = PreviewRenderer()
                    assert renderer._redis is None

    def test_normalize_template(self):
        renderer = self._make_renderer()
        assert renderer._normalize_template("IEEE") == "ieee"
        assert renderer._normalize_template("Modern Blue") == "modern_blue"
        with patch("app.services.preview_renderer.settings.DEFAULT_TEMPLATE", "apa"):
            assert renderer._normalize_template("") == "apa"

    def test_split_blocks(self):
        renderer = self._make_renderer()
        blocks = renderer._split_blocks("Hello\n\nWorld")
        assert len(blocks) >= 2

    def test_is_list_item(self):
        renderer = self._make_renderer()
        assert renderer._is_list_item("- item") is True
        assert renderer._is_list_item("1. item") is True
        assert renderer._is_list_item("not a list") is False

    def test_is_caption(self):
        renderer = self._make_renderer()
        assert renderer._is_caption("Figure 1: Caption") is True
        assert renderer._is_caption("Table 2: title") is True
        assert renderer._is_caption("Fig. 3 - caption") is True
        assert renderer._is_caption("Not a caption") is False

    def test_is_heading_markdown(self):
        renderer = self._make_renderer()
        assert renderer._is_heading("# Title") is True
        assert renderer._is_heading("## Subtitle") is True

    def test_is_heading_numeric(self):
        renderer = self._make_renderer()
        assert renderer._is_heading("1.1 Introduction") is True
        assert renderer._is_heading("1.1 Background") is True

    def test_heading_level_hash(self):
        renderer = self._make_renderer()
        assert renderer._heading_level("# Title") == 2
        assert renderer._heading_level("## Sub") == 2
        assert renderer._heading_level("### Sub2") == 3
        assert renderer._heading_level("#### Sub3") == 4
        assert renderer._heading_level("##### Sub4") == 4

    def test_heading_level_numeric(self):
        renderer = self._make_renderer()
        assert renderer._heading_level("1. Intro") == 2
        assert renderer._heading_level("1.1 Sub") == 3
        assert renderer._heading_level("1.1.1 Sub2") == 4

    def test_is_title(self):
        renderer = self._make_renderer()
        assert renderer._is_title("Research Paper Title", 0) is True
        assert renderer._is_title("Not at index 0", 1) is False
        assert renderer._is_title("Too long text" + "x" * 150, 0) is False
        assert renderer._is_title("Ends with period.", 0) is False

    def test_classify_blocks_title(self):
        renderer = self._make_renderer()
        blocks = renderer._classify_blocks([{"raw_type": "paragraph", "text": "My Title"}])
        assert blocks[0]["type"] == "title"

    def test_classify_blocks_abstract(self):
        renderer = self._make_renderer()
        blocks = renderer._classify_blocks([
            {"raw_type": "paragraph", "text": "Abstract"},
            {"raw_type": "paragraph", "text": "This is the abstract text"},
        ])
        assert blocks[0]["type"] == "abstract_heading"
        assert blocks[1]["type"] == "abstract_body"

    def test_classify_blocks_heading(self):
        renderer = self._make_renderer()
        blocks = renderer._classify_blocks([
            {"raw_type": "paragraph", "text": "Title."},
            {"raw_type": "paragraph", "text": "1.1 Introduction"},
        ])
        assert blocks[1]["type"] == "heading"

    def test_classify_blocks_caption(self):
        renderer = self._make_renderer()
        blocks = renderer._classify_blocks([
            {"raw_type": "paragraph", "text": "Figure 1: Test."},
        ])
        assert blocks[0]["type"] == "caption"

    def test_classify_blocks_paragraph(self):
        renderer = self._make_renderer()
        blocks = renderer._classify_blocks([
            {"raw_type": "paragraph", "text": "Some paragraph text."},
        ])
        assert blocks[0]["type"] == "paragraph"

    def test_render_blocks(self):
        renderer = self._make_renderer()
        html = renderer._render_blocks([
            {"type": "title", "text": "Title"},
            {"type": "heading", "text": "Heading", "level": 2},
            {"type": "paragraph", "text": "Para"},
        ])
        assert "doc-title" in html
        assert "doc-heading" in html
        assert "doc-paragraph" in html

    def test_render_blocks_list(self):
        renderer = self._make_renderer()
        html = renderer._render_blocks([
            {"type": "list_item", "text": "Item 1"},
            {"type": "list_item", "text": "Item 2"},
            {"type": "paragraph", "text": "After list"},
        ])
        assert "doc-list" in html
        assert "<li>Item 1</li>" in html

    def test_render_preview_empty(self):
        renderer = self._make_renderer()
        renderer._template_names = {"ieee", "apa"}
        with patch.object(renderer, '_get_template_css', return_value="/* css */"):
            result = renderer.render_preview("", "ieee")
            assert "html" in result
            assert "empty_content" in result["warnings"]

    def test_render_preview_with_content(self):
        renderer = self._make_renderer()
        renderer._template_names = {"ieee", "apa"}
        with patch.object(renderer, '_get_template_css', return_value="/* css */"):
            result = renderer.render_preview("Hello World", "ieee")
            assert result["html"] is not None
            assert "Hello World" in result["html"]

    def test_render_preview_unknown_template(self):
        renderer = self._make_renderer()
        renderer._template_names = {"apa"}
        with patch.object(renderer, '_get_template_css', return_value="/* css */"):
            with patch.object(renderer, '_normalize_template', side_effect=lambda x: x):
                with patch("app.services.preview_renderer.settings.DEFAULT_TEMPLATE", "apa"):
                    result = renderer.render_preview("test", "ieee")
                    assert "unknown_template" in str(result["warnings"])

    def test_preload_template_css(self):
        renderer = self._make_renderer()
        renderer._template_names = {"ieee"}
        with patch.object(renderer, '_get_template_css', return_value="css"):
            renderer.preload_template_css()
            assert "ieee" in renderer._css_cache

    def test_global_preload_function(self):
        from app.services.preview_renderer import preload_template_css, preview_renderer
        assert preview_renderer is not None
