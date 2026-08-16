# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock


class TestTableCaptionMatcher:
    def _make_doc(self, blocks=None, tables=None):
        doc = MagicMock()
        doc.blocks = blocks or []
        doc.tables = tables or []
        doc.add_processing_stage = MagicMock()
        return doc

    def _make_block(self, index, text="", block_id="b1", block_type="BODY", is_heading=False):
        b = MagicMock()
        b.index = index
        b.text = text
        b.block_id = block_id
        b.block_type = block_type
        b.metadata = {}
        b.is_heading.return_value = is_heading
        return b

    def _make_table(self, block_index=0, table_id="t1"):
        t = MagicMock()
        t.block_index = block_index
        t.table_id = table_id
        t.caption_text = ""
        t.caption_block_id = None
        t.metadata = {}
        return t

    def test_no_tables_or_blocks(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        m = TableCaptionMatcher()
        doc = self._make_doc(tables=[], blocks=[])
        result = m.process(doc)
        assert result is doc

    def test_match_caption_above(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        block = self._make_block(index=0, text="Table 1: Results", block_id="b_cap")
        table = self._make_table(block_index=1, table_id="t1")
        doc = self._make_doc(blocks=[block], tables=[table])
        m = TableCaptionMatcher(search_window_above=2, search_window_below=1)
        m.process(doc)
        assert table.caption_text == "Table 1: Results"
        assert table.caption_block_id == "b_cap"

    def test_no_match_no_caption_pattern(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        block = self._make_block(index=0, text="Some random text", block_id="b1")
        table = self._make_table(block_index=1, table_id="t1")
        doc = self._make_doc(blocks=[block], tables=[table])
        m = TableCaptionMatcher()
        m.process(doc)
        assert table.metadata.get("caption_status") == "Missing"

    def test_skip_heading_blocks(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        heading = self._make_block(index=0, text="Table 1: Results", block_id="h1", is_heading=True)
        body = self._make_block(index=1, text="Body text", block_id="b1")
        table = self._make_table(block_index=2, table_id="t1")
        doc = self._make_doc(blocks=[heading, body], tables=[table])
        m = TableCaptionMatcher()
        m.process(doc)
        assert table.caption_text == ""

    def test_find_references_start(self):
        from app.models import BlockType
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        ref = self._make_block(index=5, text="References", block_id="r1", block_type=BlockType.REFERENCES_HEADING)
        body = self._make_block(index=0, text="Intro", block_id="b1")
        m = TableCaptionMatcher()
        result = m._find_references_start_index([body, ref])
        assert result == 5

    def test_find_references_keyword_fallback(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        heading = self._make_block(index=3, text="Bibliography", block_id="r1", is_heading=True)
        m = TableCaptionMatcher()
        result = m._find_references_start_index([heading])
        assert result == 3

    def test_convenience_function(self):
        from app.pipeline.tables.caption_matcher import match_table_captions

        doc = MagicMock()
        doc.blocks = []
        doc.tables = []
        doc.add_processing_stage = MagicMock()
        result = match_table_captions(doc)
        assert result is doc
