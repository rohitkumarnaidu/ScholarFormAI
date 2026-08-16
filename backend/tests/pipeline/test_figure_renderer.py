# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Test suite for FigureRenderer.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models import Figure
from app.pipeline.figures.renderer import FigureRenderer


class TestFigureAnalysisStage:
    """Tests for the orchestrator's _run_figure_analysis_stage integration."""

    @pytest.fixture
    def doc_with_figure(self, tmp_path):
        from PIL import Image

        from app.models import PipelineDocument

        img_path = tmp_path / "fig.png"
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        img.save(str(img_path), dpi=(300, 300))
        fig = Figure(figure_id="fig_001", index=0, export_path=str(img_path))
        doc = PipelineDocument(document_id="test", blocks=[])
        doc.figures = [fig]
        doc.metadata.ai_hints = {}
        return doc

    def test_skipped_in_fast_mode(self):
        from app.pipeline.orchestrator import _get_figure_analyzer

        analyzer = _get_figure_analyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "analyze_image")
        assert hasattr(analyzer, "downsample_if_needed")

    @patch("app.pipeline.orchestrator.stages._get_figure_analyzer")
    def test_run_figure_analysis_stage_adds_metadata(self, mock_get_analyzer, doc_with_figure):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {
            "valid": True,
            "width": 800,
            "height": 600,
            "dpi": "300x300",
            "format": "PNG",
            "mode": "RGB",
            "aspect_ratio": 1.33,
            "issues": [],
        }
        mock_analyzer.downsample_if_needed.return_value = None
        mock_get_analyzer.return_value = mock_analyzer
        from app.pipeline.orchestrator import PipelineOrchestrator

        orch = PipelineOrchestrator(templates_dir="app/templates")
        result = orch._run_figure_analysis_stage(doc_with_figure)
        hints = result.metadata.ai_hints
        assert "figure_analysis" in hints
        assert len(hints["figure_analysis"]) == 1
        analysis = hints["figure_analysis"][0]
        assert analysis["figure_id"] == "fig_001"
        assert analysis["width"] == 800
        assert analysis["height"] == 600

    @patch("app.pipeline.orchestrator.stages._get_figure_analyzer")
    def test_run_figure_analysis_stage_figure_missing_path(self, mock_get_analyzer):
        mock_analyzer = MagicMock()
        mock_get_analyzer.return_value = mock_analyzer
        from app.models import PipelineDocument

        doc = PipelineDocument(document_id="test", blocks=[])
        doc.figures = [Figure(figure_id="fig_no_path", index=0, export_path=None)]
        doc.metadata.ai_hints = {}
        from app.pipeline.orchestrator import PipelineOrchestrator

        orch = PipelineOrchestrator(templates_dir="app/templates")
        result = orch._run_figure_analysis_stage(doc)
        hints = result.metadata.ai_hints
        assert "figure_analysis" in hints
        assert hints["figure_analysis"][0]["valid"] is False
        assert hints["figure_analysis"][0].get("error") == "No export path"

    def test_run_figure_analysis_stage_empty_figures(self):
        from app.models import PipelineDocument

        doc = PipelineDocument(document_id="test", blocks=[])
        doc.figures = []
        doc.metadata.ai_hints = {}
        from app.pipeline.orchestrator import PipelineOrchestrator

        orch = PipelineOrchestrator(templates_dir="app/templates")
        result = orch._run_figure_analysis_stage(doc)
        assert "figure_analysis" not in (result.metadata.ai_hints or {})


class TestFigureRenderer:
    @pytest.fixture
    def renderer(self):
        return FigureRenderer()

    def test_calculate_image_size_with_dimensions(self, renderer):
        fig = Figure(figure_id="f1", index=0, width=960, height=540)
        w, h = renderer.calculate_image_size(fig)
        assert w.inches > 0
        assert h.inches > 0
        assert abs(w.inches / h.inches - 960 / 540) < 0.01

    def test_calculate_image_size_without_dimensions(self, renderer):
        fig = Figure(figure_id="f1", index=0)
        w, h = renderer.calculate_image_size(fig)
        assert w.inches == 5.0
        assert h is None

    def test_render_placeholder_when_no_data(self, renderer):
        doc = MagicMock()
        fig = Figure(figure_id="f1", index=0)
        renderer.render(doc, fig, 1)
        doc.add_paragraph.assert_called_with("[Figure 1 Placeholder - No image data]")

    def test_render_with_export_path(self, renderer, tmp_path):
        img_path = tmp_path / "fig.png"
        img_path.write_bytes(b"fake")
        fig = Figure(figure_id="f1", index=0, export_path=str(img_path))
        doc = MagicMock()
        renderer.render(doc, fig, 1)
        paragraph = doc.add_paragraph.return_value
        paragraph.add_run.assert_called()

    def test_render_export_path_fallback(self, renderer):
        fig = Figure(figure_id="f1", index=0, export_path="/nonexistent.png")
        doc = MagicMock()
        with patch("os.path.exists", return_value=True):
            paragraph = MagicMock()
            doc.add_paragraph.return_value = paragraph
            run = MagicMock()
            paragraph.add_run.return_value = run
            run.add_picture.side_effect = Exception("corrupt")
            renderer.render(doc, fig, 1)
            doc.add_paragraph.assert_called()

    def test_render_with_image_data(self, renderer):
        fig = Figure(figure_id="f1", index=0, image_data=b"fake_image_bytes")
        fig.width = 640
        fig.height = 480
        doc = MagicMock()
        renderer.render(doc, fig, 1)
        paragraph = doc.add_paragraph.return_value
        paragraph.add_run.assert_called()

    def test_render_image_data_fallback(self, renderer):
        fig = Figure(figure_id="f1", index=0, image_data=b"bad")
        fig.width = 100
        fig.height = 100
        doc = MagicMock()
        paragraph = MagicMock()
        doc.add_paragraph.return_value = paragraph
        run = MagicMock()
        paragraph.add_run.return_value = run
        run.add_picture.side_effect = Exception("corrupt image")
        renderer.render(doc, fig, 1)
        calls = [c for c in doc.add_paragraph.call_args_list if "failed" in str(c)]
        assert len(calls) >= 1

    def test_caption_added_with_number_prefix(self, renderer):
        doc = MagicMock()
        fig = Figure(figure_id="f1", index=0, caption_text="Experimental results.")
        renderer.render(doc, fig, 1)
        cap_calls = [c for c in doc.add_paragraph.call_args_list if "Caption" in str(c)]
        assert len(cap_calls) >= 1

    def test_caption_with_existing_prefix(self, renderer):
        doc = MagicMock()
        fig = Figure(figure_id="f1", index=0, caption_text="Figure 1: Accuracy over epochs.")
        renderer.render(doc, fig, 1)
        cap_para = doc.add_paragraph.return_value
        cap_para.add_run.assert_called()

    def test_caption_not_added_when_missing(self, renderer):
        doc = MagicMock()
        fig = Figure(figure_id="f1", index=0)
        renderer.render(doc, fig, 1)
        with_caption_style = [
            c
            for c in doc.add_paragraph.call_args_list
            if c[1].get("style") == "Caption" or (c[0] and "Caption" in str(c[0]))
        ]
        assert len(with_caption_style) == 0
