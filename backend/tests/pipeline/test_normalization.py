# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest

from app.pipeline.normalization.normalizer import Normalizer


class TestNormalizer:
    @pytest.fixture
    def engine(self):

        return Normalizer()

    def test_process_empty_blocks(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[])
        result = engine.process(doc)
        assert result is doc

    def test_process_single_line(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert len(result.blocks) == 1
        assert result.blocks[0].text == "Hello world."

    def test_strips_extra_spaces(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert result.blocks[0].text == "Hello world."

    def test_strips_leading_trailing_whitespace(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert result.blocks[0].text == "Hello world."

    def test_process_heading(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert result.blocks[0].text == "INTRODUCTION"

    def test_unifies_line_endings(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        # \r\n is normalized to \n, but standalone \r may remain
        assert "\\r\\n" not in repr(result.blocks[0].text)

    def test_removes_empty_blocks(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert len(result.blocks) == 1
        assert result.blocks[0].block_id == "b3"

    def test_preserves_blocks_with_only_whitespace_handled(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert result.blocks[0].text == "Indented."

    def test_preserves_special_chars(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        # Normalizer does not decode HTML entities; text passes through cleanly
        assert "AT&amp;T" in result.blocks[0].text

    def test_handles_empty_text(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        # Empty blocks are removed during normalization
        assert len(result.blocks) == 0

    def test_adds_stage_info(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "normalization" in stages

    def test_removes_non_ascii_chars(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert "\u2014" not in result.blocks[0].text
        assert "\u2013" not in result.blocks[0].text

    def test_smart_quotes_to_straight(self, engine):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = engine.process(doc)
        assert '"Hello"' in result.blocks[0].text
        assert "'world'" in result.blocks[0].text
