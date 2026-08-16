# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.pipeline.formatting.numbering import NumberingEngine


@pytest.fixture
def mock_contract_loader():

    loader = MagicMock()
    loader.load.return_value = {
        "numbering": {},
        "equations": {"scope": "global", "brackets": "()"},
    }
    return loader


def _h(text: str, level: int, index: int, bid: str):
    from app.models import Block, BlockType

    bt = getattr(BlockType, f"HEADING_{level}", BlockType.HEADING_1)
    return Block(block_id=bid, text=text, index=index, block_type=bt, level=level)


def _body(text: str, index: int, bid: str):
    from app.models import Block, BlockType

    return Block(block_id=bid, text=text, index=index, block_type=BlockType.BODY)


class TestNumberingEngine:
    def test_number_headings_sequential(self, mock_contract_loader):
        from app.models import PipelineDocument

        engine = NumberingEngine(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                _h("Introduction", 1, 1, "b1"),
                _h("Background", 1, 2, "b2"),
                _h("Results", 1, 3, "b3"),
            ],
        )
        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "1 Introduction"
        assert result.blocks[1].text == "2 Background"
        assert result.blocks[2].text == "3 Results"

    def test_number_nested_headings(self, mock_contract_loader):
        from app.models import PipelineDocument

        engine = NumberingEngine(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                _h("Section 1", 1, 1, "b1"),
                _h("Subsection 1.1", 2, 2, "b2"),
                _h("Subsection 1.2", 2, 3, "b3"),
                _h("Section 2", 1, 4, "b4"),
            ],
        )
        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "1 Section 1"
        assert result.blocks[1].text == "1.1 Subsection 1.1"
        assert result.blocks[2].text == "1.2 Subsection 1.2"
        assert result.blocks[3].text == "2 Section 2"

    def test_idempotent_no_double_number(self, mock_contract_loader):
        from app.models import PipelineDocument

        engine = NumberingEngine(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                _h("1 Introduction", 1, 1, "b1"),
            ],
        )
        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "1 Introduction"

    def test_figure_numbering(self, mock_contract_loader):
        from app.models import Figure, PipelineDocument

        engine = NumberingEngine(mock_contract_loader)
        fig1 = Figure(figure_id="f1", index=1)
        fig2 = Figure(figure_id="f2", index=2)
        doc = PipelineDocument(document_id="doc1", figures=[fig1, fig2])
        result = engine.apply_numbering(doc, "ieee")
        assert result.figures[0].number == 1
        assert result.figures[1].number == 2

    def test_table_numbering(self, mock_contract_loader):
        from app.models import PipelineDocument, Table

        engine = NumberingEngine(mock_contract_loader)
        t1 = Table(table_id="t1", num_rows=1, num_cols=1, index=1, block_index=0)
        t2 = Table(table_id="t2", num_rows=1, num_cols=1, index=2, block_index=1)
        doc = PipelineDocument(document_id="doc1", tables=[t1, t2])
        result = engine.apply_numbering(doc, "ieee")
        assert result.tables[0].number == 1
        assert result.tables[1].number == 2

    def test_equation_numbering_parentheses(self, mock_contract_loader):
        from app.models import Equation, PipelineDocument

        engine = NumberingEngine(mock_contract_loader)
        eq1 = Equation(equation_id="e1", latex="x=1", index=1)
        eq2 = Equation(equation_id="e2", latex="y=2", index=2)
        doc = PipelineDocument(document_id="doc1", equations=[eq1, eq2])
        result = engine.apply_numbering(doc, "ieee")
        assert result.equations[0].number == "(1)"
        assert result.equations[1].number == "(2)"

    def test_equation_numbering_brackets(self, mock_contract_loader):
        from app.models import Equation, PipelineDocument

        loader = MagicMock()
        loader.load.return_value = {
            "numbering": {},
            "equations": {"scope": "global", "brackets": "[]"},
        }
        engine = NumberingEngine(loader)
        eq1 = Equation(equation_id="e1", latex="x=1", index=1)
        doc = PipelineDocument(document_id="doc1", equations=[eq1])
        result = engine.apply_numbering(doc, "ieee")
        assert result.equations[0].number == "[1]"

    def test_equation_numbering_no_brackets(self, mock_contract_loader):
        from app.models import Equation, PipelineDocument

        loader = MagicMock()
        loader.load.return_value = {
            "numbering": {},
            "equations": {"scope": "global", "brackets": "{}"},
        }
        engine = NumberingEngine(loader)
        eq1 = Equation(equation_id="e1", latex="x=1", index=1)
        doc = PipelineDocument(document_id="doc1", equations=[eq1])
        result = engine.apply_numbering(doc, "ieee")
        assert result.equations[0].number == "1"

    def test_non_heading_blocks_unchanged(self, mock_contract_loader):
        from app.models import PipelineDocument

        engine = NumberingEngine(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                _body("Some text", 1, "b1"),
                _body("More text", 2, "b2"),
            ],
        )
        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "Some text"
        assert result.blocks[1].text == "More text"
