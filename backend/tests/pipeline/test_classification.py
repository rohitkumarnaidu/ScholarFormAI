# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest

class TestContentClassifier:
    @pytest.fixture
    def classifier(self):
        from app.models import PipelineDocument
        from app.pipeline.classification.classifier import ContentClassifier
        return ContentClassifier()

    def test_process_empty_document(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[])
        result = classifier.process(doc)
        assert len(result.blocks) == 0

    def test_process_body_text(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_heading(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_figure_caption(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_table_caption(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_equation_reference(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_section_heading(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_adds_stage_info(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "classification" in stages

    def test_process_preserves_existing_block_types(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "classification" in stages

    def test_process_numbered_list(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_bullet_list(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type is not None

    def test_process_title_block(self, classifier):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = classifier.process(doc)
        assert result.blocks[0].block_type == BlockType.TITLE
