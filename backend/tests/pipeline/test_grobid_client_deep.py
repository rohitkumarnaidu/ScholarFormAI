from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


SAMPLE_TEI = """<?xml version="1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title type="main">Main Title</title>
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
        <p>Abstract text here.</p>
      </abstract>
      <textClass>
        <keywords>
          <term>AI</term>
          <term>ML</term>
        </keywords>
      </textClass>
    </profileDesc>
  </teiHeader>
</TEI>"""


@pytest.fixture
def mock_settings():
    with patch("app.pipeline.services.grobid_client.settings") as mock:
        mock.get_grobid_urls.return_value = []
        mock.GROBID_URL = "http://localhost:8070"
        mock.get_service_health_path.return_value = "/api/isalive"
        mock.GROBID_TIMEOUT = 15
        mock.GROBID_MAX_RETRIES = 3
        mock.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        yield mock


@pytest.fixture
def client(mock_settings):
    from app.pipeline.services.grobid_client import GROBIDClient

    return GROBIDClient()


class TestGROBIDClientInitEdgeCases:
    def test_remote_hosted_detection(self, mock_settings):
        from app.pipeline.services.grobid_client import GROBIDClient

        c = GROBIDClient(base_url="https://grobid.example.com")
        assert c._remote_hosted is True

    def test_localhost_detection(self, mock_settings):
        from app.pipeline.services.grobid_client import GROBIDClient

        c = GROBIDClient(base_url="http://127.0.0.1:8070")
        assert c._remote_hosted is False

    def test_circuit_breaker_enabled(self, mock_settings):
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = True
        with patch("app.pipeline.services.grobid_client.pybreaker") as mock_pybreaker:
            from app.pipeline.services.grobid_client import GROBIDClient

            mock_breaker = MagicMock()
            mock_pybreaker.CircuitBreaker.return_value = mock_breaker
            c = GROBIDClient()
            assert c.breaker is not None

    def test_health_path_normalization(self, mock_settings):
        mock_settings.get_service_health_path.return_value = "api/health"
        from app.pipeline.services.grobid_client import GROBIDClient

        c = GROBIDClient()
        assert c.health_path.startswith("/")

    def test_timeout_remote_hosted(self, mock_settings):
        mock_settings.GROBID_TIMEOUT = 120
        from app.pipeline.services.grobid_client import GROBIDClient

        c = GROBIDClient(base_url="https://remote.example.com")
        assert c.timeout <= 90

    def test_timeout_local(self, mock_settings):
        mock_settings.GROBID_TIMEOUT = 50
        from app.pipeline.services.grobid_client import GROBIDClient

        c = GROBIDClient(base_url="http://localhost:8070")
        assert c.timeout <= 30

    def test_empty_base_urls_fallback(self, mock_settings):
        mock_settings.get_grobid_urls.return_value = []
        from app.pipeline.services.grobid_client import GROBIDClient

        c = GROBIDClient()
        assert len(c.base_urls) >= 1
        assert "localhost" in c.base_urls[0]

    def test_base_url_override(self, mock_settings):
        from app.pipeline.services.grobid_client import GROBIDClient

        c = GROBIDClient(base_url="http://custom:8070")
        assert "custom" in c.base_url


class TestGROBIDClientEndpointUrl:
    def test_normalizes_path_with_slash(self, client):
        assert client._endpoint_url("http://localhost:8070", "/api/test") == "http://localhost:8070/api/test"

    def test_normalizes_path_without_slash(self, client):
        assert client._endpoint_url("http://localhost:8070", "api/test") == "http://localhost:8070/api/test"

    def test_strips_trailing_slash(self, client):
        assert client._endpoint_url("http://localhost:8070/", "/api/test") == "http://localhost:8070/api/test"


class TestGROBIDClientOrderedBaseUrls:
    def test_last_good_preferred(self, client):
        client.base_urls = ["http://url1:8070", "http://url2:8070", "http://url3:8070"]
        client._last_good_base_url = "http://url2:8070"
        client._last_good_at = __import__("time").monotonic()
        ordered = client._ordered_base_urls()
        assert ordered[0] == "http://url2:8070"

    def test_last_good_expired(self, client):
        client.base_urls = ["http://url1:8070", "http://url2:8070"]
        client._last_good_base_url = "http://url2:8070"
        client._last_good_at = -999999
        ordered = client._ordered_base_urls()
        assert ordered[0] != "http://url2:8070"

    def test_empty_base_urls(self, client):
        client.base_urls = []
        assert client._ordered_base_urls() == []


