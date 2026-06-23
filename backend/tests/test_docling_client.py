# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Unit tests for Docling layout analysis client.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.pipeline.services.docling_client import (
    DoclingClient,
    BoundingBox,
    LayoutElement,
    DOCLING_AVAILABLE,
)


class TestBoundingBox:
    """Test BoundingBox class."""
    
    def test_initialization(self):
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=80, page=0)
        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 100
        assert bbox.y1 == 80
        assert bbox.page == 0
    
    def test_width_height(self):
        bbox = BoundingBox(x0=10, y0=20, x1=110, y1=120)
        assert bbox.width == 100
        assert bbox.height == 100
    
    def test_center_y(self):
        bbox = BoundingBox(x0=0, y0=100, x1=100, y1=200)
        assert bbox.center_y == 150
    
    def test_to_dict(self):
        bbox = BoundingBox(x0=10, y0=20, x1=110, y1=120, page=1)
        bbox_dict = bbox.to_dict()
        
        assert bbox_dict["x0"] == 10
        assert bbox_dict["y0"] == 20
        assert bbox_dict["x1"] == 110
        assert bbox_dict["y1"] == 120
        assert bbox_dict["page"] == 1
        assert bbox_dict["width"] == 100
        assert bbox_dict["height"] == 100


class TestLayoutElement:
    """Test LayoutElement class."""
    
    def test_initialization(self):
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=80)
        element = LayoutElement(
            text="Sample Text",
            bbox=bbox,
            element_type="paragraph",
            font_size=12.0,
            is_bold=True,
            is_italic=False,
            confidence=0.95,
        )
        
        assert element.text == "Sample Text"
        assert element.element_type == "paragraph"
        assert element.font_size == 12.0
        assert element.is_bold is True
        assert element.is_italic is False
        assert element.confidence == 0.95
    
    def test_to_dict(self):
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=80)
        element = LayoutElement(
            text="Title",
            bbox=bbox,
            element_type="title",
            font_size=18.0,
        )
        
        elem_dict = element.to_dict()
        assert elem_dict["text"] == "Title"
        assert elem_dict["type"] == "title"
        assert elem_dict["font_size"] == 18.0
        assert "bbox" in elem_dict


