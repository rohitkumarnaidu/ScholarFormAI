# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Layout analysis tool using Docling.
"""
import sys
from typing import Optional, Type
from pydantic import BaseModel, Field
from app.pipeline.services.docling_client import DoclingClient

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
    Tool for analyzing document layout using Docling.
    
    This tool wraps the DoclingClient to provide detailed layout analysis
    including bounding boxes, font styles, and structural elements.
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
        object.__setattr__(self, "docling_client", DoclingClient())
    
    def _run(self, file_path: str) -> str:
        """
        Execute layout analysis.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            JSON string containing layout analysis results
        """
        try:
            # Analyze layout
            layout_data = self.docling_client.analyze_layout(file_path)
            
            if not layout_data:
                return "ERROR: Failed to analyze document layout."
            
            # Extract key statistics
            blocks = layout_data.get("blocks", [])
            headings = [b for b in blocks if b.get("block_type", "").startswith("heading")]
            paragraphs = [b for b in blocks if b.get("block_type") == "paragraph"]
            
            # Format response
            result = {
                "status": "success",
                "layout": {
                    "total_blocks": len(blocks),
                    "headings": len(headings),
                    "paragraphs": len(paragraphs),
                    "has_figures": any(b.get("block_type") == "figure" for b in blocks),
                    "has_tables": any(b.get("block_type") == "table" for b in blocks),
                    "structure": [
                        {
                            "type": b.get("block_type"),
                            "text_preview": (b.get("text", "") or "")[:100],
                            "font_size": b.get("font_size"),
                            "position": b.get("bbox")
                        }
                        for b in blocks[:10]  # First 10 blocks for preview
                    ]
                }
            }
            
            import json
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"ERROR: Layout analysis failed: {str(e)}"
    
    async def _arun(self, file_path: str) -> str:
        """Async version - not implemented yet."""
        raise NotImplementedError("Async execution not supported yet")
