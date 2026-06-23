# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from app.pipeline.structure_detection.detector import StructureDetector
from app.models import PipelineDocument, Block, BlockType


class TestStructureDetector:
    @pytest.fixture
    def detector(self):
        return StructureDetector()

    def test_process_empty_document(self, detector):
        doc = PipelineDocument(document_id="t", blocks=[])
        result = detector.process(doc)
        assert len(result.blocks) == 0

    def test_process_adds_stage_info(self, detector):
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=1, text="Introduction", block_type=BlockType.HEADING_1),
        ])
        result = detector.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "structure_detection" in stages

    def test_process_assigns_block_types(self, detector):
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=1, text="My Paper Title", block_type=BlockType.BODY),
            Block(block_id="b2", index=2, text="Introduction", block_type=BlockType.BODY),
            Block(block_id="b3", index=3, text="Some body content.", block_type=BlockType.BODY),
            Block(block_id="b4", index=4, text="Methods", block_type=BlockType.BODY),
        ])
        result = detector.process(doc)
        assert result.blocks[0].block_type is not None
        assert result.blocks[0].section_name is not None

    def test_process_preserves_title_block(self, detector):
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=1, text="My Paper Title", block_type=BlockType.TITLE),
            Block(block_id="b2", index=2, text="Introduction", block_type=BlockType.HEADING_1),
        ])
        result = detector.process(doc)
        assert result.blocks[0].block_type == BlockType.TITLE

    def test_process_abstract_section(self, detector):
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=1, text="Abstract", block_type=BlockType.HEADING_1),
            Block(block_id="b2", index=2, text="We present results.", block_type=BlockType.BODY),
        ])
        result = detector.process(doc)
        assert result.blocks[0].section_name is not None
        assert result.blocks[1].section_name is not None
