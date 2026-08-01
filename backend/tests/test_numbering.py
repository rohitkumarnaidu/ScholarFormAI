from unittest.mock import MagicMock

import pytest


def _make_block(block_type="heading_1", text="Introduction", level=1,
                section_name="introduction", is_heading=True):
    block = MagicMock()
    block.block_type = block_type
    block.text = text
    block.level = level
    block.section_name = section_name
    block.metadata = {}
    block.is_heading.return_value = is_heading
    return block


@pytest.fixture
def contract_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "numbering": {},
        "equations": {},
    }
    return loader


class TestApplyNumbering:
    def test_heading_numbering_increments(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = [
            _make_block("heading_1", "Introduction", 1),
            _make_block("heading_2", "Background", 2),
            _make_block("heading_2", "Related Work", 2),
            _make_block("heading_1", "Methods", 1),
        ]
        doc.figures = []
        doc.tables = []
        doc.equations = []

        result = engine.apply_numbering(doc, "ieee")

        assert result.blocks[0].text == "1 Introduction"
        assert result.blocks[0].metadata["number_string"] == "1"
        assert result.blocks[1].text == "1.1 Background"
        assert result.blocks[1].metadata["number_string"] == "1.1"
        assert result.blocks[2].text == "1.2 Related Work"
        assert result.blocks[3].text == "2 Methods"

    def test_no_double_numbering(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = [
            _make_block("heading_1", "1 Introduction", 1),
        ]
        doc.figures = []
        doc.tables = []
        doc.equations = []

        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "1 Introduction"

    def test_figure_numbering(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = []
        fig1 = MagicMock()
        fig2 = MagicMock()
        doc.figures = [fig1, fig2]
        doc.tables = []
        doc.equations = []

        engine.apply_numbering(doc, "ieee")
        assert fig1.number == 1
        assert fig2.number == 2

    def test_table_numbering(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = []
        tbl1 = MagicMock()
        tbl2 = MagicMock()
        doc.figures = []
        doc.tables = [tbl1, tbl2]
        doc.equations = []

        engine.apply_numbering(doc, "ieee")
        assert tbl1.number == 1
        assert tbl2.number == 2

    def test_equation_numbering_parentheses(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        contract_loader.load.return_value = {
            "numbering": {},
            "equations": {"scope": "global", "brackets": "()"},
        }
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        eq1 = MagicMock()
        eq2 = MagicMock()
        doc.equations = [eq1, eq2]

        engine.apply_numbering(doc, "ieee")
        assert eq1.number == "(1)"
        assert eq2.number == "(2)"

    def test_equation_numbering_brackets(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        contract_loader.load.return_value = {
            "numbering": {},
            "equations": {"scope": "global", "brackets": "[]"},
        }
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        eq = MagicMock()
        doc.equations = [eq]

        engine.apply_numbering(doc, "ieee")
        assert eq.number == "[1]"

    def test_equation_numbering_no_brackets(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        contract_loader.load.return_value = {
            "numbering": {},
            "equations": {"scope": "global", "brackets": "{}"},
        }
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        eq = MagicMock()
        doc.equations = [eq]

        engine.apply_numbering(doc, "ieee")
        assert eq.number == "1"

    def test_no_equation_rules(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        contract_loader.load.return_value = {"numbering": {}}
        engine = NumberingEngine(contract_loader)
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        eq = MagicMock()
        doc.equations = [eq]

        engine.apply_numbering(doc, "ieee")
        assert not isinstance(eq.number, str)


class TestInit:
    def test_stores_contract_loader(self, contract_loader):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(contract_loader)
        assert engine.contract_loader is contract_loader
