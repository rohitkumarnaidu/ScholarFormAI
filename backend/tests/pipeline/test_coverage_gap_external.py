# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Supplementary coverage tests for grobid_client, docling_client, and crossref_client."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
pytestmark = [pytest.mark.pipeline]


# ==============================================================================
# GROBID Client Supplementary Tests
# ==============================================================================

SAMPLE_TEI_XML = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title type="main">Test Paper Title</title>
      </titleStmt>
      <sourceDesc>
        <biblStruct>
          <analytic>
            <author>
              <persName>
                <forename type="first">John</forename>
                <surname>Smith</surname>
              </persName>
              <affiliation>
                <orgName type="institution">MIT</orgName>
              </affiliation>
            </author>
          </analytic>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract>
        <p>This is an abstract.</p>
      </abstract>
      <textClass>
        <keywords>
          <term>machine learning</term>
          <term>NLP</term>
        </keywords>
      </textClass>
    </profileDesc>
  </teiHeader>
</TEI>"""


@pytest.fixture
def grobid_mock_settings():
    with patch("app.pipeline.services.grobid_client.settings") as mock:
        mock.get_grobid_urls.return_value = []
        mock.GROBID_URL = "http://localhost:8070"
        mock.get_service_health_path.return_value = "/api/isalive"
        mock.GROBID_TIMEOUT = 15
        mock.GROBID_MAX_RETRIES = 2
        mock.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        yield mock


@pytest.fixture
def grobid_client(grobid_mock_settings):
    from app.pipeline.services.grobid_client import GROBIDClient
    return GROBIDClient()


class TestGROBIDClientInitCoverage:
    """Target: lines 75, 92-93, pybreaker import failure."""

    def test_health_path_single_char_no_rstrip(self, grobid_mock_settings):
        """health_path length == 1 skips rstrip (target line 75 false branch)."""
        grobid_mock_settings.get_service_health_path.return_value = "/"
        from app.pipeline.services.grobid_client import GROBIDClient
        c = GROBIDClient()
        assert c.health_path == "/"

    def test_pybreaker_import_failure(self, grobid_mock_settings):
        """pybreaker import falls back to None (target lines 38-39)."""
        grobid_mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = True
        with patch("app.pipeline.services.grobid_client.pybreaker", None):
            from app.pipeline.services.grobid_client import GROBIDClient
            c = GROBIDClient()
            assert c.breaker is None

    def test_circuit_breaker_remote_hosted(self, grobid_mock_settings):
        """Remote hosted adjusts circuit breaker thresholds (target lines 92-93)."""
        grobid_mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = True
        with patch("app.pipeline.services.grobid_client.pybreaker") as mock_pybreaker:
            mock_breaker = MagicMock()
            mock_pybreaker.CircuitBreaker.return_value = mock_breaker
            from app.pipeline.services.grobid_client import GROBIDClient
            c = GROBIDClient(base_url="https://remote-grobid.example.com")
            assert c.breaker is not None
            assert c._remote_hosted is True
            _, kwargs = mock_pybreaker.CircuitBreaker.call_args
            assert kwargs["fail_max"] >= 6
            assert kwargs["reset_timeout"] <= 30


class TestGROBIDClientRequestCoverage:
    """Target: line 134 (timeout in kwargs)."""

    def test_request_with_explicit_timeout(self, grobid_client):
        """_request with timeout kwarg skips default timeout logic."""
        with patch("app.pipeline.services.grobid_client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            resp = grobid_client._request("GET", "http://localhost/test", timeout=(5.0, 10.0))
            assert resp.status_code == 200
            mock_req.assert_called_once_with("GET", "http://localhost/test", timeout=(5.0, 10.0))


class TestGROBIDClientProcessHeaderFailover:
    """Target: lines 179->245, 231-243, 246 (failover, generic exception, endpoint switch)."""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_generic_exception_triggers_retry(self, mock_request, grobid_client, tmp_path):
        """Non-RequestException in header processing retries (target lines 231-243)."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = [
            AttributeError("no status_code"),
            MagicMock(status_code=200, text=SAMPLE_TEI_XML),
        ]
        result = grobid_client.process_header_document(str(pdf))
        assert result["title"] == "Test Paper Title"
        assert mock_request.call_count == 2

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_generic_exception_all_retries_exhausted(self, mock_request, grobid_client, tmp_path):
        """Generic exception exhausts all retries and returns empty (target lines 232-243)."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = AttributeError("persistent error")
        result = grobid_client.process_header_document(str(pdf))
        assert result["title"] == ""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_endpoint_failover(self, mock_request, grobid_client, tmp_path):
        """Failover from first endpoint to second (target lines 179->245, 246)."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        grobid_client.base_urls = ["http://url1:8070", "http://url2:8070"]
        mock_request.side_effect = [
            MagicMock(status_code=502, text=""),
            MagicMock(status_code=200, text=SAMPLE_TEI_XML),
        ]
        result = grobid_client.process_header_document(str(pdf))
        assert result["title"] == "Test Paper Title"

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_all_endpoints_exhausted(self, mock_request, grobid_client, tmp_path):
        """All endpoints fail, returns empty metadata."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        grobid_client.base_urls = ["http://url1:8070", "http://url2:8070"]
        mock_request.return_value = MagicMock(status_code=503, text="")
        result = grobid_client.process_header_document(str(pdf))
        assert result["title"] == ""


class TestGROBIDClientProcessReferencesCoverage:
    """Target: lines 282, 298-306 (non-transient break, generic exception, failover)."""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_non_transient_status_breaks(self, mock_request, grobid_client, tmp_path):
        """Non-transient status (404) breaks out immediately (target line 282)."""
        from app.pipeline.services.grobid_client import GROBIDClient
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        with patch.object(GROBIDClient, "is_available", return_value=True):
            mock_request.return_value = MagicMock(status_code=404)
            result = grobid_client.process_references(str(pdf))
            assert result == []

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_generic_exception_refs_retries_then_breaks(self, mock_request, grobid_client, tmp_path):
        """Generic exception exhausts retries in refs (target lines 287-298)."""
        from app.pipeline.services.grobid_client import GROBIDClient
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        with patch.object(GROBIDClient, "is_available", return_value=True):
            mock_request.side_effect = RuntimeError("unexpected error")
            result = grobid_client.process_references(str(pdf))
            assert result == []

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_refs_endpoint_failover(self, mock_request, grobid_client, tmp_path):
        """References failover between endpoints (target lines 298-306)."""
        from app.pipeline.services.grobid_client import GROBIDClient
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        grobid_client.base_urls = ["http://url1:8070", "http://url2:8070"]
        with patch.object(GROBIDClient, "is_available", return_value=True):
            mock_request.side_effect = [
                RuntimeError("fail"),
                MagicMock(status_code=200),
            ]
            result = grobid_client.process_references(str(pdf))
            assert result == []


class TestGROBIDClientParsingBranchCoverage:
    """Target: lines 404->414, 408->410, 410->414, 420->398, 438-439, 447->446."""

    def test_extract_authors_no_persname(self, grobid_client):
        """Author element without persName (target 404->414)."""
        import xml.etree.ElementTree as ET
        xml = """<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader>
          <fileDesc><titleStmt><title>T</title></titleStmt>
          <sourceDesc><biblStruct><analytic>
            <author>
              <persName>
                <forename type="first"></forename>
                <surname></surname>
              </persName>
              <affiliation><orgName type="institution">MIT</orgName></affiliation>
            </author>
            <author>
              <affiliation><orgName type="institution">Stanford</orgName></affiliation>
            </author>
          </analytic></biblStruct></sourceDesc></fileDesc></teiHeader></TEI>"""
        root = ET.fromstring(xml)
        authors, affiliations = grobid_client._extract_authors(root)
        assert len(authors) == 0
        assert "MIT" in affiliations

    def test_extract_abstract_direct_text(self, grobid_client):
        """Abstract with direct text, no <p> tags (target lines 438-439)."""
        import xml.etree.ElementTree as ET
        xml = """<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader>
          <fileDesc><titleStmt><title>T</title></titleStmt><sourceDesc/></fileDesc>
          <profileDesc><abstract>Direct abstract text here.</abstract></profileDesc></teiHeader></TEI>"""
        root = ET.fromstring(xml)
        abstract = grobid_client._extract_abstract(root)
        assert abstract == "Direct abstract text here."

    def test_extract_keywords_with_empty_term(self, grobid_client):
        """Keywords with empty term element (target line 447 false branch)."""
        import xml.etree.ElementTree as ET
        xml = """<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader>
          <fileDesc><titleStmt><title>T</title></titleStmt><sourceDesc/></fileDesc>
          <profileDesc><textClass><keywords>
            <term>valid</term>
            <term></term>
          </keywords></textClass></profileDesc></teiHeader></TEI>"""
        root = ET.fromstring(xml)
        keywords = grobid_client._extract_keywords(root)
        assert keywords == ["valid"]

    def test_calculate_confidence_incomplete_names(self, grobid_client):
        """Partial name completeness (target line 474 false branch)."""
        score = grobid_client._calculate_confidence("Long Title Here", [
            {"given": "John", "family": ""},
            {"given": "", "family": "Doe"},
        ])
        assert 0.8 <= score <= 0.95


class TestGROBIDExtractMetadataEdgeCases:
    """Target: extract_metadata edge paths."""

    def test_extract_metadata_empty_header_no_refs(self, grobid_client):
        """Metadata with empty header returns {} before refs."""
        from app.pipeline.services.grobid_client import GROBIDClient
        with patch.object(GROBIDClient, "is_available", return_value=True):
            with patch.object(grobid_client, "process_header_document", return_value={}):
                result = grobid_client.extract_metadata("test.pdf")
                assert result == {}

    def test_extract_metadata_none_refs(self, grobid_client):
        """None references become empty list."""
        from app.pipeline.services.grobid_client import GROBIDClient
        with patch.object(GROBIDClient, "is_available", return_value=True):
            with patch.object(grobid_client, "process_header_document", return_value={"title": "Test"}):
                with patch.object(grobid_client, "process_references", return_value=None):
                    result = grobid_client.extract_metadata("test.pdf")
                    assert result["references"] == []


# ==============================================================================
# Docling Client Supplementary Tests
# ==============================================================================

@pytest.fixture
def docling_mock_settings():
    with patch("app.pipeline.services.docling_client.settings.USE_DOCLING_FALLBACK", True):
        with patch("app.pipeline.services.docling_client.settings.LOW_MEMORY_MODE", False):
            yield


class TestDoclingClientModuleCoverage:
    """Target: _load_docling_converter lines 67, 75-77."""

    def test_load_converter_not_available(self, docling_mock_settings):
        """DOCLING_AVAILABLE=False returns None early (target line 67)."""
        with patch("app.pipeline.services.docling_client.DOCLING_AVAILABLE", False):
            from app.pipeline.services.docling_client import _load_docling_converter
            result = _load_docling_converter()
            assert result is None

    def test_load_converter_import_exception(self):
        """Docling import raises exception (target lines 75-77)."""
        import app.pipeline.services.docling_client as docling_mod
        with patch("app.pipeline.services.docling_client.DOCLING_AVAILABLE", True):
            with patch("app.pipeline.services.docling_client.importlib.util.find_spec", return_value=True):
                with patch("builtins.__import__", side_effect=Exception("Import failed")):
                    result = docling_mod._load_docling_converter()
                    assert result is None

    def test_docling_enabled_low_memory(self):
        """_docling_enabled returns False in low memory mode."""
        with patch("app.pipeline.services.docling_client.settings.USE_DOCLING_FALLBACK", True):
            with patch("app.pipeline.services.docling_client.settings.LOW_MEMORY_MODE", True):
                from app.pipeline.services.docling_client import _docling_enabled
                assert _docling_enabled() is False


class TestDoclingClientAnalyzeLayoutEdgeCoverage:
    """Target: analyze_layout uncovered branches."""

    def test_analyze_converter_is_none_at_runtime(self, docling_mock_settings):
        """Converter becomes None between init and analyze (target lines 218-219)."""
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            c.converter = None
            result = c.analyze_layout("test.pdf")
            assert result["elements"] == []

    def test_analyze_outer_exception_handler(self, docling_mock_settings):
        """Outer try/except in analyze_layout catches broad exceptions (target lines 291-293)."""
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            mock_doc = MagicMock()
            type(mock_doc).texts = PropertyMock(side_effect=Exception("Iteration error"))
            mock_doc.tables = []
            type(mock_doc).num_pages = PropertyMock(return_value=1)
            mock_conv.convert.return_value.document = mock_doc
            result = c.analyze_layout("test.pdf")
            assert result["elements"] == []
            assert result["pages"] == 0

    def test_analyze_table_empty_grid(self, docling_mock_settings):
        """Table with empty data.grid doesn't crash (target line 258)."""
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            mock_doc = MagicMock()
            mock_doc.texts = []
            mock_table = MagicMock()
            bbox_mock = MagicMock()
            bbox_mock.l = 10
            bbox_mock.t = 100
            bbox_mock.r = 500
            bbox_mock.b = 300
            mock_table.prov = [MagicMock(bbox=bbox_mock, page_no=1)]
            mock_table.data.grid = []
            mock_doc.tables = [mock_table]
            mock_doc.num_pages = 1
            mock_conv.convert.return_value.document = mock_doc
            result = c.analyze_layout("test.pdf")
            assert len(result["elements"]) == 1
            assert result["elements"][0]["type"] == "table"
            assert result["elements"][0]["rows"] == 0


