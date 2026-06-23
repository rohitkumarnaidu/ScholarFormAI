# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from app.pipeline.references.parser import ReferenceParser
from app.models import PipelineDocument, Block, BlockType


@pytest.fixture
def parser():
    return ReferenceParser()


class TestReferenceParser:
    def test_parse_ieee_with_quotes(self, parser):
        text = '[1] J. Smith, "Deep Learning," MIT Press, 2016.'
        ref = parser._parse_single_reference(text, 0)
        assert ref.citation_key == "1"
        assert ref.title == "Deep Learning"
        assert "Smith" in str(ref.authors)
        assert ref.reference_type is not None

    def test_parse_ieee_with_doi(self, parser):
        text = '[1] A. Author, "Title," Journal, 2020, doi:10.1234/test.'
        ref = parser._parse_single_reference(text, 0)
        assert ref.doi is not None
        assert "10.1234/test" in ref.doi

    def test_parse_no_citation_key(self, parser):
        text = "Some reference without brackets."
        ref = parser._parse_single_reference(text, 5)
        assert ref.citation_key == "ref_6"

    def test_parse_quoted_title_with_multiple_parts(self, parser):
        text = '[2] B. Doe, C. Lee, "A Study on AI," Proc. Conf., 2021.'
        ref = parser._parse_single_reference(text, 1)
        assert ref.title is not None
        assert len(ref.authors) >= 2

    def test_parse_conference_paper(self, parser):
        text = '[3] D. Author, "Title," Proc. International Conference, 2022.'
        ref = parser._parse_single_reference(text, 2)
        assert ref.reference_type == "conference_paper"

    def test_parse_journal_with_url(self, parser):
        text = '[4] E. Author, "Title," Journal, 2023. https://example.com/paper.'
        ref = parser._parse_single_reference(text, 3)
        assert ref.url is not None
        assert "https://example.com" in ref.url

    def test_parse_authors_simple(self, parser):
        authors = parser._parse_authors("A. Smith, B. Jones")
        assert len(authors) == 2
        assert "Smith" in authors[0]

    def test_parse_authors_with_and(self, parser):
        authors = parser._parse_authors("A. Smith and B. Jones")
        assert len(authors) == 2

    def test_parse_authors_empty(self, parser):
        assert parser._parse_authors("") == []

    def test_process_creates_references(self, parser):
        blocks = [
            Block(block_id="b1", text="[1] Author, \"Title,\" Journal, 2020.",
                  index=1, block_type=BlockType.REFERENCE_ENTRY),
            Block(block_id="b2", text="[2] Author2, \"Title2,\" Journal2, 2021.",
                  index=2, block_type=BlockType.REFERENCE_ENTRY),
        ]
        doc = PipelineDocument(document_id="doc1", blocks=blocks)
        result = parser.process(doc)
        assert len(result.references) == 2

    def test_process_empty_blocks(self, parser):
        doc = PipelineDocument(document_id="doc1", blocks=[])
        result = parser.process(doc)
        assert len(result.references) == 0
