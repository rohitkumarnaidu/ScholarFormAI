from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCitationAssemblyService:
    def test_init(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                assert svc is not None

    @pytest.mark.asyncio
    async def test_extract_citations_empty(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.extract_citations("")
                assert result == []

    @pytest.mark.asyncio
    async def test_extract_citations_author_year(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.extract_citations("According to (Smith 2020), the sky is blue.")
                assert "Smith 2020" in result

    @pytest.mark.asyncio
    async def test_extract_citations_numeric(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.extract_citations("As shown in [1, 2, 3]")
                assert "1" in result
                assert "2" in result
                assert "3" in result

    @pytest.mark.asyncio
    async def test_lookup_citations_empty(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.lookup_citations([])
                assert result == []

    @pytest.mark.asyncio
    async def test_lookup_citations_success(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        mock_crossref = MagicMock()
        mock_crossref.validate_citation.return_value = {"doi": "10.1234/test", "title": "Test"}
        with patch("app.services.citation_assembly_service.get_crossref_client", return_value=mock_crossref):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.lookup_citations(["Smith 2020"])
                assert len(result) == 1
                assert result[0]["doi"] == "10.1234/test"

    @pytest.mark.asyncio
    async def test_lookup_citations_failure(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        mock_crossref = MagicMock()
        mock_crossref.validate_citation.side_effect = Exception("not found")
        with patch("app.services.citation_assembly_service.get_crossref_client", return_value=mock_crossref):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.lookup_citations(["Unknown 2099"])
                assert len(result) == 1
                assert "raw" in result[0]

    def test_normalize(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        result = CitationAssemblyService._normalize("  Hello   World  ")
        assert result == "Hello World"

    def test_replace_citations_empty(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
        result = svc._replace_citations("", {"a": 1})
        assert result == ""

    def test_replace_citations_author_year(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
        result = svc._replace_citations("(Smith 2020) says", {"Smith 2020": 1})
        assert "[1]" in result

    def test_replace_citations_numeric(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
        result = svc._replace_citations("[1, 2]", {"1": 3, "2": 4})
        assert "[3, 4]" in result

    @pytest.mark.asyncio
    async def test_format_references_empty(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.format_references([], "apa")
                assert result == ""

    @pytest.mark.asyncio
    async def test_format_references_with_data(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        mock_csl = MagicMock()
        mock_csl.format_references.return_value = ["1. J. Doe, Test, 2024.", ""]
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine", return_value=mock_csl):
                svc = CitationAssemblyService()
                citations = [{"raw": "Doe 2024", "title": "Test", "authors": "Doe, J."}]
                result = await svc.format_references(citations, "apa")
                assert "1. J. Doe, Test, 2024." in result

    @pytest.mark.asyncio
    async def test_assemble(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        mock_crossref = MagicMock()
        mock_crossref.validate_citation.return_value = {"doi": "10.1234/abc", "title": "ABC"}
        mock_csl = MagicMock()
        mock_csl.format_references.return_value = ["1. A. B, ABC, 2024."]
        with patch("app.services.citation_assembly_service.get_crossref_client", return_value=mock_crossref):
            with patch("app.services.citation_assembly_service.CSLEngine", return_value=mock_csl):
                svc = CitationAssemblyService()
                sections = {"body": "According to (A B 2024), ..."}
                updated, refs = await svc.assemble(sections, "apa")
                assert "body" in updated
                assert "A B 2024" in refs or "1." in refs or refs != ""

    @pytest.mark.asyncio
    async def test_extract_citations_bracket_author_year(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
                result = await svc.extract_citations("As [Smith 2020] showed")
                assert "Smith 2020" in result

    def test_replace_citations_author_year_bracket(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
        result = svc._replace_citations("[Smith 2020] says", {"Smith 2020": 1})
        assert "[1]" in result

    def test_replace_citations_unmapped_preserved(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine"):
                svc = CitationAssemblyService()
        result = svc._replace_citations("(Unknown 1999) remains", {"Other 2000": 1})
        assert "(Unknown 1999)" in result

    @pytest.mark.asyncio
    async def test_format_references_handles_empty_authors(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        mock_csl = MagicMock()
        mock_csl.format_references.return_value = ["1. Untitled"]
        with patch("app.services.citation_assembly_service.get_crossref_client"):
            with patch("app.services.citation_assembly_service.CSLEngine", return_value=mock_csl):
                svc = CitationAssemblyService()
                result = await svc.format_references([{"raw": "Untitled"}], "apa")
                assert "1. Untitled" in result

    def test_normalize_various(self):
        from app.services.citation_assembly_service import CitationAssemblyService
        assert CitationAssemblyService._normalize(123) == "123"
        assert CitationAssemblyService._normalize("  a   b  ") == "a b"
