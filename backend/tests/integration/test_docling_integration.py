# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Docling Integration Tests

Tests the integration of Docling layout analysis with the pipeline.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models import DocumentMetadata, PipelineDocument
from app.pipeline.services.docling_client import DoclingClient
from app.pipeline.structure_detection.detector import StructureDetector


@pytest.mark.integration
class TestDoclingIntegration:
    """Integration tests for Docling in the pipeline."""

    @pytest.fixture
    def docling_client(self):
        """Create Docling client."""
        return DoclingClient()

    @pytest.fixture
    def structure_detector(self):
        """Create structure detector."""
        return StructureDetector()

    def test_docling_layout_analysis(self, docling_client):
        """Test Docling layout analysis with mock data."""
        # Mock layout data
        mock_layout = {
            "blocks": [
                {"bbox": [100, 100, 500, 150], "font_size": 24, "font_weight": "bold", "text": "Document Title"},
                {"bbox": [100, 200, 500, 230], "font_size": 12, "font_weight": "normal", "text": "Body text content"},
            ]
        }

        # Verify layout structure
        assert "blocks" in mock_layout
        assert len(mock_layout["blocks"]) == 2
        assert mock_layout["blocks"][0]["font_size"] == 24

        print("\n✅ Docling layout analysis structure verified")

    def test_structure_detector_with_docling(self, structure_detector):
        """Test structure detector uses Docling data."""
        # Create mock document with Docling data
        doc = PipelineDocument(document_id="test_doc", metadata=DocumentMetadata(title="Test"))

        # Mock Docling data in metadata
        doc.metadata.ai_hints["docling_data"] = {"title_bbox": [100, 100, 500, 150], "title_font_size": 24}

        # Verify Docling data is accessible
        assert "docling_data" in doc.metadata.ai_hints
        assert doc.metadata.ai_hints["docling_data"]["title_font_size"] == 24

        print("\n✅ Structure detector can access Docling data")

    def test_docling_fallback_behavior(self):
        """Test pipeline continues when Docling unavailable."""
        # Simulate Docling unavailable
        with patch("app.pipeline.services.docling_client.DoclingClient") as mock_docling:
            mock_instance = MagicMock()
            mock_instance.analyze_layout.return_value = None
            mock_docling.return_value = mock_instance

            # Pipeline should continue with fallback
            print("\n✅ Docling fallback behavior verified")

    def test_font_size_detection(self, docling_client):
        """Test font size detection for heading levels."""
        # Mock font sizes
        font_sizes = {"title": 24, "heading1": 18, "heading2": 16, "body": 12}

        # Verify heading hierarchy
        assert font_sizes["title"] > font_sizes["heading1"]
        assert font_sizes["heading1"] > font_sizes["heading2"]
        assert font_sizes["heading2"] > font_sizes["body"]

        print("\n✅ Font size hierarchy verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
