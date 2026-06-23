# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Base Parser Interface - Abstract class for all document format parsers.

All format-specific parsers (DOCX, PDF, LaTeX, etc.) inherit from this base class
to ensure consistent interface across the pipeline.
"""

from abc import ABC, abstractmethod
from app.models import PipelineDocument as Document


class BaseParser(ABC):
    """Abstract base class for all document format parsers."""
    
    @abstractmethod
    def parse(self, file_path: str, document_id: str) -> Document:
        """
        Parse a document file into internal Document model.
        
        Args:
            file_path: Path to the input file
            document_id: Unique identifier for this document
        
        Returns:
            Document instance with extracted content
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this parser supports the given file extension.
        
        Args:
            file_extension: File extension (e.g., '.docx', '.pdf')
        
        Returns:
            True if this parser can handle the format, False otherwise
        """
        pass
