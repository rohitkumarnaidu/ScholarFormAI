# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from app.pipeline.formatting.reference_formatter import (
    _resolve_csl_path,
    _parse_author_name,
    _reference_type_to_csl,
    ReferenceFormatter,
)


class TestResolveCslPath:
    def test_none_publisher(self):
        from app.models import Reference, ReferenceType

        assert _resolve_csl_path(None) is None

    def test_empty_publisher(self):
        assert _resolve_csl_path("") is None

    def test_unknown_publisher(self):
        assert _resolve_csl_path("nonexistent_pub") is None


class TestParseAuthorName:
    def test_comma_separated(self):
        result = _parse_author_name("Smith, J.")
        assert result["family"] == "Smith"
        assert result["given"] == "J."

    def test_space_separated(self):
        result = _parse_author_name("Jane Doe")
        assert result["family"] == "Doe"
        assert result["given"] == "Jane"

    def test_single_name(self):
        result = _parse_author_name("Aristotle")
        assert result["family"] == "Aristotle"

    def test_empty_name(self):
        result = _parse_author_name("")
        assert result["family"] == "Unknown"

    def test_only_spaces(self):
        result = _parse_author_name("   ")
        assert result["family"] == "Unknown"

    def test_comma_no_given(self):
        result = _parse_author_name("Aristotle,")
        assert result["family"] == "Aristotle"


class TestReferenceTypeToCsl:
    def test_journal_article(self):
        ref = Reference(reference_id="r1", citation_key="k", raw_text="t", index=1,
                        reference_type=ReferenceType.JOURNAL_ARTICLE)
        assert _reference_type_to_csl(ref) == "article-journal"

    def test_book(self):
        ref = Reference(reference_id="r1", citation_key="k", raw_text="t", index=1,
                        reference_type=ReferenceType.BOOK)
        assert _reference_type_to_csl(ref) == "book"

    def test_unknown_type(self):
        ref = Reference(reference_id="r1", citation_key="k", raw_text="t", index=1,
                        reference_type=ReferenceType.UNKNOWN)
        assert _reference_type_to_csl(ref) == "article"


class TestReferenceFormatter:
    @pytest.fixture
    def mock_contract_loader(self):
        loader = MagicMock()
        loader.load.return_value = {
            "references": {"style": "IEEE"},
        }
        return loader

    def test_format_ieee_legacy(self, mock_contract_loader):
        formatter = ReferenceFormatter(mock_contract_loader)
        ref = Reference(
            reference_id="r1", citation_key="k", raw_text="test", index=1,
            number=1, title="Test Title",
            authors=["Smith, J.", "Doe, A."],
            journal="Test Journal", year=2023,
        )
        result = formatter._format_legacy(ref, "ieee")
        assert "[1]" in result
        assert "Smith, J." in result
        assert "Test Title" in result
        assert "Test Journal" in result

    def test_format_ieee_legacy_no_authors(self, mock_contract_loader):
        formatter = ReferenceFormatter(mock_contract_loader)
        ref = Reference(
            reference_id="r1", citation_key="k", raw_text="test", index=1,
            number=2, title="Untitled",
        )
        result = formatter._format_legacy(ref, "ieee")
        assert "[2]" in result

    def test_format_none_style(self, mock_contract_loader):
        formatter = ReferenceFormatter(mock_contract_loader)
        loader = MagicMock()
        loader.load.return_value = {
            "references": {"style": "none"},
        }
        formatter.contract_loader = loader
        ref = Reference(
            reference_id="r1", citation_key="k",
            raw_text="  Some   raw  reference  ", index=1,
        )
        result = formatter._format_legacy(ref, "none")
        assert result == "Some raw reference"

    def test_format_reference_single(self, mock_contract_loader):
        formatter = ReferenceFormatter(mock_contract_loader)
        ref = Reference(
            reference_id="r1", citation_key="k", raw_text="test", index=1,
            number=1, title="Test", authors=["Smith, J."], year=2023,
        )
        result = formatter.format_reference(ref, "ieee")
        assert "Smith" in result

    def test_format_references_list(self, mock_contract_loader):
        formatter = ReferenceFormatter(mock_contract_loader)
        refs = [
            Reference(reference_id="r1", citation_key="k1", raw_text="t1", index=1,
                      number=1, title="A", authors=["A"], year=2023),
            Reference(reference_id="r2", citation_key="k2", raw_text="t2", index=2,
                      number=2, title="B", authors=["B"], year=2024),
        ]
        results = formatter.format_references(refs, "ieee")
        assert len(results) == 2

    def test_format_non_ieee_non_none_style(self, mock_contract_loader):
        formatter = ReferenceFormatter(mock_contract_loader)
        loader = MagicMock()
        loader.load.return_value = {
            "references": {"style": "other"},
        }
        formatter.contract_loader = loader
        ref = Reference(reference_id="r1", citation_key="k", raw_text="raw ref text", index=1)
        result = formatter._format_legacy(ref, "other")
        assert result == "raw ref text"
