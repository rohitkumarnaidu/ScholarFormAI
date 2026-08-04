
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.pipeline.integrity.cross_ref import CrossReferenceEngine

_counter = [0]


from app.models import PipelineDocument, Block, Figure, Table, Equation, BlockType

def _block(text, block_type=BlockType.BODY, block_id=None):

    _counter[0] += 1
    return Block(
        block_id=block_id or f"b{_counter[0]}",
        text=text,
        index=_counter[0],
        block_type=block_type)


class TestCrossReferenceEngine:
    def setup_method(self):
        self.engine = CrossReferenceEngine()

    def test_no_violations_when_all_refs_resolve(self):
        doc = PipelineDocument(document_id="t", 
            blocks=[
                _block("As shown in Figure 1 and Table 1, and Eq. (1)."),
            ],
            figures=[Figure(figure_id="f1", index=1)],
            tables=[Table(table_id="t1", num_rows=0, num_cols=0, index=1, block_index=1)],
            equations=[Equation(equation_id="e1", index=1, latex="x=1")])
        violations = self.engine.validate_integrity(doc)
        assert violations == []

    def test_dangling_figure_ref(self):
        doc = PipelineDocument(document_id="t", 
            blocks=[
                _block("See Figure 5 for details."),
            ],
            figures=[Figure(figure_id="f1", index=1)],
            tables=[],
            equations=[])
        violations = self.engine.validate_integrity(doc)
        assert any("Figure 5" in v for v in violations)
        assert any("1 figures" in v for v in violations)

    def test_dangling_table_ref(self):
        doc = PipelineDocument(document_id="t", 
            blocks=[
                _block("See Table 3."),
            ],
            figures=[],
            tables=[Table(table_id="t1", num_rows=0, num_cols=0, index=1, block_index=1)],
            equations=[])
        violations = self.engine.validate_integrity(doc)
        assert any("Table 3" in v for v in violations)

    def test_dangling_equation_ref(self):
        doc = PipelineDocument(document_id="t", 
            blocks=[
                _block("See Eq. (42)."),
            ],
            figures=[],
            tables=[],
            equations=[Equation(equation_id="e1", index=1, latex="x=1")])
        violations = self.engine.validate_integrity(doc)
        assert any("Eq. (42)" in v for v in violations)

    def test_skips_non_body_blocks(self):
        doc = PipelineDocument(document_id="t", 
            blocks=[
                _block("Figure 1", block_type=BlockType.HEADING_1),
                _block("Figure 2", block_type=BlockType.TITLE),
                _block("Figure 3", block_type=BlockType.BODY),
            ],
            figures=[],
            tables=[],
            equations=[])
        violations = self.engine.validate_integrity(doc)
        # HEADING_1 and TITLE are skipped, BODY is checked
        assert len(violations) == 1
        assert "Figure 3" in violations[0]
