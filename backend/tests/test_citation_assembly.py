# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCitationAssemblyExtractCitations:
    @pytest.fixture
    def service(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"), \
             patch("app.services.citation_assembly_service.CSLEngine"):
            yield CitationAssemblyService()

    async def test_empty_content(self, service):
        result = await service.extract_citations("")
        assert result == []

    async def test_none_content(self, service):
        result = await service.extract_citations(None)
        assert result == []

    async def test_author_year_parens(self, service):
        result = await service.extract_citations("(Smith 2020)")
        assert "Smith 2020" in result

    async def test_author_year_brackets(self, service):
        result = await service.extract_citations("[Smith 2020]")
        assert "Smith 2020" in result

    async def test_numeric_brackets(self, service):
        result = await service.extract_citations("[1]")
        assert "1" in result

    async def test_multiple_numeric(self, service):
        result = await service.extract_citations("[1, 2, 3]")
        assert "1" in result
        assert "2" in result
        assert "3" in result

    async def test_mixed_citations(self, service):
        text = "As (Smith 2020) showed and [1] confirms"
        result = await service.extract_citations(text)
        assert "Smith 2020" in result
        assert "1" in result

    async def test_duplicates_removed(self, service):
        text = "(Smith 2020) and [Smith 2020]"
        result = await service.extract_citations(text)
        assert len(result) == 1

    async def test_no_citations(self, service):
        result = await service.extract_citations("Plain text without citations")
        assert result == []

    async def test_author_year_with_etal(self, service):
        result = await service.extract_citations("(Smith et al. 2020)")
        assert "Smith et al. 2020" in result

    async def test_multiple_author_year(self, service):
        text = "One study (Smith 2020) and another (Jones 2021)"
        result = await service.extract_citations(text)
        assert "Smith 2020" in result
        assert "Jones 2021" in result

    async def test_author_year_with_page(self, service):
        result = await service.extract_citations("(Smith 2020, p. 15)")
        assert result == []


class TestCitationAssemblyNormalize:
    @pytest.fixture
    def service(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        return CitationAssemblyService()

    def test_trims_whitespace(self, service):
        result = service._normalize("  hello  world  ")
        assert result == "hello world"

    def test_collapses_spaces(self, service):
        result = service._normalize("hello   world")
        assert result == "hello world"

    def test_empty_string(self, service):
        result = service._normalize("")
        assert result == ""

    def test_no_change_needed(self, service):
        result = service._normalize("Smith 2020")
        assert result == "Smith 2020"


class TestCitationAssemblyLookupCitations:
    @pytest.fixture
    def service(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client") as mock_gcc, \
             patch("app.services.citation_assembly_service.CSLEngine"):
            mock_client = MagicMock()
            mock_client.validate_citation.return_value = {"title": "Test Paper"}
            mock_gcc.return_value = mock_client
            yield CitationAssemblyService()

    async def test_empty_list(self, service):
        result = await service.lookup_citations([])
        assert result == []

    async def test_single_citation(self, service):
        result = await service.lookup_citations(["Smith 2020"])
        assert len(result) == 1
        assert result[0]["raw"] == "Smith 2020"
        assert result[0]["title"] == "Test Paper"

    async def test_multiple_citations(self, service):
        result = await service.lookup_citations(["Smith 2020", "Jones 2021"])
        assert len(result) == 2

    async def test_lookup_failure(self, service):
        service.crossref.validate_citation.side_effect = Exception("API error")
        result = await service.lookup_citations(["Smith 2020"])
        assert len(result) == 1
        assert result[0]["raw"] == "Smith 2020"


class TestCitationAssemblyFormatReferences:
    @pytest.fixture
    def service(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"), \
             patch("app.services.citation_assembly_service.CSLEngine") as mock_csl:
            engine = MagicMock()
            engine.format_references.return_value = ["[1] Smith, J. (2020). Test."]
            mock_csl.return_value = engine
            yield CitationAssemblyService()

    async def test_empty_citations(self, service):
        result = await service.format_references([], "apa")
        assert result == ""

    async def test_single_reference(self, service):
        citations = [{"raw": "Smith 2020", "authors": "Smith", "title": "Test"}]
        result = await service.format_references(citations, "apa")
        assert "Smith" in result

    async def test_multiple_references(self, service):
        service.csl_engine.format_references.return_value = [
            "[1] Smith, J. (2020). A.",
            "[2] Jones, K. (2021). B.",
        ]
        citations = [
            {"raw": "Smith 2020", "authors": "Smith", "title": "A"},
            {"raw": "Jones 2021", "authors": "Jones", "title": "B"},
        ]
        result = await service.format_references(citations, "apa")
        assert len(result.split("\n")) == 2

    async def test_missing_authors(self, service):
        citations = [{"raw": "Unknown"}]
        result = await service.format_references(citations, "apa")
        assert result != ""

    async def test_empty_authors_string(self, service):
        citations = [{"raw": "Test", "authors": ""}]
        result = await service.format_references(citations, "apa")
        assert result != ""


class TestCitationAssemblyReplaceCitations:
    @pytest.fixture
    def service(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        return CitationAssemblyService()

    def test_empty_text(self, service):
        result = service._replace_citations("", {"Smith 2020": 1})
        assert result == ""

    def test_replace_author_year_parens(self, service):
        result = service._replace_citations("(Smith 2020)", {"Smith 2020": 1})
        assert result == "[1]"

    def test_replace_author_year_brackets(self, service):
        result = service._replace_citations("[Smith 2020]", {"Smith 2020": 1})
        assert result == "[1]"

    def test_replace_numeric(self, service):
        result = service._replace_citations("[1]", {"1": 3})
        assert result == "[3]"

    def test_replace_mixed(self, service):
        text = "See (Smith 2020) and [Jones 2021]"
        mapping = {"Smith 2020": 1, "Jones 2021": 2}
        result = service._replace_citations(text, mapping)
        assert result == "See [1] and [2]"

    def test_no_mapping_found(self, service):
        result = service._replace_citations("(Unknown 1999)", {"Smith 2020": 1})
        assert result == "(Unknown 1999)"


class TestCitationAssemblyAssemble:
    @pytest.fixture
    def service(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client") as mock_gcc, \
             patch("app.services.citation_assembly_service.CSLEngine") as mock_csl:
            mock_client = MagicMock()
            mock_client.validate_citation.return_value = {"title": "Paper"}
            mock_gcc.return_value = mock_client
            engine = MagicMock()
            engine.format_references.return_value = ["[1] Smith, J. (2020). Paper."]
            mock_csl.return_value = engine
            yield CitationAssemblyService()

    async def test_assemble_updates_sections(self, service):
        sections = {"intro": "As (Smith 2020) shows", "methods": "Standard approach"}
        sections_out, refs = await service.assemble(sections, "apa")
        assert "[1]" in sections_out["intro"]
        assert refs != ""


class TestCitationAssemblyInit:
    def test_initializes_crossref_and_csl(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client") as mock_gcc, \
             patch("app.services.citation_assembly_service.CSLEngine") as mock_csl:
            mock_gcc.return_value = MagicMock()
            mock_csl.return_value = MagicMock()
            svc = CitationAssemblyService()
            assert svc.crossref is not None
            assert svc.csl_engine is not None
