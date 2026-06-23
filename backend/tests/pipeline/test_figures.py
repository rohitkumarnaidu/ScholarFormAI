# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Test suite for figures pipeline: analyzer and caption matcher.
"""

from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock
import os
import pytest
from app.pipeline.figures.caption_matcher import CaptionMatcher, link_figures
from app.pipeline.figures.analyzer import FigureAnalyzer
from app.models import PipelineDocument, Block, BlockType, Figure


# ===================================================================
# CAPTION MATCHER TESTS
# ===================================================================

class TestCaptionMatcher:
    @pytest.fixture
    def matcher(self):
        return CaptionMatcher()

    def test_process_empty_document(self, matcher):
        doc = PipelineDocument(document_id="t", blocks=[])
        result = matcher.process(doc)
        assert result is doc

    def test_process_no_figures_returns_early(self, matcher):
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=1, text="As shown in Figure 1.", block_type=BlockType.BODY),
        ])
        result = matcher.process(doc)
        assert result is doc

    def test_process_with_figures_and_captions(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. Experimental results.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Some body text.", block_type=BlockType.BODY),
                Block(block_id="b3", index=2, text="Figure 2. Training loss curve.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f1", index=0, metadata={"block_index": 0}),
                Figure(figure_id="f2", index=1, metadata={"block_index": 2}),
            ],
        )
        result = matcher.process(doc)
        # Each figure should be matched to its caption
        assert result.figures[0].caption_text is not None
        assert result.figures[1].caption_text is not None

    def test_adds_stage_info(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Figure 1. Testing.", block_type=BlockType.BODY)],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        result = matcher.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "figure_linking" in stages

    def test_vision_client_disabled_by_default(self, matcher):
        assert matcher.vision_client is None

    def test_vision_enhance_skipped_when_client_none(self, matcher):
        matcher.vision_client = None
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY)],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        result = matcher.process(doc)
        assert result is doc

    def test_caption_pattern_matching(self, matcher):
        """Various valid caption forms should be matched."""
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. System diagram.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Fig. 2: Architecture overview.", block_type=BlockType.BODY),
                Block(block_id="b3", index=2, text="Fig 3. Data flow.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f1", index=0, metadata={"block_index": 0}),
                Figure(figure_id="f2", index=1, metadata={"block_index": 1}),
                Figure(figure_id="f3", index=2, metadata={"block_index": 2}),
            ],
        )
        result = matcher.process(doc)
        assert result.figures[0].caption_text == "Figure 1. System diagram."
        assert result.figures[1].caption_text == "Fig. 2: Architecture overview."
        assert result.figures[2].caption_text == "Fig 3. Data flow."

    def test_headings_excluded_from_captions(self, matcher):
        """Heading blocks with figure-like text should NOT be matched."""
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. The Problem", block_type=BlockType.HEADING_1),
                Block(block_id="b2", index=1, text="Body text.", block_type=BlockType.BODY),
            ],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 1})],
        )
        result = matcher.process(doc)
        assert result.figures[0].caption_text is None

    def test_max_distance_respected(self, matcher):
        """Figures too far from a caption should NOT be matched."""
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Intro.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="More text.", block_type=BlockType.BODY),
                Block(block_id="b3", index=2, text="Even more.", block_type=BlockType.BODY),
                Block(block_id="b4", index=3, text="Figure 1. Far caption.", block_type=BlockType.BODY),
            ],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        # max_distance=1, but distance=3 -> no match
        tight_matcher = CaptionMatcher(max_distance=1)
        result = tight_matcher.process(doc)
        assert result.figures[0].caption_text is None

    def test_tie_breaker_prefers_figure_above_caption(self, matcher):
        """When two figures are equally distant, prefer the one above the caption."""
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Some text.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Figure 1. The caption.", block_type=BlockType.BODY),
                Block(block_id="b3", index=2, text="Some text.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f_above", index=0, metadata={"block_index": 0}),
                Figure(figure_id="f_below", index=1, metadata={"block_index": 2}),
            ],
        )
        result = matcher.process(doc)
        # Both are distance=1 from caption at index=1
        # The one above (index=0) should win (distance > 0 in tie-breaker)
        matched = [f for f in result.figures if f.caption_text is not None]
        assert len(matched) == 1
        assert matched[0].figure_id == "f_above"

    def test_caption_block_metadata_updated(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. Matched.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
            ],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 1})],
        )
        result = matcher.process(doc)
        cap_block = result.blocks[0]
        assert cap_block.metadata.get("is_figure_caption") is True
        assert cap_block.metadata.get("linked_figure_id") == "f1"

    def test_link_figures_convenience_function(self):
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY)],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        result = link_figures(doc, enable_vision=False)
        assert result.figures[0].caption_text == "Figure 1. Test."

    def test_process_error_handling(self, matcher):
        """If process encounters an error, it returns the document with error stage."""
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY)],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        # Force an error in _find_caption_candidates
        with patch.object(matcher, '_find_caption_candidates', side_effect=Exception("boom")):
            result = matcher.process(doc)
            assert result is doc
            stages = [s for s in result.processing_history if s.stage_name == "figure_linking"]
            assert len(stages) == 1
            assert stages[0].status == "error"

    # -- vision enhancement tests -------------------------------------

    def test_vision_enhancement_generates_caption_when_missing(self, tmp_path):
        mock_vision = MagicMock()
        mock_vision.analyze_figure.return_value = "A bar chart showing quarterly revenue growth."
        matcher = CaptionMatcher()
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        img_path = tmp_path / "fig.png"
        img_path.write_text("fake")
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Some body text.", block_type=BlockType.BODY)],
            figures=[Figure(
                figure_id="f1", index=0, metadata={"block_index": 0},
                export_path=str(img_path),
            )],
        )
        result = matcher.process(doc)
        assert result.figures[0].metadata.get("vision_analysis") == "A bar chart showing quarterly revenue growth."

    def test_vision_enhancement_skipped_without_export_path(self):
        mock_vision = MagicMock()
        matcher = CaptionMatcher()
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Body text.", block_type=BlockType.BODY)],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        matcher.process(doc)
        mock_vision.analyze_figure.assert_not_called()

    def test_vision_enhancement_failure_does_not_crash(self):
        mock_vision = MagicMock()
        mock_vision.analyze_figure.side_effect = Exception("vision failed")
        matcher = CaptionMatcher()
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY)],
            figures=[Figure(
                figure_id="f1", index=0, metadata={"block_index": 0},
                export_path="/fake/path.png",
            )],
        )
        result = matcher.process(doc)
        assert result is doc


# ===================================================================
# FIGURE ANALYZER TESTS
# ===================================================================

class TestFigureAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return FigureAnalyzer()

    def test_analyze_valid_image(self, analyzer, temp_image):
        result = analyzer.analyze_image(temp_image)
        assert result["width"] == 800
        assert result["height"] == 600
        assert "aspect_ratio" in result
        assert result["format"] == "PNG"
        assert result["mode"] == "RGB"
        # Default DPI (72) may be below min_dpi threshold
        assert isinstance(result["valid"], bool)

    def test_analyze_low_resolution_image(self, analyzer, temp_image_low_res):
        result = analyzer.analyze_image(temp_image_low_res)
        assert result["valid"] is False
        assert result["width"] == 100
        assert result["height"] == 80
        assert len(result["issues"]) > 0
        assert any("Low resolution" in issue for issue in result["issues"])

    def test_analyze_nonexistent_file(self, analyzer):
        result = analyzer.analyze_image("/nonexistent/path.png")
        assert "error" in result
        assert result["path"] == "/nonexistent/path.png"

    def test_analyze_jpeg_format(self, analyzer, temp_jpeg_image):
        result = analyzer.analyze_image(temp_jpeg_image)
        assert result["format"] == "JPEG"
        assert result["width"] == 1024
        assert isinstance(result["valid"], bool)

    def test_aspect_ratio_calculation(self, analyzer):
        from PIL import Image
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            img = Image.new("RGB", (400, 200), color=(0, 0, 0))
            img.save(path)
            result = analyzer.analyze_image(path)
            assert result["aspect_ratio"] == 2.0
        finally:
            os.unlink(path)

    def test_custom_min_dimensions(self):
        analyzer = FigureAnalyzer(min_width=500, min_height=500, min_dpi=300)
        from PIL import Image
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            img = Image.new("RGB", (600, 400), color=(0, 0, 0))
            img.save(path)
            result = analyzer.analyze_image(path)
            assert result["valid"] is False
            assert any("Low resolution" in issue for issue in result["issues"])
        finally:
            os.unlink(path)

    # -- downsample tests --------------------------------------------

    def test_downsample_not_needed(self, analyzer, temp_image):
        result = analyzer.downsample_if_needed(temp_image, max_size_bytes=50_000_000)
        assert result == temp_image

    def test_downsample_returns_none_for_missing(self, analyzer):
        result = analyzer.downsample_if_needed("/nonexistent.png")
        assert result is None

    def test_downsample_creates_smaller_file(self, analyzer):
        """When file exceeds max_size, a downsampled copy is created."""
        from PIL import Image
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            # Create a large image
            img = Image.new("RGB", (2000, 2000), color=(128, 128, 128))
            img.save(path)
            original_size = os.path.getsize(path)

            # Very small max to force downsample
            result = analyzer.downsample_if_needed(path, max_size_bytes=1)
            assert result is not None
            assert result != path
            assert os.path.exists(result)
            assert "_downsampled" in result
            # Clean up the downsampled file
            os.unlink(result)
        finally:
            os.unlink(path)

    def test_downsample_error_returns_original(self, analyzer):
        """If downsampling fails, the original path is returned."""
        with patch("PIL.Image.open", side_effect=Exception("corrupt")):
            from PIL import Image
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                path = f.name
            try:
                img = Image.new("RGB", (100, 100))
                img.save(path)
                result = analyzer.downsample_if_needed(path, max_size_bytes=1)
                assert result == path
            finally:
                os.unlink(path)

    def test_analyze_corrupt_image(self, analyzer):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"not a real image file")
            path = f.name
        try:
            result = analyzer.analyze_image(path)
            assert "error" in result or result.get("valid") is False
        finally:
            os.unlink(path)
