# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
import os
from unittest.mock import patch, MagicMock
import pytest


class TestFigureAnalyzer:
    def test_init_defaults(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        assert fa.min_width == 300
        assert fa.min_height == 300
        assert fa.min_dpi == 150

    def test_init_custom(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer(min_width=500, min_height=400, min_dpi=200)
        assert fa.min_width == 500
        assert fa.min_height == 400
        assert fa.min_dpi == 200

    def test_downsample_file_not_found(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        with patch("os.path.exists", return_value=False):
            assert fa.downsample_if_needed("/nonexistent.png") is None

    def test_downsample_under_max_size(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=100_000),
        ):
            assert fa.downsample_if_needed("/tmp/img.png") == "/tmp/img.png"

    def test_downsample_success(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        mock_img = MagicMock()
        mock_img.__enter__.return_value = mock_img
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=5_000_000),
            patch("app.pipeline.figures.analyzer.Image.open", return_value=mock_img),
        ):
            result = fa.downsample_if_needed("/tmp/img.png")
            assert result is not None
            assert "_downsampled" in result
            mock_img.thumbnail.assert_called_once()
            mock_img.save.assert_called_once()

    def test_downsample_exception(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=5_000_000),
            patch("app.pipeline.figures.analyzer.Image.open", side_effect=Exception("corrupt")),
        ):
            result = fa.downsample_if_needed("/tmp/img.png")
            assert result == "/tmp/img.png"

    def test_analyze_file_not_found(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        with patch("os.path.exists", return_value=False):
            result = fa.analyze_image("/nonexistent.png")
            assert result["error"] == "File not found"

    def test_analyze_success(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        mock_img = MagicMock()
        mock_img.__enter__.return_value = mock_img
        mock_img.size = (800, 600)
        mock_img.format = "PNG"
        mock_img.mode = "RGB"
        mock_img.info = {"dpi": (300, 300)}
        with (
            patch("os.path.exists", return_value=True),
            patch("app.pipeline.figures.analyzer.Image.open", return_value=mock_img),
        ):
            result = fa.analyze_image("/tmp/img.png")
            assert result["valid"] is True
            assert result["width"] == 800
            assert result["height"] == 600
            assert result["format"] == "PNG"

    def test_analyze_low_resolution(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer(min_width=500, min_height=500)
        mock_img = MagicMock()
        mock_img.__enter__.return_value = mock_img
        mock_img.size = (100, 100)
        mock_img.format = "PNG"
        mock_img.mode = "RGB"
        mock_img.info = {"dpi": (300, 300)}
        with (
            patch("os.path.exists", return_value=True),
            patch("app.pipeline.figures.analyzer.Image.open", return_value=mock_img),
        ):
            result = fa.analyze_image("/tmp/img.png")
            assert result["valid"] is False
            assert len(result["issues"]) > 0

    def test_analyze_low_dpi(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer(min_dpi=300)
        mock_img = MagicMock()
        mock_img.__enter__.return_value = mock_img
        mock_img.size = (800, 600)
        mock_img.format = "PNG"
        mock_img.mode = "RGB"
        mock_img.info = {"dpi": (72, 72)}
        with (
            patch("os.path.exists", return_value=True),
            patch("app.pipeline.figures.analyzer.Image.open", return_value=mock_img),
        ):
            result = fa.analyze_image("/tmp/img.png")
            assert result["valid"] is False
            assert any("DPI" in i for i in result["issues"])

    def test_analyze_dpi_as_single_value(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        mock_img = MagicMock()
        mock_img.__enter__.return_value = mock_img
        mock_img.size = (800, 600)
        mock_img.format = "PNG"
        mock_img.mode = "RGB"
        mock_img.info = {"dpi": 150}
        with (
            patch("os.path.exists", return_value=True),
            patch("app.pipeline.figures.analyzer.Image.open", return_value=mock_img),
        ):
            result = fa.analyze_image("/tmp/img.png")
            assert "dpi" in result

    def test_analyze_exception(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        fa = FigureAnalyzer()
        with (
            patch("os.path.exists", return_value=True),
            patch("app.pipeline.figures.analyzer.Image.open", side_effect=Exception("corrupt")),
        ):
            result = fa.analyze_image("/tmp/img.png")
            assert "error" in result
            assert "corrupt" in result["error"]
