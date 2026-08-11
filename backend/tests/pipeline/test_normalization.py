# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest

from app.models import Block, BlockType, PipelineDocument
from app.pipeline.normalization.normalizer import Normalizer


def _make_block(text: str, block_id: str = "b1", index: int = 0, block_type: BlockType = BlockType.BODY) -> Block:
    return Block(
        block_id=block_id,
        text=text,
        index=index,
        block_type=block_type,
    )


class TestNormalizer:
    @pytest.fixture
    def engine(self):
        return Normalizer()

    def test_process_empty_blocks(self, engine):
        doc = PipelineDocument(document_id="t", blocks=[])
        result = engine.process(doc)
        assert result is doc

    def test_process_single_line(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("Hello world.", "b1", 0)],
        )
        result = engine.process(doc)
        assert len(result.blocks) == 1
        assert result.blocks[0].text == "Hello world."

    def test_strips_extra_spaces(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("Hello   world.", "b1", 0)],
        )
        result = engine.process(doc)
        assert result.blocks[0].text == "Hello world."

    def test_strips_leading_trailing_whitespace(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("  Hello world.  ", "b1", 0)],
        )
        result = engine.process(doc)
        assert result.blocks[0].text == "Hello world."

    def test_process_heading(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("INTRODUCTION", "b1", 0, BlockType.HEADING_1)],
        )
        result = engine.process(doc)
        assert result.blocks[0].text == "INTRODUCTION"

    def test_unifies_line_endings(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("Line 1\r\nLine 2", "b1", 0)],
        )
        result = engine.process(doc)
        # \r\n is normalized to \n, but standalone \r may remain
        assert "\\r\\n" not in repr(result.blocks[0].text)

    def test_removes_empty_blocks(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[
                _make_block("", "b1", 0),
                _make_block("   ", "b2", 1),
                _make_block("Content", "b3", 2),
            ],
        )
        result = engine.process(doc)
        assert len(result.blocks) == 1
        assert result.blocks[0].block_id == "b3"

    def test_preserves_blocks_with_only_whitespace_handled(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("  Indented.  ", "b1", 0)],
        )
        result = engine.process(doc)
        assert result.blocks[0].text == "Indented."

    def test_preserves_special_chars(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("AT&amp;T", "b1", 0)],
        )
        result = engine.process(doc)
        # Normalizer does not decode HTML entities; text passes through cleanly
        assert "AT&amp;T" in result.blocks[0].text

    def test_handles_empty_text(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("", "b1", 0)],
        )
        result = engine.process(doc)
        # Empty blocks are removed during normalization
        assert len(result.blocks) == 0

    def test_adds_stage_info(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("Some text", "b1", 0)],
        )
        result = engine.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "normalization" in stages

    def test_removes_non_ascii_chars(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("Hello \u2014 world \u2013 test", "b1", 0)],
        )
        result = engine.process(doc)
        assert "\u2014" not in result.blocks[0].text
        assert "\u2013" not in result.blocks[0].text

    def test_smart_quotes_to_straight(self, engine):
        doc = PipelineDocument(
            document_id="t",
            blocks=[_make_block("\u201cHello\u201d \u2018world\u2019", "b1", 0)],
        )
        result = engine.process(doc)
        assert '"Hello"' in result.blocks[0].text
        assert "'world'" in result.blocks[0].text