class TestDoclingClientHeadersFootersCoverage:
    """Target: _detect_headers_footers empty page branch."""

    def test_detect_headers_footers_empty_page(self):
        """Empty page in element grouping skips processing."""
        from app.pipeline.services.docling_client import DoclingClient, BoundingBox, LayoutElement
        c = DoclingClient()
        p1_body = LayoutElement(text="Body", bbox=BoundingBox(0, 200, 100, 400, page=1), element_type="text")
        p2_body = LayoutElement(text="P2 Body", bbox=BoundingBox(0, 200, 100, 400, page=2), element_type="text")
        headers, footers = c._detect_headers_footers([p1_body, p2_body])
        assert headers == []
        assert footers == []


class TestDoclingClientExtractElementsCoverage:
    """Target: _extract_elements with bbox missing page attribute."""

    def test_extract_elements_bbox_no_page(self):
        """BBox without page attribute defaults to 0."""
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.bbox.l = 0
        mock_item.bbox.t = 0
        mock_item.bbox.r = 100
        mock_item.bbox.b = 50
        del mock_item.bbox.page
        mock_item.text = "No page"
        mock_item.label = "text"
        mock_item.prov = []
        mock_doc.iterate_items.return_value = [mock_item]
        elements = c._extract_elements(mock_doc)
        assert len(elements) == 1
        assert elements[0].bbox.page == 0


