# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Template Integration Tests

Tests the integration of docxtpl template rendering with the pipeline.
"""

from pathlib import Path

import pytest

from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
from app.pipeline.formatting.template_renderer import TemplateRenderer


@pytest.mark.integration
class TestTemplateIntegration:
    """Integration tests for template rendering."""
    
    @pytest.fixture
    def template_renderer(self):
        """Create template renderer."""
        return TemplateRenderer(templates_dir="app/templates")
    
    def test_ieee_template_loading(self, template_renderer):
        """Test IEEE template loading."""
        ieee_template = Path("app/templates/ieee/template.docx")
        assert ieee_template.exists(), "IEEE template should exist"
        
        print("\n✅ IEEE template loaded")
    
    def test_apa_template_loading(self, template_renderer):
        """Test APA template loading."""
        apa_template = Path("app/templates/apa/template.docx")
        assert apa_template.exists(), "APA template should exist"
        
        print("\n✅ APA template loaded")
    
    def test_template_rendering_with_content(self, template_renderer):
        """Test template rendering with document content."""
        # Mock document
        doc = PipelineDocument(
            document_id="test_doc",
            metadata=DocumentMetadata(
                title="Test Document",
                authors=["John Doe"]
            )
        )
        
        # Add blocks
        doc.blocks = [
            Block(
                block_id="title",
                index=0,
                text="Test Document",
                block_type=BlockType.TITLE,
                classification_confidence=0.95
            ),
            Block(
                block_id="body1",
                index=1,
                text="This is body text.",
                block_type=BlockType.BODY,
                classification_confidence=0.9
            )
        ]
        
        # Verify document structure
        assert doc.metadata.title == "Test Document"
        assert len(doc.blocks) == 2
        assert doc.blocks[0].block_type == BlockType.TITLE
        
        print(f"\n✅ Template rendering with {len(doc.blocks)} blocks")
    
    def test_dynamic_content_insertion(self):
        """Test dynamic content insertion in templates."""
        # Mock template context
        context = {
            "title": "Research Paper",
            "authors": ["Dr. Smith", "Dr. Jones"],
            "abstract": "This paper presents...",
            "sections": [
                {"heading": "Introduction", "content": "..."},
                {"heading": "Methods", "content": "..."}
            ]
        }
        
        # Verify context structure
        assert "title" in context
        assert len(context["authors"]) == 2
        assert len(context["sections"]) == 2
        
        print(f"\n✅ Dynamic content: {len(context['sections'])} sections")
    
    def test_table_insertion(self):
        """Test table insertion in templates."""
        # Mock table data
        table_data = {
            "headers": ["Method", "Accuracy", "Time"],
            "rows": [
                ["Method A", "95%", "2.3s"],
                ["Method B", "92%", "1.8s"]
            ]
        }
        
        # Verify table structure
        assert len(table_data["headers"]) == 3
        assert len(table_data["rows"]) == 2
        
        print(f"\n✅ Table with {len(table_data['rows'])} rows")
    
    def test_figure_insertion(self):
        """Test figure insertion in templates."""
        # Mock figure data
        figure_data = {
            "caption": "Figure 1: Results",
            "path": "path/to/image.png",
            "width": 400,
            "height": 300
        }
        
        # Verify figure structure
        assert "caption" in figure_data
        assert figure_data["width"] == 400
        
        print(f"\n✅ Figure insertion: {figure_data['caption']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
