# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


"""
Unit tests for the export pipeline.
"""
import pytest
import os
from unittest.mock import MagicMock, patch
from app.models import PipelineDocument, DocumentMetadata
from app.pipeline.export.exporter import Exporter
from app.pipeline.export.pdf_exporter import PDFExporter
from app.pipeline.export.jats_generator import JATSGenerator

class TestExportPipeline:
    
    @pytest.fixture
    def document(self):
        doc = PipelineDocument(
            document_id="test_doc",
            metadata=DocumentMetadata(
                title="Test Title",
                authors=["Author One"],
                publication_date="2023-01-01",
                volume="42",
                issue="1"
            )
        )
        doc.output_path = "output/test.docx"
        doc.generated_doc = MagicMock()
        return doc

    def test_exporter_pdf_call(self, document):
        """Test that Exporter calls PDFExporter when 'pdf' format is requested."""
        exporter = Exporter()
        exporter.pdf_exporter = MagicMock()
        exporter.export_jats = MagicMock()
        exporter.export = MagicMock() # Mock DOCX save
        
        # Request PDF export
        document.formatting_options = {"export_formats": ["pdf", "docx"]}
        
        with patch("os.path.dirname", return_value="output"):
             exporter.process(document)
        
        # Verify PDF conversion was called
        exporter.pdf_exporter.convert_to_pdf.assert_called_with(
            "output/test.docx", 
            "output"
        )

    def test_jats_generation_metadata(self, document):
        """Test JATS XML generation includes new metadata fields."""
        generator = JATSGenerator()
        xml_content = generator.to_xml(document)
        
        # Verify DOCTYPE
        assert "<!DOCTYPE article" in xml_content
        
        # Verify Metadata
        assert "<article-title>Test Title</article-title>" in xml_content
        assert "<surname>One</surname>" in xml_content
        assert "<year>2023</year>" in xml_content
        assert "<volume>42</volume>" in xml_content
        assert "<issue>1</issue>" in xml_content

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_pdf_exporter_command(self, mock_exists, mock_run):
        """Test PDFExporter subcommand construction."""
        # Mock file existence
        mock_exists.return_value = True
        
        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        
        # Mock successful execution
        mock_run.return_value = MagicMock(returncode=0)
        
        exporter.convert_to_pdf("test.docx", "output_dir")
        
        # Verify command arguments
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/soffice"
        assert "--convert-to" in args
        assert "pdf" in args
        assert "test.docx" in args
