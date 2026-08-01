# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch


def _make_block(index, text="", is_heading=False):
    b = MagicMock()
    b.is_heading.return_value = is_heading
    b.text = text
    b.index = index
    b.block_id = f"b{index}"
    b.metadata = {}
    return b


def _make_figure(figure_id, block_index, export_path=None, caption_text=""):
    f = MagicMock()
    f.figure_id = figure_id
    f.metadata = {"block_index": block_index}
    f.caption_text = caption_text
    f.caption_block_id = None
    f.export_path = export_path
    return f


class TestCaptionMatcher:
    def test_init_defaults(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        assert cm.max_distance == 2
        assert cm.enable_vision is False
        assert cm.vision_client is None

    def test_init_custom_max_distance(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher(max_distance=5)
        assert cm.max_distance == 5

    def test_init_vision_enabled_success(self):
        mock_client = MagicMock()
        with patch("app.services.nvidia_client.get_nvidia_client", return_value=mock_client):
            from app.pipeline.figures.caption_matcher import CaptionMatcher
            cm = CaptionMatcher(enable_vision=True)
            assert cm.enable_vision is True
            assert cm.vision_client is mock_client

    def test_init_vision_enabled_exception(self):
        with patch("app.services.nvidia_client.get_nvidia_client", side_effect=Exception("no GPU")):
            from app.pipeline.figures.caption_matcher import CaptionMatcher
            cm = CaptionMatcher(enable_vision=True)
            assert cm.vision_client is None

    def test_find_caption_candidates_empty(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        assert cm._find_caption_candidates([]) == []

    def test_find_caption_candidates_heading_skipped(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        assert cm._find_caption_candidates([_make_block(0, "Figure 1 Analysis", is_heading=True)]) == []

    def test_find_caption_candidates_matches(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        blocks = [
            _make_block(3, "Figure 1: Experimental results"),
            _make_block(5, "Some body text"),
            _make_block(7, "Fig. 2: Another figure"),
        ]
        assert cm._find_caption_candidates(blocks) == [3, 7]

    def test_find_caption_candidates_case_insensitive(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        assert cm._find_caption_candidates([_make_block(1, "figure 10: Lowercase")]) == [1]

    def test_match_candidates_empty_candidates(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        assert cm._match_candidates([], [], []) == []

    def test_match_candidates_basic_match(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher(max_distance=2)
        fig = _make_figure("F1", 5)
        fig_block = _make_block(5, "Figure block content")
        cap_block = _make_block(6, "Figure 1: Test caption")
        blocks = [fig_block, cap_block]
        matches = cm._match_candidates(blocks, [fig], [6])
        assert len(matches) == 1
        assert matches[0][0] is fig
        assert matches[0][1] is cap_block

    def test_match_candidates_beyond_max_distance(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher(max_distance=2)
        fig = _make_figure("F1", 0)
        # 4 blocks between fig and caption → list distance 4 > 2
        blocks = [
            _make_block(0, "fig"),
            _make_block(1, "a"),
            _make_block(2, "b"),
            _make_block(3, "c"),
            _make_block(10, "Figure 1: Far away"),
        ]
        matches = cm._match_candidates(blocks, [fig], [10])
        assert matches == []

    def test_match_candidates_no_block_index(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        fig = MagicMock()
        fig.figure_id = "F1"
        fig.metadata = {}
        cap_block = _make_block(1, "Figure 1")
        matches = cm._match_candidates([cap_block], [fig], [1])
        assert matches == []

    def test_match_candidates_already_assigned_figure(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher(max_distance=2)
        fig = _make_figure("F1", 0)
        fig_block = _make_block(0, "fig")
        cap1 = _make_block(1, "Figure 1: First")
        cap2 = _make_block(2, "Figure 1: Second")
        blocks = [fig_block, cap1, cap2]
        matches = cm._match_candidates(blocks, [fig], [1, 2])
        assert len(matches) == 1

    def test_match_candidates_tiebreak_prefers_above(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher(max_distance=3)
        fig_above = _make_figure("F1", 0)
        fig_below = _make_figure("F2", 4)
        cap_block = _make_block(2, "Figure: Middle")
        blocks = [
            _make_block(0, "fig above"),
            cap_block,
            _make_block(4, "fig below"),
        ]
        matches = cm._match_candidates(blocks, [fig_above, fig_below], [2])
        assert len(matches) == 1
        assert matches[0][0] is fig_above

    def test_process_no_figures(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        doc = MagicMock()
        doc.blocks = [MagicMock()]
        doc.figures = []
        result = cm.process(doc)
        assert result is doc

    def test_process_with_matches(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher(max_distance=2)
        fig_block = _make_block(0, "image here")
        cap_block = _make_block(1, "Figure 1: Results")
        fig = _make_figure("F1", 0)
        doc = MagicMock()
        doc.blocks = [fig_block, cap_block]
        doc.figures = [fig]
        result = cm.process(doc)
        assert result is doc
        assert fig.caption_text == "Figure 1: Results"
        assert fig.caption_block_id == "b1"
        assert cap_block.metadata["is_figure_caption"] is True
        assert cap_block.metadata["linked_figure_id"] == "F1"
        doc.add_processing_stage.assert_called_once()

    def test_process_exception(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        doc = MagicMock()
        doc.blocks = [MagicMock()]
        doc.figures = [MagicMock()]
        with patch.object(cm, "_find_caption_candidates", side_effect=RuntimeError("boom")):
            result = cm.process(doc)
        assert result is doc
        doc.add_processing_stage.assert_called_once_with(
            stage_name="figure_linking",
            status="error",
            message=ANY
        )

    def test_process_with_vision_enhancement(self):
        mock_client = MagicMock()
        mock_client.analyze_figure.return_value = "A bar chart showing growth"
        with patch("app.services.nvidia_client.get_nvidia_client", return_value=mock_client):
            from app.pipeline.figures.caption_matcher import CaptionMatcher
            cm = CaptionMatcher(enable_vision=True)
            fig_block = _make_block(0, "image")
            cap_block = _make_block(1, "Figure 1: Basic")
            fig = _make_figure("F1", 0, export_path="/tmp/fig1.png", caption_text="")
            doc = MagicMock()
            doc.blocks = [fig_block, cap_block]
            doc.figures = [fig]
            with patch("os.path.exists", return_value=True):
                result = cm.process(doc)
            assert result is doc
            assert fig.caption_text == "Figure 1: Basic"
            assert fig.metadata["caption_source"] == "manual_with_vision"

    def test_enhance_captions_no_export_path(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        cm.vision_client = MagicMock()
        fig = _make_figure("F1", 1, export_path=None)
        assert cm._enhance_captions_with_vision([fig]) == 0

    def test_enhance_captions_export_path_missing(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        cm.vision_client = MagicMock()
        fig = _make_figure("F1", 1, export_path="/nonexistent.png")
        with patch("os.path.exists", return_value=False):
            assert cm._enhance_captions_with_vision([fig]) == 0

    def test_enhance_captions_vision_fails(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        mock_client = MagicMock()
        mock_client.analyze_figure.side_effect = Exception("vision error")
        cm.vision_client = mock_client
        fig = _make_figure("F1", 1, export_path="/tmp/fig1.png")
        with patch("os.path.exists", return_value=True):
            assert cm._enhance_captions_with_vision([fig]) == 0

    def test_enhance_captions_existing_caption(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        mock_client = MagicMock()
        mock_client.analyze_figure.return_value = "A bar chart"
        cm.vision_client = mock_client
        fig = _make_figure("F1", 1, export_path="/tmp/fig1.png", caption_text="Figure 1: Existing")
        with patch("os.path.exists", return_value=True):
            count = cm._enhance_captions_with_vision([fig])
        assert count == 1
        assert fig.metadata["caption_source"] == "manual_with_vision"
        assert fig.caption_text == "Figure 1: Existing"

    def test_enhance_captions_empty_caption(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        cm = CaptionMatcher()
        mock_client = MagicMock()
        mock_client.analyze_figure.return_value = "Some chart"
        cm.vision_client = mock_client
        fig = _make_figure("F1", 1, export_path="/tmp/fig1.png", caption_text="")
        with patch("os.path.exists", return_value=True):
            count = cm._enhance_captions_with_vision([fig])
        assert count == 1
        assert "vision_generated" in fig.metadata.get("caption_source", "")

    def test_link_figures_convenience(self):
        from app.pipeline.figures.caption_matcher import link_figures
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        result = link_figures(doc, enable_vision=False)
        assert result is doc

    def test_link_figures_vision_default(self):
        from app.pipeline.figures.caption_matcher import link_figures
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        result = link_figures(doc)
        assert result is doc
