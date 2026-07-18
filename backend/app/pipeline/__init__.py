# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Pipeline package - All document processing stages.

Backward-compatible re-exports:
  PipelineOrchestrator is imported from the orchestrator sub-package so that
  existing callers (``from app.pipeline import PipelineOrchestrator``) continue
  to work after the god-class decomposition.
"""

from app.pipeline.figures import CaptionMatcher, FigureAnalyzer, FigureRenderer, figure_analyzer, link_figures
from app.pipeline.tables import TableCaptionMatcher, TableExtractor, TableRenderer, match_table_captions
from app.pipeline.orchestrator.orchestrator import PipelineOrchestrator

__all__ = [
    "CaptionMatcher", "link_figures", "FigureAnalyzer", "figure_analyzer", "FigureRenderer",
    "TableCaptionMatcher", "TableExtractor", "TableRenderer", "match_table_captions",
    "PipelineOrchestrator",
]