class TestDoclingClient:
    """Test DoclingClient class."""
    
    def test_initialization(self):
        client = DoclingClient()
        assert client is not None
    
    def test_is_available(self):
        client = DoclingClient()
        # Availability depends on whether docling is installed
        assert isinstance(client.is_available(), bool)
    
    @pytest.mark.skipif(not DOCLING_AVAILABLE, reason="Docling not installed")
    def test_analyze_layout_with_docling(self):
        """Test layout analysis when Docling is available."""
        client = DoclingClient()
        
        # This test requires a real PDF file
        # For now, we'll test the structure
        if client.is_available():
            # Would need a sample PDF for full test
            pass
    
    def test_analyze_layout_without_docling(self):
        """Test layout analysis fallback when Docling unavailable."""
        with patch('app.pipeline.services.docling_client.DOCLING_AVAILABLE', False):
            client = DoclingClient()
            result = client.analyze_layout("dummy.pdf")
            
            # Should return empty layout
            assert result["elements"] == []
            assert result["headers"] == []
            assert result["footers"] == []
            assert result["tables"] == []
            assert result["figures"] == []
            assert result["confidence"] == 0.0
    
    def test_analyze_layout_file_not_found(self):
        """Test handling of missing PDF file."""
        client = DoclingClient()
        result = client.analyze_layout("/nonexistent/file.pdf")
        
        # Should return empty layout on error
        assert result["confidence"] == 0.0
    
    def test_detect_headers_footers(self):
        """Test header/footer detection logic."""
        client = DoclingClient()
        
        # Create mock elements at different positions
        elements = [
            # Header (top 10%)
            LayoutElement(
                text="Header Text",
                bbox=BoundingBox(x0=0, y0=5, x1=100, y1=15, page=0),
                element_type="paragraph",
            ),
            # Body (middle)
            LayoutElement(
                text="Body Text",
                bbox=BoundingBox(x0=0, y0=400, x1=100, y1=450, page=0),
                element_type="paragraph",
            ),
            # Footer (bottom 10%)
            LayoutElement(
                text="Footer Text",
                bbox=BoundingBox(x0=0, y0=950, x1=100, y1=990, page=0),
                element_type="paragraph",
            ),
        ]
        
        headers, footers = client._detect_headers_footers(elements)
        
        assert len(headers) == 1
        assert headers[0].text == "Header Text"
        assert len(footers) == 1
        assert footers[0].text == "Footer Text"
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        client = DoclingClient()
        
        elements = [
            LayoutElement(
                text="Text 1",
                bbox=BoundingBox(0, 0, 100, 100),
                element_type="paragraph",
                confidence=0.9,
            ),
            LayoutElement(
                text="Text 2",
                bbox=BoundingBox(0, 100, 100, 200),
                element_type="paragraph",
                confidence=0.8,
            ),
        ]
        
        confidence = client._calculate_confidence(elements)
        assert abs(confidence - 0.85) < 0.001  # Use tolerance for floating point
    
    def test_calculate_confidence_empty(self):
        """Test confidence calculation with no elements."""
        client = DoclingClient()
        confidence = client._calculate_confidence([])
        assert confidence == 0.0
    
    def test_find_title_with_logo_tolerance(self):
        """Test title detection with logo at top."""
        client = DoclingClient()
        
        elements = [
            # Logo (ignored - above threshold)
            LayoutElement(
                text="Company Logo",
                bbox=BoundingBox(x0=0, y0=10, x1=100, y1=50),
                element_type="figure",
                font_size=24.0,
            ),
            # Title (below logo threshold)
            LayoutElement(
                text="Research Paper Title",
                bbox=BoundingBox(x0=0, y0=200, x1=500, y1=250),
                element_type="title",
                font_size=18.0,
            ),
            # Subtitle (smaller font)
            LayoutElement(
                text="Subtitle",
                bbox=BoundingBox(x0=0, y0=260, x1=400, y1=290),
                element_type="paragraph",
                font_size=14.0,
            ),
        ]
        
        title = client.find_title_with_logo_tolerance(elements, logo_y_threshold=150.0)
        
        assert title is not None
        assert title.text == "Research Paper Title"
        assert title.font_size == 18.0
    
    def test_find_title_no_elements_below_threshold(self):
        """Test title detection when all elements are above threshold."""
        client = DoclingClient()
        
        elements = [
            LayoutElement(
                text="Logo",
                bbox=BoundingBox(x0=0, y0=10, x1=100, y1=50),
                element_type="figure",
                font_size=24.0,
            ),
        ]
        
        title = client.find_title_with_logo_tolerance(elements, logo_y_threshold=150.0)
        assert title is None
    
    def test_empty_layout(self):
        """Test empty layout structure."""
        client = DoclingClient()
        empty = client._empty_layout()
        
        assert empty["elements"] == []
        assert empty["headers"] == []
        assert empty["footers"] == []
        assert empty["tables"] == []
        assert empty["figures"] == []
        assert empty["confidence"] == 0.0


@pytest.mark.integration
class TestDoclingIntegration:
    """Integration tests requiring Docling library."""
    
    def test_docling_import(self):
        """Test that Docling can be imported."""
        try:
            from docling.document_converter import DocumentConverter
            assert DocumentConverter is not None
        except ImportError:
            assert DOCLING_AVAILABLE is False
    
    def test_client_initialization_with_docling(self):
        """Test client initializes properly with Docling."""
        client = DoclingClient()
        if not DOCLING_AVAILABLE:
            assert client.is_available() is False
            return
        assert client.is_available() is True
        assert client.converter is not None


# Fixtures for testing
@pytest.fixture
def sample_bbox():
    """Sample bounding box."""
    return BoundingBox(x0=10, y0=20, x1=110, y1=120, page=0)


@pytest.fixture
def sample_element(sample_bbox):
    """Sample layout element."""
    return LayoutElement(
        text="Sample Text",
        bbox=sample_bbox,
        element_type="paragraph",
        font_size=12.0,
        confidence=0.9,
    )


@pytest.fixture
def docling_client():
    """Docling client instance."""
    return DoclingClient()
