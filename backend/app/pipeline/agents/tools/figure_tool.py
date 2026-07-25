# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Figure analysis tool for detecting and analyzing figures in documents.
"""
import sys
from typing import Optional, Type
from pydantic import BaseModel, Field

if sys.version_info < (3, 14):
    try:
        from langchain.tools import BaseTool as _LangChainBaseTool
    except Exception:
        _LangChainBaseTool = object
else:
    _LangChainBaseTool = object

BaseTool = _LangChainBaseTool if isinstance(_LangChainBaseTool, type) else object


class FigureToolInput(BaseModel):
    """Input schema for figure analysis tool."""
    file_path: str = Field(description="Path to the document file to analyze figures")


class FigureAnalysisTool(BaseTool):
    """
    Tool for detecting and analyzing figures in academic documents.

    Uses LLM-based layout analysis (preferred) or Docling as fallback.
    """
    name: str = "analyze_figures"
    description: str = (
        "Detect and analyze figures in a document. "
        "Returns information about figure count, captions, positions, and quality. "
        "Use this when you need to understand the visual content and "
        "ensure proper figure formatting."
    )
    args_schema: Type[BaseModel] = FigureToolInput

    def __init__(self):
        super().__init__()
        self._layout_analyzer = None

    def _get_layout_analyzer(self):
        if self._layout_analyzer is not None:
            return self._layout_analyzer
        try:
            from app.pipeline.parsing.llm_pdf_parser import LLMPDFParser
            self._layout_analyzer = LLMPDFParser()
            return self._layout_analyzer
        except Exception:
            pass
        try:
            from app.pipeline.services.docling_client import DoclingClient
            self._layout_analyzer = DoclingClient()
            return self._layout_analyzer
        except Exception:
            self._layout_analyzer = False
            return None

    def _run(self, file_path: str) -> str:
        try:
            analyzer = self._get_layout_analyzer()
            if analyzer is None:
                return "ERROR: No layout analyzer available (install LLM provider or Docling)."

            layout_data = analyzer.analyze_layout(file_path)

            if not layout_data:
                return "ERROR: Failed to analyze document for figures."

            elements = layout_data.get("elements", [])
            figures = []
            for elem in elements:
                if elem.get("type") in ("figure", "image", "picture"):
                    figure_info = {
                        "caption": elem.get("text", "No caption"),
                        "type": elem.get("type"),
                        "page": elem.get("page", 0),
                        "has_caption": bool(elem.get("text")),
                    }
                    figures.append(figure_info)

            quality_issues = []
            for idx, fig in enumerate(figures, 1):
                if not fig["has_caption"]:
                    quality_issues.append(f"Figure {idx} missing caption")

            result = {
                "status": "success",
                "figures": {
                    "total_count": len(figures),
                    "with_captions": sum(1 for f in figures if f["has_caption"]),
                    "quality_issues": quality_issues,
                    "figures": figures[:10],
                },
            }

            import json
            return json.dumps(result, indent=2)

        except Exception as e:
            return f"ERROR: Figure analysis failed: {str(e)}"

    async def _arun(self, file_path: str) -> str:
        raise NotImplementedError("Async execution not supported yet")
