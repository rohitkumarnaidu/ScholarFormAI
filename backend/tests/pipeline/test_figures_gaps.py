# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Gap-filling tests for figures pipeline: analyzer and caption_matcher.
Targets 100% line coverage for each module.
"""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
import os
import importlib
import sys
import builtins
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from app.pipeline.figures.analyzer import FigureAnalyzer, figure_analyzer
from app.pipeline.figures.caption_matcher import CaptionMatcher, link_figures

# ===================================================================
# FIGURE ANALYZER — Lines 33-55, 67-106
# ===================================================================

class TestFigureAnalyzerGaps:
    """Covers all analyzer lines including downsample_if_needed and analyze_image."""

    @pytest.fixture
    def analyzer(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        return FigureAnalyzer()

    # -- downsample_if_needed (lines 33-55) --

    def test_downsample_file_not_found_returns_none(self, analyzer):
        """Line 33-34: file does not exist."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        result = analyzer.downsample_if_needed("/nonexistent/path.png")
        assert result is None

    def test_downsample_not_needed(self, analyzer, tmp_path):
        """Line 37-38: file size <= max_size_bytes."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "small.png"
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        img.save(str(path))
        result = analyzer.downsample_if_needed(str(path), max_size_bytes=50_000_000)
        assert result == str(path)

    def test_downsample_creates_downsampled(self, analyzer, tmp_path):
        """Lines 40-51: file exceeds max_size, thumbnail created."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "large.png"
        from PIL import Image
        img = Image.new("RGB", (2000, 2000), color=(128, 128, 128))
        img.save(str(path))
        result = analyzer.downsample_if_needed(str(path), max_size_bytes=1)
        assert result is not None
        assert result != str(path)
        assert "_downsampled" in result
        assert os.path.exists(result)
        os.unlink(result)

    def test_downsample_error_returns_original(self, analyzer, tmp_path):
        """Lines 52-55: exception during downsample returns original path."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "corrupt.png"
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        img.save(str(path))
        with patch("PIL.Image.open", side_effect=Exception("corrupt")):
            result = analyzer.downsample_if_needed(str(path), max_size_bytes=1)
            assert result == str(path)

    def test_downsample_with_jpeg(self, analyzer, tmp_path):
        """Save with JPEG extension."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "large.jpg"
        from PIL import Image
        img = Image.new("RGB", (2000, 2000), color=(128, 128, 128))
        img.save(str(path), "JPEG", quality=95)
        result = analyzer.downsample_if_needed(str(path), max_size_bytes=1)
        assert result is not None
        assert "_downsampled" in result
        if os.path.exists(result):
            os.unlink(result)

    # -- analyze_image (lines 67-106) --

    def test_analyze_file_not_found(self, analyzer):
        """Line 67-68: file does not exist."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        result = analyzer.analyze_image("/nonexistent/path.png")
        assert "error" in result
        assert result["path"] == "/nonexistent/path.png"

    def test_analyze_valid_image(self, analyzer, tmp_path):
        """Lines 70-103: normal analysis."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "test.png"
        from PIL import Image
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        img.save(str(path))
        result = analyzer.analyze_image(str(path))
        assert result["width"] == 800
        assert result["height"] == 600
        assert result["format"] == "PNG"
        assert result["mode"] == "RGB"
        assert "aspect_ratio" in result

    def test_analyze_low_resolution(self, analyzer, tmp_path):
        """Lines 86-87: width/height < min requirements."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "low.png"
        from PIL import Image
        img = Image.new("RGB", (100, 80), color=(0, 0, 0))
        img.save(str(path))
        result = analyzer.analyze_image(str(path))
        assert result["valid"] is False
        assert any("Low resolution" in issue for issue in result["issues"])

    def test_analyze_low_dpi(self, analyzer, tmp_path):
        """Lines 89-90: DPI below threshold."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "low_dpi.png"
        from PIL import Image
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        img.save(str(path), dpi=(72, 72))
        analyzer_with_dpi = FigureAnalyzer(min_width=100, min_height=100, min_dpi=200)
        result = analyzer_with_dpi.analyze_image(str(path))
        assert result["valid"] is False
        assert any("Low DPI" in issue for issue in result["issues"])

    def test_analyze_aspect_ratio(self, analyzer, tmp_path):
        """Line 92: aspect ratio calculation."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "ratio.png"
        from PIL import Image
        img = Image.new("RGB", (400, 200))
        img.save(str(path))
        result = analyzer.analyze_image(str(path))
        assert result["aspect_ratio"] == 2.0

    def test_analyze_dpi_as_tuple(self, analyzer, tmp_path):
        """Lines 77-81: dpi as tuple vs scalar."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "dpi_tuple.png"
        from PIL import Image
        img = Image.new("RGB", (800, 600))
        img.save(str(path), dpi=(150, 150))
        result = analyzer.analyze_image(str(path))
        assert "dpi" in result

    def test_analyze_dpi_as_number(self, analyzer, tmp_path):
        """Line 81: dpi as scalar (not tuple)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "dpi_scalar.png"
        from PIL import Image
        img = Image.new("RGB", (800, 600))
        img.save(str(path))
        result = analyzer.analyze_image(str(path))
        assert "dpi" in result

    def test_analyze_dpi_default_72(self, analyzer, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "dpi_default.png"
        from PIL import Image
        img = Image.new("RGB", (800, 600))
        img.save(str(path))
        result = analyzer.analyze_image(str(path))
        assert result["dpi"] is not None

    def test_analyze_corrupt_image(self, analyzer, tmp_path):
        """Line 105-106: exception during analyze."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "corrupt.png"
        with open(str(path), "wb") as f:
            f.write(b"not a real image")
        result = analyzer.analyze_image(str(path))
        assert "error" in result

    def test_analyze_image_exception_on_open(self, analyzer, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "missing.png"
        with patch("PIL.Image.open", side_effect=Exception("corrupt")):
            with patch("os.path.exists", return_value=True):
                result = analyzer.analyze_image(str(path))
                assert "error" in result

    def test_analyze_image_scalar_dpi_low(self, analyzer, tmp_path):
        """When dpi is a scalar (int), not a tuple."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "dpi_int.png"
        from PIL import Image
        img = Image.new("RGB", (800, 600))
        img.save(str(path))
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (800, 600)
            mock_img.format = "PNG"
            mock_img.mode = "RGB"
            mock_img.info = {"dpi": 72}
            mock_open.return_value.__enter__.return_value = mock_img
            result = analyzer.analyze_image(str(path))
            assert "dpi" in result

    def test_analyze_no_issues(self, analyzer, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, Figure
        path = tmp_path / "good.png"
        from PIL import Image
        img = Image.new("RGB", (1000, 1000))
        img.save(str(path), dpi=(300, 300))
        analyzer_hq = FigureAnalyzer(min_width=100, min_height=100, min_dpi=72)
        result = analyzer_hq.analyze_image(str(path))
        assert result["valid"] is True
        assert len(result["issues"]) == 0

    # -- figure_analyzer global instance (line 109) --

    def test_figure_analyzer_global_instance(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        assert isinstance(figure_analyzer, FigureAnalyzer)
        assert figure_analyzer.min_width == 300
        assert figure_analyzer.min_height == 300
        assert figure_analyzer.min_dpi == 150

# ===================================================================
# FIGURE CAPTION MATCHER — Lines 44-64, 70-128, 140-174, 180-190, 199-249, 253-254
# ===================================================================

class TestCaptionMatcherGaps:
    """Covers all caption_matcher lines."""

    @pytest.fixture
    def matcher(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        return CaptionMatcher()

    # -- __init__ (lines 44-64) --

    def test_init_defaults(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        matcher = CaptionMatcher()
        assert matcher.max_distance == 2
        assert matcher.enable_vision is False
        assert matcher.vision_client is None
        assert matcher.caption_pattern is not None

    def test_init_custom(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        matcher = CaptionMatcher(max_distance=5, enable_vision=True)
        assert matcher.max_distance == 5
        assert matcher.enable_vision is True

    def test_init_vision_enabled_success(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_client = MagicMock()
        with patch("app.services.nvidia_client.get_nvidia_client",
                   return_value=mock_client):
            matcher = CaptionMatcher(enable_vision=True)
            assert matcher.vision_client is mock_client

    def test_init_vision_enabled_failure(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        with patch("app.services.nvidia_client.get_nvidia_client",
                   side_effect=Exception("no client")):
            matcher = CaptionMatcher(enable_vision=True)
            assert matcher.vision_client is None

    def test_caption_pattern_matches(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        assert matcher.caption_pattern.match("Figure 1.")
        assert matcher.caption_pattern.match("Fig. 2:")
        assert matcher.caption_pattern.match("Fig 3-a")
        assert matcher.caption_pattern.match("Figure 10a")
        assert not matcher.caption_pattern.match("Table 1.")
        assert not matcher.caption_pattern.match("Introduction")

    # -- process (lines 70-128) --

    def test_process_no_figures_returns_early(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY),
        ])
        result = matcher.process(doc)
        assert result is doc

    def test_process_no_blocks_but_figures(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t", figures=[
            Figure(figure_id="f1", index=0),
        ])
        result = matcher.process(doc)
        assert result is doc

    def test_process_with_figures_and_captions(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. Results.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f1", index=0, metadata={"block_index": 1}),
            ],
        )
        result = matcher.process(doc)
        assert result.figures[0].caption_text == "Figure 1. Results."

    def test_process_with_exception(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f1", index=0, metadata={"block_index": 0}),
            ],
        )
        with patch.object(matcher, "_find_caption_candidates",
                          side_effect=Exception("boom")):
            result = matcher.process(doc)
            assert result is doc
            stages = [s for s in result.processing_history if s.stage_name == "figure_linking"]
            assert stages[0].status == "error"

    def test_process_success_stage_added(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f1", index=0, metadata={"block_index": 1}),
            ],
        )
        result = matcher.process(doc)
        stages = {s.stage_name: s.status for s in result.processing_history}
        assert stages.get("figure_linking") == "success"

    def test_process_vision_enhanced_count_in_message(self, matcher, tmp_path):
        """Vision-enhanced count included in success message (lines 115-117)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        mock_vision.analyze_figure.return_value = "A chart"
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        img_path = tmp_path / "fig.png"
        img_path.write_text("fake")
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f1", index=0, metadata={"block_index": 1},
                       export_path=str(img_path)),
            ],
        )
        result = matcher.process(doc)
        stage = next(s for s in result.processing_history if s.stage_name == "figure_linking")
        assert "enhanced" in stage.message

    def test_process_updates_updated_at(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
            ],
            figures=[
                Figure(figure_id="f1", index=0, metadata={"block_index": 1}),
            ],
        )
        original = doc.updated_at
        result = matcher.process(doc)
        assert result.updated_at >= original

    # -- _enhance_captions_with_vision (lines 140-174) --

    def test_enhance_skipped_no_export_path(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        matcher.vision_client = mock_vision
        matcher.enable_vision = True
        figures = [Figure(figure_id="f1", index=0)]
        result = matcher._enhance_captions_with_vision(figures)
        assert result == 0
        mock_vision.analyze_figure.assert_not_called()

    def test_enhance_skipped_export_path_not_exists(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        matcher.vision_client = mock_vision
        matcher.enable_vision = True
        figures = [Figure(figure_id="f1", index=0, export_path="/nonexistent/path.png")]
        result = matcher._enhance_captions_with_vision(figures)
        assert result == 0
        mock_vision.analyze_figure.assert_not_called()

    def test_enhance_generates_caption_when_missing(self, matcher, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        mock_vision.analyze_figure.return_value = "A bar chart showing revenue."
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        img_path = tmp_path / "fig.png"
        img_path.write_text("fake")
        figures = [Figure(figure_id="f1", index=0, export_path=str(img_path))]
        result = matcher._enhance_captions_with_vision(figures)
        assert result == 1
        assert figures[0].metadata.get("vision_analysis") == "A bar chart showing revenue."
        assert figures[0].metadata.get("caption_source") == "vision_generated"
        assert "Figure f1:" in figures[0].caption_text

    def test_enhance_with_existing_caption(self, matcher, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        mock_vision.analyze_figure.return_value = "Detailed analysis."
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        img_path = tmp_path / "fig.png"
        img_path.write_text("fake")
        figures = [Figure(figure_id="f1", index=0, export_path=str(img_path),
                          caption_text="Figure 1: Existing caption.")]
        result = matcher._enhance_captions_with_vision(figures)
        assert result == 1
        assert figures[0].metadata.get("caption_source") == "manual_with_vision"
        assert figures[0].caption_text == "Figure 1: Existing caption."

    def test_enhance_exception_does_not_crash(self, matcher, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        mock_vision.analyze_figure.side_effect = Exception("vision fail")
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        img_path = tmp_path / "fig.png"
        img_path.write_text("fake")
        figures = [Figure(figure_id="f1", index=0, export_path=str(img_path))]
        result = matcher._enhance_captions_with_vision(figures)
        assert result == 0

    def test_enhance_vision_returns_none(self, matcher, tmp_path):
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        mock_vision.analyze_figure.return_value = None
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        img_path = tmp_path / "fig.png"
        img_path.write_text("fake")
        figures = [Figure(figure_id="f1", index=0, export_path=str(img_path))]
        result = matcher._enhance_captions_with_vision(figures)
        assert result == 0

    def test_enhance_empty_caption_text_generates(self, matcher, tmp_path):
        """Empty string caption_text triggers vision generation (line 159)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        mock_vision = MagicMock()
        mock_vision.analyze_figure.return_value = "A diagram of architecture."
        matcher.vision_client = mock_vision
        matcher.enable_vision = True

        img_path = tmp_path / "fig.png"
        img_path.write_text("fake")
        figures = [Figure(figure_id="f1", index=0, export_path=str(img_path),
                          caption_text="")]
        result = matcher._enhance_captions_with_vision(figures)
        assert result == 1
        assert figures[0].metadata.get("caption_source") == "vision_generated"

    # -- _find_caption_candidates (lines 180-190) --

    def test_find_caption_candidates_body_blocks(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY),
            Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b3", index=2, text="Fig. 2: Another.", block_type=BlockType.BODY),
        ]
        result = matcher._find_caption_candidates(blocks)
        assert result == [0, 2]

    def test_find_caption_candidates_heading_skipped(self, matcher):
        """Heading blocks are skipped (line 184-185)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Analysis", block_type=BlockType.HEADING_1),
            Block(block_id="b2", index=1, text="Figure 2. Real caption.", block_type=BlockType.BODY),
        ]
        result = matcher._find_caption_candidates(blocks)
        assert result == [1]

    def test_find_caption_candidates_no_matches(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Introduction", block_type=BlockType.BODY),
        ]
        result = matcher._find_caption_candidates(blocks)
        assert result == []

    def test_find_caption_candidates_empty_blocks(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        result = matcher._find_caption_candidates([])
        assert result == []

    # -- _match_candidates (lines 199-249) --

    def test_match_candidates_basic(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Caption.", block_type=BlockType.BODY),
            Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
        ]
        figures = [Figure(figure_id="f1", index=0, metadata={"block_index": 1})]
        result = matcher._match_candidates(blocks, figures, [0])
        assert len(result) == 1
        assert result[0][0].figure_id == "f1"
        assert result[0][1].block_id == "b1"

    def test_match_candidates_already_assigned(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Cap1.", block_type=BlockType.BODY),
            Block(block_id="b2", index=1, text="Figure 2. Cap2.", block_type=BlockType.BODY),
            Block(block_id="b3", index=2, text="Body.", block_type=BlockType.BODY),
        ]
        figures = [
            Figure(figure_id="f1", index=0, metadata={"block_index": 0}),
            Figure(figure_id="f2", index=1, metadata={"block_index": 2}),
        ]
        result = matcher._match_candidates(blocks, figures, [0, 1])
        assert len(result) == 2
        assert result[0][0].figure_id == "f1"
        assert result[1][0].figure_id == "f2"

    def test_match_candidates_figure_no_block_index(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Cap.", block_type=BlockType.BODY),
        ]
        figures = [Figure(figure_id="f1", index=0)]
        result = matcher._match_candidates(blocks, figures, [0])
        assert len(result) == 0

    def test_match_candidates_figure_block_index_not_in_map(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Cap.", block_type=BlockType.BODY),
        ]
        figures = [Figure(figure_id="f1", index=0, metadata={"block_index": 99})]
        result = matcher._match_candidates(blocks, figures, [0])
        assert len(result) == 0

    def test_match_candidates_beyond_max_distance(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b2", index=1, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b3", index=2, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b4", index=3, text="Figure 1. Far.", block_type=BlockType.BODY),
        ]
        figures = [Figure(figure_id="f1", index=0, metadata={"block_index": 0})]
        tight = CaptionMatcher(max_distance=1)
        result = tight._match_candidates(blocks, figures, [3])
        assert len(result) == 0

    def test_match_candidates_tiebreaker_prefers_above(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Body above.", block_type=BlockType.BODY),
            Block(block_id="b2", index=1, text="Figure 1. Caption.", block_type=BlockType.BODY),
            Block(block_id="b3", index=2, text="Body below.", block_type=BlockType.BODY),
        ]
        figures = [
            Figure(figure_id="f_above", index=0, metadata={"block_index": 0}),
            Figure(figure_id="f_below", index=1, metadata={"block_index": 2}),
        ]
        result = matcher._match_candidates(blocks, figures, [1])
        assert len(result) == 1
        assert result[0][0].figure_id == "f_above"

    def test_match_candidates_tiebreaker_equal_distance_both_above(self, matcher):
        """When both above with same abs distance, first encountered wins."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b2", index=1, text="Figure 1. Cap.", block_type=BlockType.BODY),
            Block(block_id="b3", index=2, text="Body.", block_type=BlockType.BODY),
        ]
        figures = [
            Figure(figure_id="f1", index=0, metadata={"block_index": 0}),
            Figure(figure_id="f2", index=1, metadata={"block_index": 2}),
        ]
        result = matcher._match_candidates(blocks, figures, [1])
        assert len(result) == 1

    def test_match_candidates_no_caption_block_in_map(self, matcher):
        """Caption index not in block_map (line 214)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Cap.", block_type=BlockType.BODY),
        ]
        figures = [Figure(figure_id="f1", index=0, metadata={"block_index": 0})]
        result = matcher._match_candidates(blocks, figures, [99])
        assert len(result) == 0

    def test_match_candidates_no_caption_list_index(self, matcher):
        """Caption index not in list_index_map (line 214)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Cap.", block_type=BlockType.BODY),
        ]
        figures = [Figure(figure_id="f1", index=0, metadata={"block_index": 0})]
        with patch.object(matcher, "caption_pattern"):
            result = matcher._match_candidates(blocks, figures, [])
        assert len(result) == 0

    def test_match_candidates_figure_block_index_none(self, matcher):
        """figure.metadata block_index is None (line 227)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Figure 1. Cap.", block_type=BlockType.BODY),
        ]
        figures = [Figure(figure_id="f1", index=0, metadata={"block_index": None})]
        result = matcher._match_candidates(blocks, figures, [0])
        assert len(result) == 0

    def test_match_candidates_current_dist_less_than_min(self, matcher):
        """New figure is closer than current best (lines 237-238)."""
        from app.models import PipelineDocument, Block, BlockType, Figure
        blocks = [
            Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b2", index=1, text="Figure 1. Cap.", block_type=BlockType.BODY),
            Block(block_id="b3", index=2, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b4", index=3, text="Body.", block_type=BlockType.BODY),
        ]
        figures = [
            Figure(figure_id="f_far", index=0, metadata={"block_index": 0}),
            Figure(figure_id="f_near", index=1, metadata={"block_index": 2}),
        ]
        result = matcher._match_candidates(blocks, figures, [1])
        assert len(result) == 1
        # Tiebreaker prefers figure ABOVE caption (positive distance)
        assert result[0][0].figure_id == "f_far"

    # -- link_figures convenience (lines 253-254) --

    def test_link_figures_convenience(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Figure 1. Test.", block_type=BlockType.BODY)],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        result = link_figures(doc, enable_vision=False)
        assert result.figures[0].caption_text == "Figure 1. Test."

    def test_link_figures_with_vision(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY)],
            figures=[Figure(figure_id="f1", index=0, metadata={"block_index": 0})],
        )
        result = link_figures(doc, enable_vision=True)
        assert result is not None

# ===================================================================
# Global figure_analyzer instance coverage (line 109)
# ===================================================================

class TestFigureAnalyzerGlobalInstance:

    def test_global_instance_exists(self):
        from app.models import PipelineDocument, Block, BlockType, Figure
        from app.pipeline.figures.analyzer import figure_analyzer
        assert isinstance(figure_analyzer, FigureAnalyzer)
        assert figure_analyzer.min_width == 300
        assert figure_analyzer.min_height == 300
        assert figure_analyzer.min_dpi == 150
