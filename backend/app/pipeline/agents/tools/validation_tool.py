# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Validation tool using AI-based analysis.
"""
import sys
from typing import Optional, Type
from pydantic import BaseModel, Field
from app.pipeline.validation import DocumentValidator
from app.models import PipelineDocument

if sys.version_info < (3, 14):
    try:
        from langchain.tools import BaseTool as _LangChainBaseTool
    except Exception:
        _LangChainBaseTool = object
else:
    _LangChainBaseTool = object

BaseTool = _LangChainBaseTool if isinstance(_LangChainBaseTool, type) else object


class ValidationToolInput(BaseModel):
    """Input schema for validation tool."""
    document_id: str = Field(description="ID of the document to validate")


class ValidationTool(BaseTool):
    """
    Tool for validating document structure and metadata.
    
    This tool wraps the DocumentValidator to check document quality,
    completeness, and academic formatting compliance.
    """
    name: str = "validate_document"
    description: str = (
        "Validate the structure, metadata, and formatting of a document. "
        "Returns validation results including errors, warnings, and confidence scores. "
        "Use this to ensure the document meets academic standards and is properly formatted."
    )
    args_schema: Type[BaseModel] = ValidationToolInput
    
    def __init__(self):
        super().__init__()
        object.__setattr__(self, "validator", DocumentValidator())
        object.__setattr__(self, "_document_cache", {})  # Simple cache for demo purposes
    
    def set_document(self, doc_id: str, document: PipelineDocument):
        """Cache a document for validation."""
        self._document_cache[doc_id] = document
    
    def _run(self, document_id: str) -> str:
        """
        Execute document validation.
        
        Args:
            document_id: ID of the document to validate
            
        Returns:
            JSON string containing validation results
        """
        try:
            # Retrieve document from cache
            document = self._document_cache.get(document_id)
            
            if not document:
                return f"ERROR: Document with ID '{document_id}' not found in cache."
            
            # Validate document
            validation_result = self.validator.validate(document)
            is_valid = getattr(validation_result, "is_valid", getattr(document, "is_valid", False))
            errors = list(getattr(validation_result, "errors", getattr(document, "validation_errors", [])))
            warnings = list(getattr(validation_result, "warnings", getattr(document, "validation_warnings", [])))
            
            # Format response
            result = {
                "status": "success",
                "validation": {
                    "is_valid": is_valid,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "errors": errors[:5],  # First 5 errors
                    "warnings": warnings[:5],  # First 5 warnings
                    "metadata_quality": {
                        "has_title": bool(document.metadata.title),
                        "has_authors": len(document.metadata.authors) > 0,
                        "has_abstract": bool(document.metadata.abstract),
                        "reference_count": len(document.references)
                    }
                }
            }
            
            import json
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"ERROR: Validation failed: {str(e)}"
    
    async def _arun(self, document_id: str) -> str:
        """Async version - not implemented yet."""
        raise NotImplementedError("Async execution not supported yet")
