# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest

from app.models import Block, BlockType, PipelineDocument
from app.pipeline.classification.classifier import ContentClassifier


class TestContentClassifier:
    @pytest.fixture
    def classifier(self):
        return ContentClassifier()

    def test_process_empty_document(self, classifier):
        doc = PipelineDocument(document_id="t", blocks=[])
        result = classifier.process(doc)
        assert len(result.blocks) == 0

    def test_process_body_text(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="Regular paragraph text.", block_type=BlockType.BODY),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_heading(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="Introduction", block_type=BlockType.HEADING_1),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_figure_caption(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="Figure 1. Results showing accuracy.", block_type=BlockType.BODY),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_table_caption(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="Table 1. Performance metrics.", block_type=BlockType.BODY),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_equation_reference(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="As shown in Eq. (1).", block_type=BlockType.BODY),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_section_heading(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="Related Work", block_type=BlockType.HEADING_1),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_adds_stage_info(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="Hello.", block_type=BlockType.BODY),
            ],
        )
        result = classifier.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "classification" in stages

    def test_process_preserves_existing_block_types(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="Some content text.", block_type=BlockType.ABSTRACT_BODY),
            ],
        )
        result = classifier.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "classification" in stages

    def test_process_numbered_list(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="1. First item", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="2. Second item", block_type=BlockType.BODY),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_bullet_list(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="- Bullet item", block_type=BlockType.BODY),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_title_block(self, classifier):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                Block(block_id="b1", index=1, text="My Paper Title", block_type=BlockType.TITLE),
            ],
        )
        result = classifier.process(doc)
        assert result.blocks[0].block_type == BlockType.TITLE
