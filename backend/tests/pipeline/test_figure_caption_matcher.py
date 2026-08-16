# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCaptionMatcher:
    def _make_doc(self, blocks=None, figures=None):
        doc = MagicMock()
        doc.blocks = blocks or []
        doc.figures = figures or []
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None
        return doc

    def _make_block(self, index=0, text="", block_id="b1", is_heading=False):
        b = MagicMock()
        b.index = index
        b.text = text
        b.block_id = block_id
        b.metadata = {}
        b.is_heading.return_value = is_heading
        return b

    def _make_figure(self, figure_id="f1", caption_text="", export_path=None, metadata=None):
        f = MagicMock()
        f.figure_id = figure_id
        f.caption_text = caption_text
        f.caption_block_id = None
        f.export_path = export_path
        f.metadata = metadata or {}
        return f

    def test_no_figures(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        doc = self._make_doc(figures=[])
        m = CaptionMatcher()
        result = m.process(doc)
        assert result is doc

    def test_match_caption(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        cap_block = self._make_block(index=0, text="Figure 1: Test", block_id="cap1")
        body_block = self._make_block(index=1, text="Body", block_id="body1")
        fig = self._make_figure(figure_id="f1", metadata={"block_index": 1})
        doc = self._make_doc(blocks=[cap_block, body_block], figures=[fig])
        m = CaptionMatcher(max_distance=3)
        m.process(doc)
        assert fig.caption_text == "Figure 1: Test"
        assert fig.caption_block_id == "cap1"
        assert cap_block.metadata["is_figure_caption"] is True

    def test_caption_candidates_skip_headings(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        heading = self._make_block(index=0, text="Figure 1: Overview", block_id="h1", is_heading=True)
        m = CaptionMatcher()
        candidates = m._find_caption_candidates([heading])
        assert candidates == []

    def test_vision_enhancement_skipped_no_path(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        fig = self._make_figure(figure_id="f1", export_path=None)
        m = CaptionMatcher()
        count = m._enhance_captions_with_vision([fig])
        assert count == 0

    @patch("app.pipeline.figures.caption_matcher.os.path.exists", return_value=True)
    def test_vision_enhancement_calls_client(self, mock_exists):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        vision = MagicMock()
        vision.analyze_figure.return_value = "A chart showing data"
        m = CaptionMatcher()
        m.vision_client = vision
        fig = self._make_figure(figure_id="f1", export_path="/tmp/fig1.png", caption_text="")
        count = m._enhance_captions_with_vision([fig])
        assert count == 1
        assert "vision_generated" in fig.metadata.get("caption_source", "")

    @patch("app.pipeline.figures.caption_matcher.os.path.exists", return_value=True)
    def test_vision_enhancement_existing_caption(self, mock_exists):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        vision = MagicMock()
        vision.analyze_figure.return_value = "Enhanced description"
        m = CaptionMatcher()
        m.vision_client = vision
        fig = self._make_figure(figure_id="f1", export_path="/tmp/fig1.png", caption_text="Original caption")
        count = m._enhance_captions_with_vision([fig])
        assert count == 1
        assert fig.metadata["caption_source"] == "manual_with_vision"

    def test_convenience_function(self):
        from app.pipeline.figures.caption_matcher import link_figures

        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None
        result = link_figures(doc)
        assert result is doc

    def test_enable_vision_init(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        m = CaptionMatcher(enable_vision=True)
        assert m.enable_vision is True

    def test_vision_enhancement_exception(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher

        vision = MagicMock()
        vision.analyze_figure.side_effect = RuntimeError("vision failed")
        m = CaptionMatcher()
        m.vision_client = vision
        fig = self._make_figure(figure_id="f1", export_path="/tmp/f.png", caption_text="")
        with patch("app.pipeline.figures.caption_matcher.os.path.exists", return_value=True):
            count = m._enhance_captions_with_vision([fig])
        assert count == 0
