import pytest
from unittest.mock import MagicMock, patch


def _make_block(text="Some text", block_type="BODY", index=0,
                block_id="b1", is_heading=False, section_name=None):
    block = MagicMock()
    block.text = text
    block.block_type = block_type
    block.index = index
    block.block_id = block_id
    block.is_heading.return_value = is_heading
    block.section_name = section_name
    block.metadata = {}
    return block


def _make_figure(figure_id="f1", export_path=None, caption_text="",
                 block_index=0):
    fig = MagicMock()
    fig.figure_id = figure_id
    fig.export_path = export_path
    fig.caption_text = caption_text
    fig.caption_block_id = None
    fig.metadata = {"block_index": block_index}
    return fig


class TestFindCaptionCandidates:
    def test_finds_caption(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher()
        blocks = [_make_block("Figure 1: Test", index=0)]
        candidates = matcher._find_caption_candidates(blocks)
        assert candidates == [0]

    def test_skips_headings(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher()
        blocks = [_make_block("Figure 1: Analysis", index=0, is_heading=True)]
        candidates = matcher._find_caption_candidates(blocks)
        assert candidates == []

    def test_skips_non_matching(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher()
        blocks = [_make_block("Just some text", index=0)]
        candidates = matcher._find_caption_candidates(blocks)
        assert candidates == []

    def test_matches_variations(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher()
        blocks = [
            _make_block("Fig. 1: Caption", index=0),
            _make_block("Figure 2-a Caption", index=1),
        ]
        candidates = matcher._find_caption_candidates(blocks)
        assert len(candidates) == 2


class TestMatchCandidates:
    def test_basic_match(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher()
        blocks = [
            _make_block("", index=0),  # figure placeholder
            _make_block("Figure 1: Test", index=1),
        ]
        figures = [_make_figure(figure_id="f1", block_index=0)]
        matches = matcher._match_candidates(blocks, figures, [1])
        assert len(matches) == 1
        assert matches[0][0].figure_id == "f1"

    def test_too_far_apart(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher(max_distance=1)
        blocks = [_make_block("", index=i) for i in range(5)]
        blocks.append(_make_block("Figure 1: Caption", index=5))
        figures = [_make_figure(figure_id="f1", block_index=0)]
        matches = matcher._match_candidates(blocks, figures, [5])
        assert len(matches) == 0

    def test_no_figures(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher()
        blocks = [_make_block("Figure 1: Cap", index=0)]
        matches = matcher._match_candidates(blocks, [], [0])
        assert matches == []

    def test_skip_already_assigned(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher()
        blocks = [
            _make_block("", index=0),
            _make_block("Figure 1: First", index=1),
            _make_block("Figure 2: Second", index=2),
        ]
        figures = [
            _make_figure(figure_id="f1", block_index=0),
            _make_figure(figure_id="f2", block_index=0),
        ]
        matches = matcher._match_candidates(blocks, figures, [1, 2])
        assert len(matches) == 2

    def test_prefers_figure_above_caption(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        matcher = CaptionMatcher(max_distance=5)
        blocks = [
            _make_block("", index=0),
            _make_block("", index=2),
            _make_block("Figure 1: Cap", index=3),
        ]
        figures = [
            _make_figure(figure_id="f1", block_index=0),
            _make_figure(figure_id="f2", block_index=2),
        ]
        matches = matcher._match_candidates(blocks, figures, [3])
        assert matches[0][0].figure_id == "f2"


class FakeVisionClient:
    def analyze_figure(self, image_path=None, caption=None):
        return "AI generated description"


class TestProcess:
    def test_process_empty_document(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        matcher = CaptionMatcher()
        result = matcher.process(doc)
        assert result is doc

    def test_process_with_match(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        doc = MagicMock()
        doc.blocks = [
            _make_block("", index=0),
            _make_block("Figure 1: Cap", index=1),
        ]
        doc.figures = [_make_figure(figure_id="f1", block_index=0)]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        matcher = CaptionMatcher()
        result = matcher.process(doc)
        assert result.figures[0].caption_text == "Figure 1: Cap"

    def test_process_exception_handling(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        doc = MagicMock()
        doc.blocks = [_make_block("Figure 1: Cap", index=0)]
        doc.figures = [_make_figure(figure_id="f1")]
        doc.add_processing_stage = MagicMock()
        doc.figures[0].metadata = {}  # no block_index

        matcher = CaptionMatcher()
        result = matcher.process(doc)
        assert result is doc

    def test_vision_enhancement(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        doc = MagicMock()
        doc.blocks = [
            _make_block("", index=0),
            _make_block("Figure 1: Test", index=1),
        ]
        doc.figures = [_make_figure(figure_id="f1", block_index=0, export_path="/tmp/fig.png")]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        with patch("os.path.exists", return_value=True):
            matcher = CaptionMatcher(enable_vision=True)
            matcher.vision_client = FakeVisionClient()
            result = matcher.process(doc)
        assert result.figures[0].metadata["vision_analysis"] == "AI generated description"

    def test_vision_generates_caption_when_missing(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        doc = MagicMock()
        doc.blocks = [
            _make_block("", index=0),
            _make_block("", index=1),
        ]
        doc.figures = [_make_figure(figure_id="f1", block_index=0, export_path="/tmp/fig.png")]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        with patch("os.path.exists", return_value=True):
            matcher = CaptionMatcher(enable_vision=True)
            matcher.vision_client = FakeVisionClient()
            result = matcher.process(doc)
        assert "vision_generated" in str(result.figures[0].metadata.get("caption_source", ""))

    def test_vision_skipped_when_no_path(self):
        from app.pipeline.figures.caption_matcher import CaptionMatcher
        doc = MagicMock()
        doc.blocks = [
            _make_block("", index=0),
            _make_block("Figure 1: Cap", index=1),
        ]
        doc.figures = [_make_figure(figure_id="f1", block_index=0, export_path=None)]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        matcher = CaptionMatcher(enable_vision=True)
        matcher.vision_client = FakeVisionClient()
        result = matcher.process(doc)
        assert "vision_analysis" not in result.figures[0].metadata


class TestLinkFigures:
    def test_convenience_function(self):
        from app.pipeline.figures.caption_matcher import link_figures
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        result = link_figures(doc, enable_vision=False)
        assert result is doc
