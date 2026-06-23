# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Reference Model - Represents a bibliographic reference.

References are parsed and normalized by the references/ pipeline stage.
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ReferenceType(str, Enum):
    """Type of referenced work."""
    JOURNAL_ARTICLE = "journal_article"
    CONFERENCE_PAPER = "conference_paper"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    THESIS = "thesis"
    TECHNICAL_REPORT = "technical_report"
    PATENT = "patent"
    WEB_PAGE = "web_page"
    PREPRINT = "preprint"
    UNKNOWN = "unknown"


class CitationStyle(str, Enum):
    """Citation/reference formatting style."""
    IEEE = "ieee"
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    HARVARD = "harvard"
    VANCOUVER = "vancouver"
    SPRINGER = "springer"
    UNKNOWN = "unknown"


class Reference(BaseModel):
    """
    Represents a bibliographic reference.
    
    References are extracted from the reference section and parsed
    into structured fields. They are referenced by citation keys.
    """
    
    # Unique identifier
    reference_id: str = Field(
        ...,
        description="Unique identifier (e.g., 'ref_001')"
    )
    
    # Sequential numbering (assigned by formatting stage)
    number: Optional[int] = Field(
        default=None,
        description="Sequential reference number (e.g., 1 for '[1]')"
    )
    
    # Citation key (e.g., 'Smith2020', '[1]', 'Smi20')
    citation_key: str = Field(
        ...,
        description="Key used for in-text citations"
    )
    
    # Raw reference text (as appears in document)
    raw_text: str = Field(
        ...,
        description="Original reference text from document"
    )
    
    # Reference type
    reference_type: ReferenceType = Field(
        default=ReferenceType.UNKNOWN,
        description="Type of referenced work"
    )
    
    # Parsed bibliographic fields
    # --- Authors ---
    authors: List[str] = Field(
        default_factory=list,
        description="List of author names (e.g., ['Smith, J.', 'Doe, A.'])"
    )
    
    # --- Title ---
    title: Optional[str] = Field(
        default=None,
        description="Title of the work"
    )
    
    # --- Publication venue ---
    journal: Optional[str] = Field(
        default=None,
        description="Journal name (for articles)"
    )
    conference: Optional[str] = Field(
        default=None,
        description="Conference name (for conference papers)"
    )
    book_title: Optional[str] = Field(
        default=None,
        description="Book title (for books or book chapters)"
    )
    publisher: Optional[str] = Field(
        default=None,
        description="Publisher name"
    )
    
    # --- Publication details ---
    year: Optional[int] = Field(
        default=None,
        description="Publication year"
    )
    volume: Optional[str] = Field(
        default=None,
        description="Volume number"
    )
    issue: Optional[str] = Field(
        default=None,
        description="Issue number"
    )
    pages: Optional[str] = Field(
        default=None,
        description="Page range (e.g., '123-145')"
    )
    
    # --- Identifiers ---
    doi: Optional[str] = Field(
        default=None,
        description="Digital Object Identifier"
    )
    isbn: Optional[str] = Field(
        default=None,
        description="ISBN (for books)"
    )
    issn: Optional[str] = Field(
        default=None,
        description="ISSN (for journals)"
    )
    url: Optional[str] = Field(
        default=None,
        description="Web URL"
    )
    arxiv_id: Optional[str] = Field(
        default=None,
        description="arXiv identifier (for preprints)"
    )
    
    # --- Other fields ---
    edition: Optional[str] = Field(
        default=None,
        description="Edition (for books)"
    )
    note: Optional[str] = Field(
        default=None,
        description="Additional notes"
    )
    
    # Position in document
    block_id: Optional[str] = Field(
        default=None,
        description="Block ID of this reference in the references section"
    )
    index: int = Field(
        ...,
        description="Sequential position in reference list (0-based)"
    )
    
    # Citation tracking
    cited_by: List[str] = Field(
        default_factory=list,
        description="List of block IDs that cite this reference"
    )
    citation_count: int = Field(
        default=0,
        description="Number of times this reference is cited"
    )
    
    # Formatting
    formatted_text: Optional[str] = Field(
        default=None,
        description="Formatted reference text according to target style"
    )
    style: Optional[CitationStyle] = Field(
        default=None,
        description="Citation style to use for formatting"
    )
    
    # Validation
    is_valid: bool = Field(
        default=True,
        description="Whether reference passed validation"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation warnings (e.g., missing required fields)"
    )
    is_complete: bool = Field(
        default=False,
        description="Whether all required fields for the reference type are present"
    )
    
    # Extensibility
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    model_config = ConfigDict(use_enum_values=True)
    
    def get_primary_author(self) -> Optional[str]:
        """Get the primary (first) author."""
        return self.authors[0] if self.authors else None
    
    def get_author_list(self, max_authors: int = 3) -> str:
        """
        Get formatted author list with et al. if needed.
        
        Args:
            max_authors: Maximum number of authors to show before using et al.
        
        Returns:
            Formatted author string (e.g., "Smith et al." or "Smith, J. and Doe, A.")
        """
        if not self.authors:
            return "Unknown"
        
        if len(self.authors) <= max_authors:
            return ", ".join(self.authors)
        else:
            return f"{self.authors[0]} et al."
    
    def get_short_citation(self) -> str:
        """Get short citation form (e.g., 'Smith2020' or '[1]')."""
        return self.citation_key
    
    def has_doi(self) -> bool:
        """Check if reference has a DOI."""
        return self.doi is not None and len(self.doi.strip()) > 0
