# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Reference extraction tool using GROBID and reference parser.
"""

import sys

from pydantic import BaseModel, Field

from app.pipeline.references.parser import ReferenceParser
from app.pipeline.services.grobid_client import GROBIDClient

if sys.version_info < (3, 14):
    try:
        from langchain.tools import BaseTool as _LangChainBaseTool
    except Exception:
        _LangChainBaseTool = object
else:
    _LangChainBaseTool = object

BaseTool = _LangChainBaseTool if isinstance(_LangChainBaseTool, type) else object


class ReferenceToolInput(BaseModel):
    """Input schema for reference extraction tool."""

    file_path: str = Field(description="Path to the PDF file to extract references from")


class ReferenceExtractionTool(BaseTool):
    """
    Tool for extracting and parsing references from academic documents.

    This tool combines GROBID's reference extraction with our reference parser
    to provide structured, normalized reference data.
    """

    name: str = "extract_references"
    description: str = (
        "Extract and parse references from an academic document. "
        "Returns structured reference information including authors, titles, "
        "publication years, DOIs, and citation counts. Use this when you need "
        "to analyze the document's bibliography or validate citations."
    )
    args_schema: type[BaseModel] = ReferenceToolInput

    def __init__(self, grobid_url: str = "http://localhost:8070"):
        super().__init__()
        object.__setattr__(self, "grobid_client", GROBIDClient(base_url=grobid_url))
        object.__setattr__(self, "reference_parser", ReferenceParser())

    def _run(self, file_path: str) -> str:
        """
        Execute reference extraction.

        Args:
            file_path: Path to the PDF file

        Returns:
            JSON string containing extracted references
        """
        try:
            # Check GROBID availability
            if not self.grobid_client.is_available():
                return "ERROR: GROBID service is not available for reference extraction."

            # Extract metadata (includes references)
            metadata = self.grobid_client.extract_metadata(file_path)

            if not metadata or "references" not in metadata:
                return "ERROR: No references found in the document."

            raw_references = metadata.get("references", [])

            # Parse and normalize references
            parsed_refs = []
            for idx, ref in enumerate(raw_references[:20], 1):  # Limit to first 20
                parsed = {
                    "index": idx,
                    "raw_text": ref.get("raw_text", ""),
                    "title": ref.get("title", ""),
                    "authors": ref.get("authors", []),
                    "year": ref.get("year", ""),
                    "doi": ref.get("doi", ""),
                    "venue": ref.get("venue", ""),
                }
                parsed_refs.append(parsed)

            # Format response
            result = {
                "status": "success",
                "references": {
                    "total_count": len(raw_references),
                    "parsed_count": len(parsed_refs),
                    "has_dois": sum(1 for r in parsed_refs if r.get("doi")),
                    "references": parsed_refs,
                },
            }

            import json

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"ERROR: Reference extraction failed: {str(e)}"

    async def _arun(self, file_path: str) -> str:
        """Async version - not implemented yet."""
        raise NotImplementedError("Async execution not supported yet")
