# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
import pytest
from app.pipeline.structure_detection.detector import StructureDetector

class TestStructureDetector:
    @pytest.fixture
    def detector(self):

        from app.models import PipelineDocument, Block, BlockType
        return StructureDetector()

    def test_process_empty_document(self, detector):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="t", blocks=[])
        result = detector.process(doc)
        assert len(result.blocks) == 0

    def test_process_adds_stage_info(self, detector):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = detector.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "structure_detection" in stages

    def test_process_assigns_block_types(self, detector):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = detector.process(doc)
        assert result.blocks[0].block_type is not None
        assert result.blocks[0].section_name is not None

    def test_process_preserves_title_block(self, detector):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = detector.process(doc)
        assert result.blocks[0].block_type == BlockType.TITLE

    def test_process_abstract_section(self, detector):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = detector.process(doc)
        assert result.blocks[0].section_name is not None
        assert result.blocks[1].section_name is not None
