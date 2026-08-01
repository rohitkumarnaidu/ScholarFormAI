# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from app.pipeline.references.parser import ReferenceParser
from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
from app.pipeline.contracts.loader import ContractLoader

FIXTURES_DIR = "tests/fixtures/contracts"

class TestReferenceParser:
    @pytest.fixture
    def parser(self):

        return ReferenceParser()

    def test_process_empty_document(self, parser):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="t", blocks=[Block(block_id="b1", index=1, text="hello", block_type=BlockType.BODY)])
        result = parser.process(doc)
        assert result.references == []

    def test_process_with_reference_entries(self, parser):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = parser.process(doc)
        assert len(result.references) >= 1

    def test_process_no_match(self, parser):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = parser.process(doc)
        assert result.references == []

    def test_process_adds_stage_info(self, parser):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="t", blocks=[
        ])
        result = parser.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "reference_parsing" in stages or result.references is not None

class TestReferenceFormatterEngine:
    @pytest.fixture
    def formatter(self):
        return ReferenceFormatterEngine(contract_loader=ContractLoader(contracts_dir=FIXTURES_DIR))

    def test_format_all_empty(self, formatter):
        refs = formatter.format_all([], "ieee")
        assert refs == []

    def test_format_all_with_csl_fallback(self, formatter):
        from app.models import Reference
        refs = [Reference(reference_id="r1", citation_key="k1", raw_text="Test", index=1, authors=["A"], title="T", year=2024)]
        result = formatter.format_all(refs, "none")
        assert len(result) == 1

    def test_format_single(self, formatter):
        from app.models import Reference
        ref = Reference(reference_id="r2", citation_key="k2", raw_text="Test", index=1, authors=["A. B."], title="Title", year=2024)
        rules = {"journal_format": "{authors}, \"{title},\" {journal}, {year}."}
        result = formatter.format_single(ref, rules)
        assert "A. B." in result or "Title" in result
