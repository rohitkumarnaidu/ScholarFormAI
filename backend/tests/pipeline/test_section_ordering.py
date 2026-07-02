# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from app.pipeline.formatting.section_ordering import SectionOrderValidator

@pytest.fixture
def mock_contract_loader():

    from app.models import PipelineDocument, Block, BlockType
    loader = MagicMock()
    loader.load.return_value = {
        "sections": {
            "order": ["abstract", "introduction", "methods", "results", "discussion", "conclusion", "references"],
            "required": ["abstract", "introduction", "references"],
        }
    }
    return loader

def _h(text: str, section_name: str, index: int, bid: str):
    from app.models import PipelineDocument, Block, BlockType
    return Block(
        block_id=bid, text=text, index=index,
        block_type=BlockType.HEADING_1,
        section_name=section_name,
        level=1,
    )

def _body(text: str, index: int, bid: str):
    from app.models import PipelineDocument, Block, BlockType
    return Block(block_id=bid, text=text, index=index, block_type=BlockType.BODY)

class TestSectionOrderValidator:
    def test_valid_order_no_violations(self, mock_contract_loader):
        from app.models import PipelineDocument, Block, BlockType
        validator = SectionOrderValidator(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                _h("Abstract", "Abstract", 1, "b1"),
                _h("Introduction", "Introduction", 2, "b2"),
                _h("Methods", "Methods", 3, "b3"),
                _h("Results", "Results", 4, "b4"),
                _h("Discussion", "Discussion", 5, "b5"),
                _h("Conclusion", "Conclusion", 6, "b6"),
                _h("References", "References", 7, "b7"),
            ],
        )
        violations = validator.validate_order(doc, "ieee")
        assert violations == []

    def test_missing_required_section(self, mock_contract_loader):
        from app.models import PipelineDocument, Block, BlockType
        validator = SectionOrderValidator(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                _h("Introduction", "Introduction", 1, "b1"),
                _h("References", "References", 2, "b2"),
            ],
        )
        violations = validator.validate_order(doc, "ieee")
        assert any("abstract" in v.lower() for v in violations)

    def test_out_of_order_section(self, mock_contract_loader):
        from app.models import PipelineDocument, Block, BlockType
        validator = SectionOrderValidator(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                _h("Abstract", "Abstract", 1, "b1"),
                _h("Results", "Results", 2, "b2"),
                _h("Introduction", "Introduction", 3, "b3"),
            ],
        )
        violations = validator.validate_order(doc, "ieee")
        assert any("out of order" in v.lower() for v in violations)

    def test_no_headings_no_violations(self, mock_contract_loader):
        from app.models import PipelineDocument, Block, BlockType
        validator = SectionOrderValidator(mock_contract_loader)
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[_body("Some text", 1, "b1")],
        )
        violations = validator.validate_order(doc, "ieee")
        assert any("missing" in v.lower() for v in violations)

    def test_empty_document(self, mock_contract_loader):
        from app.models import PipelineDocument, Block, BlockType
        validator = SectionOrderValidator(mock_contract_loader)
        doc = PipelineDocument(document_id="doc1")
        violations = validator.validate_order(doc, "ieee")
        assert len(violations) == 3
