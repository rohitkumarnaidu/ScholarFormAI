# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


"""
CrossRef API Client for DOI validation and metadata retrieval.

This client interfaces with the CrossRef REST API to:
1. Validate if a DOI exists.
2. Retrieve metadata for a DOI.
3. Calculate confidence scores based on metadata matching.

Rate Limit: 50 requests/second (polite pool).
"""

import logging
import requests
import time
from typing import Dict, Any, Optional
from difflib import SequenceMatcher

from app.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

class CrossRefException(ExternalServiceError):
    """Exception raised for CrossRef service errors."""
    def __init__(self, message: str = "CrossRef service call failed.") -> None:
        super().__init__(service="CrossRef", message=message)

class CrossRefClient:
    """REST API client for CrossRef service."""

    BASE_URL = "https://api.crossref.org/works/"
    
    # Rate limiting: 50 req/s = 0.02s per request. 
    # specific logic to ensuring we don't exceed this.
    MIN_REQUEST_INTERVAL = 0.025  # Slightly conservative (40 req/s)

    def __init__(self, email: Optional[str] = None):
        """
        Initialize CrossRef client.
        
        Args:
            email: Optional email for "Polite" pool usage (recommended).
        """
        self.headers = {}
        if email:
            self.headers["User-Agent"] = f"ScholarFormAI/1.0 (mailto:{email})"
        
        self.last_request_time = 0.0

    def _wait_for_rate_limit(self):
        """Ensure we respect the rate limit."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def validate_doi(self, doi: str) -> bool:
        """
        Check if a DOI exists in CrossRef.
        
        Args:
            doi: The DOI string to validate.
            
        Returns:
            True if DOI exists, False otherwise.
        """
        try:
            self.get_metadata(doi)
            return True
        except CrossRefException:
            return False

    def get_metadata(self, doi: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a DOI.
        
        Args:
            doi: The DOI string.
            
        Returns:
            Dictionary with metadata.
            
        Raises:
            CrossRefException: If DOI not found vs API error.
        """
        self._wait_for_rate_limit()
        
        clean_doi = doi.strip()
        url = f"{self.BASE_URL}{clean_doi}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {})
            elif response.status_code == 404:
                raise CrossRefException(f"DOI not found: {doi}")
            else:
                raise CrossRefException(f"CrossRef API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise CrossRefException(f"Network error: {str(e)}")

    def calculate_confidence(self, reference_data: Dict[str, Any], crossref_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score by comparing local reference data with CrossRef data.
        
        Args:
            reference_data: Dict containing 'title', 'year', 'authors'.
            crossref_data: Metadata from CrossRef.
            
        Returns:
            Float confidence score (0.0 - 1.0).
        """
        score = 0.0
        checks = 0
        
        # 1. Title Match (Weighted 50%)
        ref_title = reference_data.get("title", "")
        cr_title_list = crossref_data.get("title", [])
        cr_title = cr_title_list[0] if cr_title_list else ""
        
        if ref_title and cr_title:
            similarity = SequenceMatcher(None, ref_title.lower(), cr_title.lower()).ratio()
            score += similarity * 0.5
            checks += 1
        
        # 2. Year Match (Weighted 30%)
        ref_year = reference_data.get("year")
        
        # Extract year from CrossRef 'published-print' or 'published-online'
        cr_date_parts = crossref_data.get("published-print", {}).get("date-parts", [])
        if not cr_date_parts:
            cr_date_parts = crossref_data.get("published-online", {}).get("date-parts", [])
            
        if ref_year and cr_date_parts:
            cr_year = cr_date_parts[0][0]
            if int(ref_year) == int(cr_year):
                score += 0.3
            checks += 1
            
        # 3. Author Match (Weighted 20%) - Check first author surname
        ref_authors = reference_data.get("authors", [])
        cr_authors = crossref_data.get("author", [])
        
        if ref_authors and cr_authors:
            # Simple check: is the first surname match?
            # Assuming ref_authors is list of strings "Surname, Firstname" or similar
            # And CrossRef is list of dicts {'given': '...', 'family': '...'}
            
            # Very basic approximation
            first_ref_author = ref_authors[0].lower()
            found = False
            for author in cr_authors:
                family = author.get("family", "").lower()
                if family and family in first_ref_author:
                    found = True
                    break
            
            if found:
                score += 0.2
            checks += 1
            
        # Normalize if some checks were skipped? 
        # For strictness, we just return the accumulated score.
        # But if we only checked title, maybe that's enough?
        
        if checks == 0:
            return 0.0
            
        return score
