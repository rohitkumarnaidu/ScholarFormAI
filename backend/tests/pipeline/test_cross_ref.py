# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock


class TestCrossReferenceEngine:
    def _make_block(self, block_id="b1", text="", block_type=None, section_name=None):
        from app.models import BlockType

        if block_type is None:
            block_type = BlockType.BODY
        b = MagicMock()
        b.block_id = block_id
        b.text = text
        b.block_type = block_type
        b.section_name = section_name
        return b

    def _make_doc(self, blocks=None, figures=None, tables=None, equations=None):
        doc = MagicMock()
        doc.blocks = blocks or []
        doc.figures = figures or []
        doc.tables = tables or []
        doc.equations = equations or []
        return doc

    def test_no_violations(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine

        doc = self._make_doc(blocks=[self._make_block(text="See Figure 1")], figures=[MagicMock()])
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert violations == []

    def test_dangling_figure_ref(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine

        doc = self._make_doc(blocks=[self._make_block(text="See Figure 5")], figures=[MagicMock()])
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 1
        assert "Dangling reference" in violations[0]
        assert "Figure 5" in violations[0]

    def test_dangling_table_ref(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine

        doc = self._make_doc(blocks=[self._make_block(text="See Table 3")], tables=[MagicMock(), MagicMock()])
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 1
        assert "Dangling reference" in violations[0]
        assert "Table 3" in violations[0]

    def test_dangling_equation_ref(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine

        doc = self._make_doc(blocks=[self._make_block(text="See Eq. (5)")], equations=[MagicMock()])
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 1
        assert "Dangling reference" in violations[0]

    def test_only_body_blocks_checked(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine

        heading = self._make_block(text="See Figure 99", block_type="HEADING_1")
        body = self._make_block(text="See Figure 1", block_type="BODY")
        doc = self._make_doc(blocks=[heading, body], figures=[MagicMock()])
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 0
        assert "Figure 99" not in str(violations)

    def test_no_body_blocks(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine

        doc = self._make_doc(
            blocks=[self._make_block(text="See Figure 1", block_type="HEADING_1")], figures=[MagicMock()]
        )
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert violations == []

    def test_multiple_violations(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine

        doc = self._make_doc(blocks=[self._make_block(text="See Figure 2 and Table 5")], figures=[MagicMock()])
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 2
