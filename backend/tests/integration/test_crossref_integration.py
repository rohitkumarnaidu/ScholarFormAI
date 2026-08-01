# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


"""
Integration tests for CrossRef validation in the document validator.
"""

import pytest
from unittest.mock import MagicMock
from app.models import PipelineDocument, DocumentMetadata, Reference
from app.pipeline.validation import DocumentValidator

@pytest.mark.integration
class TestCrossRefIntegration:
    
    @pytest.fixture
    def document_with_doi(self):
        doc = PipelineDocument(
            document_id="test_doc",
            metadata=DocumentMetadata(title="Test Document")
        )
        
        # Create a mock reference with DOI
        ref = Reference(
            reference_id="ref_test",
            index=0,
            citation_key="RefTest",
            raw_text="The Title",
            doi="10.1000/182",
            title="The Title",
            authors=["Smith, J."]
        )
        
        doc.references = [ref]
        return doc

    def test_validator_detects_valid_doi(self, document_with_doi):
        """Test validator with mock crossref logic."""
        
        validator = DocumentValidator()
        validator.crossref_client = MagicMock()
        
        # Mock client responses
        validator.crossref_client.validate_doi.return_value = True
        validator.crossref_client.get_metadata.return_value = {
            "title": ["The Title"],
            "published-print": {"date-parts": [[2023]]},
            "author": [{"family": "Smith"}]
        }
        validator.crossref_client.calculate_confidence.return_value = 0.95
        
        # Execute validation
        result = validator.validate(document_with_doi)
        
        # Check Reference Metadata
        ref = document_with_doi.references[0]
        assert "validation" in ref.metadata
        assert ref.metadata["validation"]["doi_valid"] is True
        assert ref.metadata["validation"]["confidence"] == 0.95
        
        # Check warnings
        assert not any("invalid DOI" in w for w in result.warnings)

    def test_validator_detects_invalid_doi(self, document_with_doi):
        """Test validator handles invalid DOI."""
        
        validator = DocumentValidator()
        validator.crossref_client = MagicMock()
        
        # Mock client response
        validator.crossref_client.validate_doi.return_value = False
        
        # Execute validation
        result = validator.validate(document_with_doi)
        
        # Check Reference Metadata
        ref = document_with_doi.references[0]
        assert ref.metadata["validation"]["doi_valid"] is False
        assert ref.metadata["validation"]["confidence"] == 0.0
        
        # Check warnings
        found_warning = any("invalid DOI" in w for w in result.warnings)
        assert found_warning, "Should warn about invalid DOI"
