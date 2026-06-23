# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Metadata extraction tool using GROBID.
"""
import sys
from typing import Optional, Type
from pydantic import BaseModel, Field
from app.pipeline.services.grobid_client import GROBIDClient

if sys.version_info < (3, 14):
    try:
        from langchain.tools import BaseTool as _LangChainBaseTool
    except Exception:
        _LangChainBaseTool = object
else:
    _LangChainBaseTool = object

BaseTool = _LangChainBaseTool if isinstance(_LangChainBaseTool, type) else object


class MetadataToolInput(BaseModel):
    """Input schema for metadata extraction tool."""
    file_path: str = Field(description="Path to the PDF file to extract metadata from")


class MetadataExtractionTool(BaseTool):
    """
    Tool for extracting metadata from academic PDFs using GROBID.
    
    This tool wraps the GROBIDClient to provide structured metadata extraction
    including title, authors, abstract, and references.
    """
    name: str = "extract_metadata"
    description: str = (
        "Extract metadata from an academic PDF document. "
        "Returns structured information including title, authors, abstract, affiliations, "
        "publication date, and references. Use this when you need to understand "
        "the document's bibliographic information."
    )
    args_schema: Type[BaseModel] = MetadataToolInput
    
    def __init__(self, grobid_url: str = "http://localhost:8070"):
        super().__init__()
        object.__setattr__(self, "grobid_client", GROBIDClient(base_url=grobid_url))
    
    def _run(self, file_path: str) -> str:
        """
        Execute metadata extraction.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            JSON string containing extracted metadata
        """
        try:
            # Phase 3: Check Caching
            from app.cache.redis_cache import redis_cache
            import hashlib
            
            # Read file content for caching key when available.
            # In unit tests or remote file workflows, the local file may not exist.
            content = None
            try:
                with open(file_path, "rb") as f:
                    content = f.read().decode('utf-8', errors='ignore')
            except OSError:
                content = f"file_path:{file_path}"

            cached_metadata = redis_cache.get_grobid_result(content)
            if cached_metadata:
                import json
                return json.dumps(cached_metadata, indent=2)

            # Check GROBID availability
            if not self.grobid_client.is_available():
                return "ERROR: GROBID service is not available. Please ensure GROBID is running."
            
            # Extract metadata
            metadata = self.grobid_client.extract_metadata(file_path)
            
            if not metadata:
                return "ERROR: Failed to extract metadata from the document."
            
            # Format response
            result = {
                "status": "success",
                "metadata": {
                    "title": metadata.get("title", "Unknown"),
                    "authors": metadata.get("authors", []),
                    "abstract": metadata.get("abstract", ""),
                    "affiliations": metadata.get("affiliations", []),
                    "publication_date": metadata.get("publication_date", ""),
                    "doi": metadata.get("doi", ""),
                    "keywords": metadata.get("keywords", []),
                    "reference_count": len(metadata.get("references", []))
                }
            }
            
            # Cache the result (TTL 1 hour)
            redis_cache.set_grobid_result(content, result)
            
            import json
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"ERROR: Metadata extraction failed: {str(e)}"
    
    async def _arun(self, file_path: str) -> str:
        """Async version - not implemented yet."""
        raise NotImplementedError("Async execution not supported yet")
