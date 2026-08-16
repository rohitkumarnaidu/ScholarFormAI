from unittest.mock import MagicMock, patch

import pytest


class TestCrossRefClient:
    @pytest.fixture
    def client(self):
        from app.services.crossref_client import CrossRefClient

        return CrossRefClient(contact_email="test@example.com")

    def test_validate_citation_too_short(self, client):
        result = client.validate_citation("short")
        assert result == {}

    def test_validate_citation_empty(self, client):
        result = client.validate_citation("")
        assert result == {}

    def test_get_cache_no_redis(self, client):
        with patch("app.services.crossref_client.HAS_REDIS", False):
            assert client._get_cache("test") is None

    def test_trim_cache(self, client):
        with patch("app.services.crossref_client.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "message": {
                    "items": [
                        {
                            "DOI": "10.123/test",
                            "title": ["Test"],
                            "author": [],
                            "score": 1.0,
                            "URL": "https://doi.org/test",
                        }
                    ]
                }
            }
            for i in range(2500):
                client._api_cache[f"key_{i}"] = {"data": i}
            client.validate_citation("test query")
        assert len(client._api_cache) <= 2001


class TestCitationAssemblyService:
    @pytest.fixture
    def svc(self):
        from app.services.citation_assembly_service import CitationAssemblyService

        svc = CitationAssemblyService()
        svc.crossref = MagicMock()
        svc.csl_engine = MagicMock()
        return svc

    @pytest.mark.asyncio
    async def test_extract_citations_empty(self, svc):
        result = await svc.extract_citations("")
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_author_year_parens(self, svc):
        result = await svc.extract_citations("(Smith 2020) and (Jones 2021)")
        assert len(result) == 2
        assert "Smith 2020" in result
        assert "Jones 2021" in result

    @pytest.mark.asyncio
    async def test_extract_numeric_brackets(self, svc):
        result = await svc.extract_citations("as shown in [1, 2, 3]")
        assert result == ["1", "2", "3"]

    @pytest.mark.asyncio
    async def test_lookup_citations(self, svc):
        svc.crossref.validate_citation.return_value = {"doi": "10.123/test"}
        results = await svc.lookup_citations(["Smith 2020"])
        assert len(results) == 1
        assert results[0]["doi"] == "10.123/test"
        assert results[0]["raw"] == "Smith 2020"

    @pytest.mark.asyncio
    async def test_lookup_citations_failure(self, svc):
        svc.crossref.validate_citation.side_effect = RuntimeError("API error")
        results = await svc.lookup_citations(["Smith 2020"])
        assert len(results) == 1
        assert "raw" in results[0]

    def test_normalize(self):
        from app.services.citation_assembly_service import CitationAssemblyService

        result = CitationAssemblyService._normalize("  Hello   World ")
        assert result == "Hello World"

    def test_replace_citations(self):
        from app.services.citation_assembly_service import CitationAssemblyService

        svc = CitationAssemblyService()
        svc.crossref = MagicMock()
        svc.csl_engine = MagicMock()
        mapping = {"Smith 2020": 1, "Jones 2021": 2}
        text = "(Smith 2020) and [Jones 2021]"
        result = svc._replace_citations(text, mapping)
        assert "[1]" in result
        assert "[2]" in result
