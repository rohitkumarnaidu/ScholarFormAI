# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Layout analysis tool using LLM (preferred) or Docling (fallback).
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


class LayoutToolInput(BaseModel):
    """Input schema for layout analysis tool."""

    file_path: str = Field(description="Path to the document file to analyze layout")


class LayoutAnalysisTool(BaseTool):
    """
    Tool for analyzing document layout using LLM (preferred) or Docling.

    Returns detailed information about text blocks, their positions,
    and hierarchical structure.
    """

    name: str = "analyze_layout"
    description: str = (
        "Analyze the layout and structure of a document. "
        "Returns detailed information about text blocks, their positions, font styles, "
        "and hierarchical structure. Use this when you need to understand "
        "the visual layout and formatting of the document."
    )
    args_schema: Type[BaseModel] = LayoutToolInput

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
                return "ERROR: Failed to analyze document layout."

            elements = layout_data.get("elements", [])
            headings = [
                e for e in elements if e.get("type", "").startswith("section_header") or e.get("type") == "heading"
            ]
            paragraphs = [e for e in elements if e.get("type") == "paragraph"]

            result = {
                "status": "success",
                "layout": {
                    "total_elements": len(elements),
                    "headings": len(headings),
                    "paragraphs": len(paragraphs),
                    "has_figures": any(e.get("type") in ("figure", "image") for e in elements),
                    "has_tables": any(e.get("type") == "table" for e in elements),
                    "structure": [
                        {
                            "type": e.get("type"),
                            "text_preview": (e.get("text", "") or "")[:100],
                            "level": e.get("level"),
                        }
                        for e in elements[:10]
                    ],
                },
            }

            import json

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"ERROR: Layout analysis failed: {str(e)}"

    async def _arun(self, file_path: str) -> str:
        """Async version - not implemented yet."""
        raise NotImplementedError("Async execution not supported yet")
