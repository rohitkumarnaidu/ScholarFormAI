from __future__ import annotations

from unittest.mock import patch

import pytest


class TestPipelineDocument:
    def test_document_metadata_defaults(self):
        from app.models.pipeline_document import DocumentMetadata
        md = DocumentMetadata()
        assert md.title is None
        assert md.authors == []
        assert md.abstract is None

    def test_document_metadata_full(self):
        from app.models.pipeline_document import DocumentMetadata
        md = DocumentMetadata(
            title="Test", authors=["Alice"], affiliations=["MIT"],
            abstract="An abstract", keywords=["test"], doi="10.1234/test",
        )
        assert md.title == "Test"
        assert md.doi == "10.1234/test"

    def test_template_info_defaults(self):
        from app.models.pipeline_document import TemplateInfo
        t = TemplateInfo(template_name="ieee")
        assert t.template_name == "ieee"
        assert t.template_version == "1.0"

    def test_processing_stage_defaults(self):
        from app.models.pipeline_document import ProcessingStage
        ps = ProcessingStage(stage_name="parse", status="completed")
        assert ps.stage_name == "parse"
        assert ps.status == "completed"
        assert ps.message is None

    def test_create_pipeline_document(self):
        from app.models.pipeline_document import DocumentMetadata, PipelineDocument
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(title="Test Paper"),
        )
        assert doc.document_id == "doc1"
        assert doc.metadata.title == "Test Paper"
        assert doc.blocks == []
        assert doc.is_valid is True

    def test_validate_document_id_empty(self):
        from app.models.pipeline_document import PipelineDocument
        with pytest.raises(Exception):
            PipelineDocument(document_id="")

    def test_validate_document_id_whitespace(self):
        from app.models.pipeline_document import PipelineDocument
        with pytest.raises(Exception):
            PipelineDocument(document_id="   ")

    def test_add_processing_stage(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        doc.add_processing_stage("parse", "completed", "Done", 100)
        assert len(doc.processing_history) == 1
        assert doc.processing_history[0].stage_name == "parse"

    def test_add_processing_stage_updates_timestamp(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        old_updated = doc.updated_at
        doc.add_processing_stage("validate", "processing")
        assert doc.updated_at >= old_updated

    def test_add_processing_stage_exception_handled(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        with patch("app.models.pipeline_document.ProcessingStage") as mock_ps:
            mock_ps.side_effect = ValueError("bad stage")
            doc.add_processing_stage("bad", "fail")
            assert len(doc.processing_history) == 0

    def test_get_block_by_id(self):
        from app.models.block import Block
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        b = Block(block_id="b1", text="Hello", index=0)
        doc.blocks.append(b)
        assert doc.get_block_by_id("b1") is b
        assert doc.get_block_by_id("nonexistent") is None

    def test_get_block_by_id_empty(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        assert doc.get_block_by_id("") is None

    def test_get_figure_by_id(self):
        from app.models.figure import Figure
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        f = Figure(figure_id="f1", caption="Fig 1", image_path="/img.png", index=0)
        doc.figures.append(f)
        assert doc.get_figure_by_id("f1") is f
        assert doc.get_figure_by_id("") is None

    def test_get_equation_by_id(self):
        from app.models.equation import Equation
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        e = Equation(equation_id="e1", latex="x=y", index=0)
        doc.equations.append(e)
        assert doc.get_equation_by_id("e1") is e
        assert doc.get_equation_by_id("") is None

    def test_get_blocks_by_type(self):
        from app.models.block import Block
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        doc.blocks.append(Block(block_id="b1", text="A", index=0, block_type="body"))
        doc.blocks.append(Block(block_id="b2", text="B", index=1, block_type="heading_1"))
        bodies = doc.get_blocks_by_type("body")
        assert len(bodies) == 1
        assert doc.get_blocks_by_type("") == []

    def test_get_blocks_in_section(self):
        from app.models.block import Block
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        b1 = Block(block_id="b1", text="Intro text", index=0, section_name="Introduction")
        b2 = Block(block_id="b2", text="Method", index=1, section_name="Methods")
        doc.blocks.extend([b1, b2])
        results = doc.get_blocks_in_section("intro")
        assert len(results) == 1
        assert doc.get_blocks_in_section("") == []

    def test_get_section_names(self):
        from app.models.block import Block
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        doc.blocks.append(Block(block_id="b1", text="A", index=0, section_name="Intro"))
        doc.blocks.append(Block(block_id="b2", text="B", index=1, section_name="Methods"))
        doc.blocks.append(Block(block_id="b3", text="C", index=2))
        names = doc.get_section_names()
        assert "Intro" in names
        assert "Methods" in names

    def test_get_stats(self):
        from app.models.block import Block
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        doc.blocks.append(Block(block_id="b1", text="A", index=0))
        stats = doc.get_stats()
        assert stats["blocks"] == 1
        assert stats["figures"] == 0
        assert stats["references"] == 0

    def test_get_stats_exception_returns_defaults(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        with patch.object(doc, "blocks", side_effect=Exception("boom")):
            stats = doc.get_stats()
            assert stats["blocks"] == 0

    def test_create_with_full_data(self):
        from app.models.block import Block
        from app.models.pipeline_document import DocumentMetadata, PipelineDocument, TemplateInfo
        doc = PipelineDocument(
            document_id="d1",
            original_filename="paper.docx",
            metadata=DocumentMetadata(title="Paper", authors=["Alice"]),
            template=TemplateInfo(template_name="ieee"),
            blocks=[Block(block_id="b1", text="Body", index=0)],
        )
        assert doc.original_filename == "paper.docx"
        assert doc.template.template_name == "ieee"
        assert len(doc.blocks) == 1