# ==============================================================================
# CrossRef Client Supplementary Tests (proper async)
# ==============================================================================

class TestCrossRefClientInit:
    """Test __init__ paths."""

    def test_init_with_email(self):
        from app.pipeline.services.crossref_client import CrossRefClient
        client = CrossRefClient(email="researcher@example.com")
        assert "User-Agent" in client.headers
        assert "researcher@example.com" in client.headers["User-Agent"]
        assert client.last_request_time == 0.0

    def test_init_without_email(self):
        from app.pipeline.services.crossref_client import CrossRefClient
        client = CrossRefClient()
        assert client.headers == {}
        assert client.last_request_time == 0.0


class TestCrossRefClientAsync:
    """Proper async tests for CrossRef async methods."""

    @pytest.fixture
    def crossref_client(self):
        from app.pipeline.services.crossref_client import CrossRefClient
        return CrossRefClient(email="test@example.com")

    async def test_validate_doi_found(self, crossref_client):
        with patch.object(crossref_client, "get_metadata") as mock_get:
            mock_get.return_value = {"title": ["Found"]}
            result = await crossref_client.validate_doi("10.1234/test")
            assert result is True

    async def test_validate_doi_not_found(self, crossref_client):
        from app.pipeline.services.crossref_client import CrossRefException
        with patch.object(crossref_client, "get_metadata") as mock_get:
            mock_get.side_effect = CrossRefException("Not found")
            result = await crossref_client.validate_doi("10.1234/missing")
            assert result is False

    @patch("app.pipeline.services.crossref_client.httpx.AsyncClient")
    async def test_get_metadata_success(self, mock_client, crossref_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"title": ["Test Paper"]}}
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get.return_value = mock_response
        result = await crossref_client.get_metadata("10.1234/test")
        assert result["title"] == ["Test Paper"]
        mock_instance.get.assert_called_once()

    @patch("app.pipeline.services.crossref_client.httpx.AsyncClient")
    async def test_get_metadata_doi_stripped(self, mock_client, crossref_client):
        """DOI whitespace is stripped before request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"title": ["Test"]}}
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get.return_value = mock_response
        result = await crossref_client.get_metadata("  10.1234/test  ")
        assert result["title"] == ["Test"]
        call_url = mock_instance.get.call_args[0][0]
        assert "10.1234/test" in call_url
        assert "  " not in call_url

    @patch("app.pipeline.services.crossref_client.httpx.AsyncClient")
    async def test_get_metadata_404(self, mock_client, crossref_client):
        from app.pipeline.services.crossref_client import CrossRefException
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get.return_value = mock_response
        with pytest.raises(CrossRefException, match="DOI not found"):
            await crossref_client.get_metadata("10.1234/missing")

    @patch("app.pipeline.services.crossref_client.httpx.AsyncClient")
    async def test_get_metadata_api_error(self, mock_client, crossref_client):
        from app.pipeline.services.crossref_client import CrossRefException
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get.return_value = mock_response
        with pytest.raises(CrossRefException, match="API error"):
            await crossref_client.get_metadata("10.1234/error")

    @patch("app.pipeline.services.crossref_client.httpx.AsyncClient")
    async def test_get_metadata_network_error(self, mock_client, crossref_client):
        from app.pipeline.services.crossref_client import CrossRefException
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get.side_effect = __import__("httpx").HTTPError("No connection")
        with pytest.raises(CrossRefException, match="Network error"):
            await crossref_client.get_metadata("10.1234/netfail")

    async def test_wait_for_rate_limit_sleeps(self, crossref_client):
        """Rate limit interval exceeded triggers sleep."""
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.time.side_effect = [100.0, 100.01]
            mock_loop.return_value = mock_loop_instance
            with patch.object(crossref_client, "MIN_REQUEST_INTERVAL", 0.5):
                with patch("asyncio.sleep") as mock_sleep:
                    crossref_client.last_request_time = 100.0
                    await crossref_client._wait_for_rate_limit()
                    mock_sleep.assert_called_once()
                    mock_loop_instance.time.assert_called()

    async def test_wait_for_rate_limit_no_sleep(self, crossref_client):
        """Rate limit not exceeded skips sleep."""
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.time.return_value = 200.0
            mock_loop.return_value = mock_loop_instance
            with patch("asyncio.sleep") as mock_sleep:
                crossref_client.last_request_time = 100.0
                await crossref_client._wait_for_rate_limit()
                mock_sleep.assert_not_called()


class TestCrossRefClientConfidenceBranchCoverage:
    """Target: branch coverage in calculate_confidence."""

    @pytest.fixture
    def crossref_client(self):
        from app.pipeline.services.crossref_client import CrossRefClient
        return CrossRefClient()

    def test_year_mismatch(self, crossref_client):
        """Year present but doesn't match."""
        ref_data = {"title": "Deep Learning", "year": 2017}
        cr_data = {
            "title": ["Deep Learning"],
            "published-print": {"date-parts": [[2016]]},
        }
        score = crossref_client.calculate_confidence(ref_data, cr_data)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_year_missing_in_ref(self, crossref_client):
        """No year in reference data."""
        ref_data = {"title": "Test"}
        cr_data = {"title": ["Test"], "published-print": {"date-parts": [[2016]]}}
        score = crossref_client.calculate_confidence(ref_data, cr_data)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_author_not_found(self, crossref_client):
        """Author in reference but not matching crossref."""
        ref_data = {"authors": ["Smith, John"], "title": "Title", "year": 2020}
        cr_data = {"title": ["Title"], "published-print": {"date-parts": [[2020]]}, "author": [{"family": "Doe", "given": "Jane"}]}
        score = crossref_client.calculate_confidence(ref_data, cr_data)
        assert score == pytest.approx(0.8, abs=0.01)

    def test_no_title_no_year_no_authors(self, crossref_client):
        """No data at all returns 0.0."""
        score = crossref_client.calculate_confidence({}, {})
        assert score == 0.0

    def test_author_partial_match_from_full_name(self, crossref_client):
        """Author family found in reference full name string."""
        ref_data = {"title": "Deep Learning", "authors": ["Goodfellow, Ian", "Smith"], "year": 2016}
        cr_data = {
            "title": ["Deep Learning"],
            "published-online": {"date-parts": [[2016]]},
            "author": [{"family": "Goodfellow", "given": "Ian"}],
        }
        score = crossref_client.calculate_confidence(ref_data, cr_data)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_confidence_title_no_author_check_found(self, crossref_client):
        """Title match without author but with insufficient data."""
        ref_data = {"title": "Exact Match Title", "year": 2020}
        cr_data = {
            "title": ["Exact Match Title"],
            "published-print": {"date-parts": [[2019]]},
        }
        score = crossref_client.calculate_confidence(ref_data, cr_data)
        assert score == pytest.approx(0.5, abs=0.01)


class TestCrossRefException:
    """Test CrossRefException constructors."""

    def test_default_message(self):
        from app.pipeline.services.crossref_client import CrossRefException
        exc = CrossRefException()
        assert "CrossRef" in str(exc)

    def test_custom_message(self):
        from app.pipeline.services.crossref_client import CrossRefException
        exc = CrossRefException("Custom error message")
        assert "Custom" in str(exc)