class TestGROBIDClientRetryBackoff:
    def test_attempt_1(self, client):
        assert client._retry_backoff_seconds(1) == 1.0

    def test_attempt_2(self, client):
        assert client._retry_backoff_seconds(2) == 2.0

    def test_attempt_3(self, client):
        assert client._retry_backoff_seconds(3) == 4.0

    def test_attempt_4_capped(self, client):
        assert client._retry_backoff_seconds(4) == 8.0

    def test_attempt_5_capped(self, client):
        assert client._retry_backoff_seconds(5) == 8.0


class TestGROBIDClientRequest:
    def test_request_without_breaker(self, client):
        client.breaker = None
        with patch("app.pipeline.services.grobid_client.requests.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            resp = client._request("GET", "http://localhost/test")
            assert resp.status_code == 200

    def test_request_with_breaker(self, mock_settings, client):
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = True
        with patch("app.pipeline.services.grobid_client.pybreaker") as mock_pybreaker:
            mock_breaker = MagicMock()
            mock_breaker.call = lambda fn: fn()
            mock_pybreaker.CircuitBreaker.return_value = mock_breaker
            client.breaker = mock_breaker
            with patch("app.pipeline.services.grobid_client.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200)
                resp = client._request("GET", "http://localhost/test")
                assert resp.status_code == 200


class TestGROBIDClientProcessHeaderEdgeCases:
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_transient_status_retries(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = [
            MagicMock(status_code=502, text=""),
            MagicMock(status_code=200, text=SAMPLE_TEI),
        ]
        result = client.process_header_document(str(pdf))
        assert result["title"] == "Main Title"
        assert mock_request.call_count == 2

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_permanent_status_breaks(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.return_value = MagicMock(status_code=404, text="")
        result = client.process_header_document(str(pdf))
        assert result["title"] == ""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_request_exception_retries(self, mock_request, client, tmp_path):
        from requests import RequestException

        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = [
            RequestException("timeout"),
            MagicMock(status_code=200, text=SAMPLE_TEI),
        ]
        result = client.process_header_document(str(pdf))
        assert result["title"] == "Main Title"

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_non_xml_response_retries(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = [
            MagicMock(status_code=200, text="Not XML"),
            MagicMock(status_code=200, text=SAMPLE_TEI),
        ]
        result = client.process_header_document(str(pdf))
        assert result["title"] == "Main Title"

    def test_file_not_found_empty(self, client):
        result = client.process_header_document("/nonexistent/path.pdf")
        assert result["title"] == ""

    def test_empty_metadata_structure(self, client):
        result = client._empty_metadata()
        assert result["title"] == ""
        assert result["authors"] == []
        assert result["confidence"] == 0.0
        assert result["source"] == "grobid"


class TestGROBIDClientProcessReferencesEdgeCases:
    @patch.object(
        __import__("app.pipeline.services.grobid_client", fromlist=["GROBIDClient"]).GROBIDClient,
        "is_available",
        return_value=True,
    )
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_transient_status_retries_references(self, mock_request, mock_avail, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = [
            MagicMock(status_code=503),
            MagicMock(status_code=200),
        ]
        result = client.process_references(str(pdf))
        assert result == []

    @patch.object(
        __import__("app.pipeline.services.grobid_client", fromlist=["GROBIDClient"]).GROBIDClient,
        "is_available",
        return_value=True,
    )
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_request_exception_refs_retries(self, mock_request, mock_avail, client, tmp_path):
        from requests import RequestException

        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = [
            RequestException("timeout"),
            MagicMock(status_code=200),
        ]
        result = client.process_references(str(pdf))
        assert result == []
        assert mock_request.call_count == 2

    def test_references_file_not_found(self, client):
        result = client.process_references("/nonexistent/file.pdf")
        assert result == []


class TestGROBIDClientExtractMetadataEdgeCases:
    @patch.object(
        __import__("app.pipeline.services.grobid_client", fromlist=["GROBIDClient"]).GROBIDClient,
        "is_available",
        return_value=True,
    )
    @patch.object(
        __import__("app.pipeline.services.grobid_client", fromlist=["GROBIDClient"]).GROBIDClient,
        "process_header_document",
    )
    def test_empty_metadata_returns_empty(self, mock_header, mock_avail, client):
        mock_header.return_value = {}
        result = client.extract_metadata("test.pdf")
        assert result == {}

    @patch.object(
        __import__("app.pipeline.services.grobid_client", fromlist=["GROBIDClient"]).GROBIDClient,
        "is_available",
        return_value=True,
    )
    @patch.object(
        __import__("app.pipeline.services.grobid_client", fromlist=["GROBIDClient"]).GROBIDClient,
        "process_header_document",
    )
    @patch.object(
        __import__("app.pipeline.services.grobid_client", fromlist=["GROBIDClient"]).GROBIDClient, "process_references"
    )
    def test_references_are_empty_list(self, mock_refs, mock_header, mock_avail, client):
        mock_header.return_value = {"title": "Test"}
        mock_refs.return_value = []
        result = client.extract_metadata("test.pdf")
        assert result["references"] == []


class TestGROBIDClientTEIParsingEdgeCases:
    def test_empty_string(self, client):
        result = client._parse_tei_xml("")
        assert result["title"] == ""

    def test_non_xml_text(self, client):
        result = client._parse_tei_xml("plain text")
        assert result["title"] == ""

    def test_xml_with_namespace_edge(self, client):
        xml = """<?xml version="1.0"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <fileDesc>
              <titleStmt>
                <title type="main">Edge Title</title>
              </titleStmt>
              <sourceDesc/>
            </fileDesc>
          </teiHeader>
        </TEI>"""
        result = client._parse_tei_xml(xml)
        assert result["title"] == "Edge Title"

    def test_bom_prefixed_xml(self, client):
        xml = "\ufeff" + SAMPLE_TEI
        result = client._parse_tei_xml(xml)
        assert result["title"] == "Main Title"

    def test_invalid_xml(self, client):
        result = client._parse_tei_xml("<<<garbage>>>")
        assert result["title"] == ""


class TestGROBIDClientExtractAuthors:
    def test_full_extraction(self, client):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(SAMPLE_TEI)
        authors, affiliations = client._extract_authors(root)
        assert len(authors) == 1
        assert authors[0]["given"] == "John"
        assert authors[0]["family"] == "Smith"
        assert "MIT" in affiliations

    def test_no_authors(self, client):
        xml = """<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title>Test</title></titleStmt><sourceDesc/></fileDesc></teiHeader></TEI>"""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml)
        authors, affiliations = client._extract_authors(root)
        assert authors == []
        assert affiliations == []


class TestGROBIDClientExtractAbstract:
    def test_full_abstract(self, client):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(SAMPLE_TEI)
        abstract = client._extract_abstract(root)
        assert "Abstract text" in abstract

    def test_no_abstract(self, client):
        xml = """<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title>T</title></titleStmt></fileDesc></teiHeader></TEI>"""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml)
        assert client._extract_abstract(root) == ""


class TestGROBIDClientExtractKeywords:
    def test_full_keywords(self, client):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(SAMPLE_TEI)
        kw = client._extract_keywords(root)
        assert len(kw) == 2
        assert "AI" in kw

    def test_no_keywords(self, client):
        xml = """<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader/></TEI>"""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml)
        assert client._extract_keywords(root) == []


class TestGROBIDClientConfidenceEdgeCases:
    def test_title_short(self, client):
        score = client._calculate_confidence("Short", [])
        assert score == pytest.approx(0.4, abs=0.01)

    def test_title_long(self, client):
        score = client._calculate_confidence("A" * 20, [])
        assert score == pytest.approx(0.6, abs=0.01)

    def test_one_author(self, client):
        score = client._calculate_confidence(
            "Full Title Here",
            [
                {"given": "John", "family": "Doe"},
            ],
        )
        assert score >= 0.8

    def test_two_authors_complete(self, client):
        score = client._calculate_confidence(
            "Full Title Here",
            [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
        )
        assert score == pytest.approx(1.0, abs=0.01)

    def test_two_authors_incomplete(self, client):
        score = client._calculate_confidence(
            "Full Title Here",
            [
                {"given": "", "family": "Doe"},
                {"given": "Jane", "family": ""},
            ],
        )
        assert 0.8 <= score <= 0.95


class TestGROBIDException:
    def test_exception_message(self):
        from app.pipeline.services.grobid_client import GROBIDException

        exc = GROBIDException("Custom message")
        assert "Custom message" in str(exc)
        assert exc.service == "GROBID"

    def test_default_message(self):
        from app.pipeline.services.grobid_client import GROBIDException

        exc = GROBIDException()
        assert "GROBID" in str(exc)


class TestGROBIDClientMarkLastGood:
    def test_marks_base_url(self, client):
        client.base_urls = ["http://url1:8070", "http://url2:8070"]
        client._mark_last_good_base_url("http://url2:8070", reason="test")
        assert client._last_good_base_url == "http://url2:8070"
        assert client.base_url == "http://url2:8070"

    def test_same_url_does_not_log(self, client, caplog):
        import logging

        caplog.set_level(logging.WARNING)
        client.base_urls = ["http://url1:8070"]
        client._last_good_base_url = "http://url1:8070"
        client._mark_last_good_base_url("http://url1:8070", reason="test")
        assert len(caplog.records) == 0

    def test_different_url_logs(self, client):
        client.base_urls = ["http://url1:8070", "http://url2:8070"]
        client._last_good_base_url = "http://url1:8070"
        with patch("app.pipeline.services.grobid_client.logger.warning") as mock_warn:
            client._mark_last_good_base_url("http://url2:8070", reason="test")
            mock_warn.assert_called_once()
