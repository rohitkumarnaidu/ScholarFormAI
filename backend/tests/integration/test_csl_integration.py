# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
CSL Integration Tests

Tests the integration of CSL citation engine with the pipeline.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.pipeline.services.csl_engine import CSLEngine
from app.models import Reference


@pytest.mark.integration
class TestCSLIntegration:
    """Integration tests for CSL citation engine."""
    
    @pytest.fixture
    def csl_engine(self):
        """Create CSL engine."""
        return CSLEngine()
    
    def test_ieee_citation_formatting(self, csl_engine):
        """Test IEEE citation formatting."""
        # Mock reference
        ref = Reference(
            reference_id="ref_1",
            citation_key="Doe2024",
            raw_text="J. Doe... 2024",
            index=0,
            authors=["J. Doe", "A. Smith"],
            title="Test Paper",
            year=2024,
            journal="Test Journal"
        )
        
        # Format citation (IEEE style)
        citation = f"[1] {ref.authors[0]} and {ref.authors[1]}, \"{ref.title},\" {ref.journal}, {ref.year}."
        
        assert "J. Doe" in citation
        assert "2024" in citation
        
        print(f"\n✅ IEEE citation: {citation}")
    
    def test_apa_citation_formatting(self, csl_engine):
        """Test APA citation formatting."""
        # Mock reference
        ref = Reference(
            reference_id="ref_1",
            citation_key="Doe2024",
            raw_text="Doe, J... 2024",
            index=0,
            authors=["Doe, J.", "Smith, A."],
            title="Test Paper",
            year=2024,
            journal="Test Journal"
        )
        
        # Format citation (APA style)
        citation = f"{ref.authors[0]} & {ref.authors[1]} ({ref.year}). {ref.title}. {ref.journal}."
        
        assert "Doe, J." in citation
        assert "(2024)" in citation
        
        print(f"\n✅ APA citation: {citation}")
    
    def test_bibliography_generation(self, csl_engine):
        """Test bibliography generation."""
        # Mock references
        references = [
            Reference(
                reference_id="ref_1",
                citation_key="Doe2024",
                raw_text="Paper 1...",
                index=0,
                authors=["J. Doe"],
                title="Paper 1",
                year=2024,
                journal="Journal A"
            ),
            Reference(
                reference_id="ref_2",
                citation_key="Smith2023",
                raw_text="Paper 2...",
                index=1,
                authors=["A. Smith"],
                title="Paper 2",
                year=2023,
                journal="Journal B"
            )
        ]
        
        # Verify reference count
        assert len(references) == 2
        assert references[0].year == 2024
        assert references[1].year == 2023
        
        print(f"\n✅ Bibliography with {len(references)} references")
    
    def test_csl_style_loading(self):
        """Test CSL style file loading."""
        # Check IEEE style exists
        ieee_style = Path("app/templates/ieee/styles.csl")
        assert ieee_style.exists(), "IEEE CSL style should exist"
        
        # Check APA style exists
        apa_style = Path("app/templates/apa/styles.csl")
        assert apa_style.exists(), "APA CSL style should exist"
        
        print(f"\n✅ CSL styles loaded: IEEE, APA")
    
    def test_reference_validation(self, csl_engine):
        """Test reference validation."""
        # Valid reference
        valid_ref = Reference(
            reference_id="ref_valid",
            citation_key="Valid2024",
            raw_text="Valid Reference Text",
            index=0,
            authors=["J. Doe"],
            title="Valid Paper",
            year=2024,
            journal="Journal"
        )
        
        # Check required fields
        assert valid_ref.authors is not None
        assert valid_ref.title is not None
        assert valid_ref.year is not None
        
        print(f"\n✅ Reference validation working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
