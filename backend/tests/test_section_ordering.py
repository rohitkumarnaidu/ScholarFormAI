from unittest.mock import MagicMock

import pytest


def _make_block(block_type="heading_1", text="Introduction", section_name="introduction", is_heading=True):
    block = MagicMock()
    block.block_type = block_type
    block.text = text
    block.section_name = section_name
    block.is_heading.return_value = is_heading
    return block


@pytest.fixture
def contract_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "sections": {
            "order": ["abstract", "introduction", "methods", "results", "conclusion", "references"],
            "required": ["abstract", "introduction", "conclusion", "references"],
        }
    }
    return loader


class TestSectionOrderValidator:
    def test_valid_order(self, contract_loader):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        validator = SectionOrderValidator(contract_loader)
        doc = MagicMock()
        doc.blocks = [
            _make_block("heading_1", "Abstract", "abstract"),
            _make_block("heading_1", "Introduction", "introduction"),
            _make_block("heading_1", "Methods", "methods"),
            _make_block("heading_1", "Results", "results"),
            _make_block("heading_1", "Conclusion", "conclusion"),
            _make_block("heading_1", "References", "references"),
        ]

        violations = validator.validate_order(doc, "ieee")
        assert violations == []

    def test_missing_required_section(self, contract_loader):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        validator = SectionOrderValidator(contract_loader)
        doc = MagicMock()
        doc.blocks = [
            _make_block("heading_1", "Introduction", "introduction"),
            _make_block("heading_1", "Methods", "methods"),
        ]

        violations = validator.validate_order(doc, "ieee")
        missing = [v for v in violations if "Missing" in v]
        assert len(missing) == 3

    def test_out_of_order(self, contract_loader):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        validator = SectionOrderValidator(contract_loader)
        doc = MagicMock()
        doc.blocks = [
            _make_block("heading_1", "Introduction", "introduction"),
            _make_block("heading_1", "Abstract", "abstract"),
        ]

        violations = validator.validate_order(doc, "ieee")
        assert any("out of order" in v for v in violations)

    def test_duplicate_section_ignored(self, contract_loader):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        validator = SectionOrderValidator(contract_loader)
        doc = MagicMock()
        doc.blocks = [
            _make_block("heading_1", "Introduction", "introduction"),
            _make_block("heading_1", "Introduction", "introduction"),
        ]

        violations = validator.validate_order(doc, "ieee")
        sum(1 for v in violations if "Missing" in v)
        assert "Missing required section: abstract" in str(violations)

    def test_non_heading_blocks_skipped(self, contract_loader):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        validator = SectionOrderValidator(contract_loader)
        doc = MagicMock()
        doc.blocks = [
            _make_block("paragraph", "Some text", None, is_heading=False),
            _make_block("heading_1", "Introduction", "introduction"),
        ]

        violations = validator.validate_order(doc, "ieee")
        assert any("Introduction" not in v for v in violations if "Missing" in v)

    def test_empty_document(self, contract_loader):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        validator = SectionOrderValidator(contract_loader)
        doc = MagicMock()
        doc.blocks = []

        violations = validator.validate_order(doc, "ieee")
        assert len(violations) == 4
