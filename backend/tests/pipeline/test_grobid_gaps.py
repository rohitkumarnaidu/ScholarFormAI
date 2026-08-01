# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from app.pipeline.services.grobid_client import GROBIDClient


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
            <author>
              <persName>
                <forename type="first">Jane</forename>
                <surname>Doe</surname>
              </persName>
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
def mock_settings():
    with patch("app.pipeline.services.grobid_client.settings") as mock:
        mock.get_grobid_urls.return_value = []
        mock.GROBID_URL = "http://localhost:8070"
        mock.get_service_health_path.return_value = "/api/isalive"
        mock.GROBID_TIMEOUT = 15
        mock.GROBID_MAX_RETRIES = 2
        mock.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        yield mock


@pytest.fixture
def client(mock_settings):
    return GROBIDClient()


class TestGROBIDClientInit:
    """Coverage gaps: 74, 75->77, 90->94"""

    def test_health_path_without_leading_slash(self, mock_settings):
        mock_settings.get_service_health_path.return_value = "api/isalive"
        c = GROBIDClient()
        assert c.health_path == "/api/isalive"

    def test_health_path_with_trailing_slash(self, mock_settings):
        mock_settings.get_service_health_path.return_value = "/api/isalive/"
        c = GROBIDClient()
        assert not c.health_path.endswith("/")

    @patch("app.pipeline.services.grobid_client.pybreaker")
    def test_circuit_breaker_remote_hosted(self, mock_pybreaker, mock_settings):
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = True
        c = GROBIDClient(base_url="http://remote.grobid.example.com")
        assert c._remote_hosted is True
        _, kwargs = mock_pybreaker.CircuitBreaker.call_args
        assert kwargs["fail_max"] >= 6
        assert kwargs["reset_timeout"] <= 30


class TestGROBIDClientImportFallbacks:
    """Coverage gaps: 27-28, 38-39"""

    def test_defusedxml_not_available(self):
        import app.pipeline.services.grobid_client as mod
        with patch.dict("sys.modules", {"defusedxml": None}):
            importlib.reload(mod)
            import xml.etree.ElementTree as stdlib_et
            assert mod.ET is stdlib_et
        importlib.reload(mod)

    def test_pybreaker_not_available(self):
        with patch("app.pipeline.services.grobid_client.pybreaker", None):
            with patch("app.pipeline.services.grobid_client.settings") as mock_st:
                mock_st.get_grobid_urls.return_value = []
                mock_st.GROBID_URL = "http://localhost:8070"
                mock_st.get_service_health_path.return_value = "/api/isalive"
                mock_st.GROBID_TIMEOUT = 15
                mock_st.GROBID_MAX_RETRIES = 2
                mock_st.EXTERNAL_CIRCUIT_BREAKER_ENABLED = True
                c = GROBIDClient()
                assert c.breaker is None


class TestGROBIDClientRequest:
    """Coverage gaps: 134->139, 141"""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_request_timeout_remote_hosted(self, mock_req, mock_settings):
        mock_settings.GROBID_URL = "http://remote.grobid.example.com"
        c = GROBIDClient()
        c._request("GET", "http://test.com")
        _, kwargs = mock_req.call_args
        connect_timeout, read_timeout = kwargs["timeout"]
        assert connect_timeout == 5.0

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_request_timeout_local_hosted(self, mock_req, client):
        client._request("GET", "http://test.com")
        _, kwargs = mock_req.call_args
        connect_timeout, read_timeout = kwargs["timeout"]
        assert connect_timeout == 3.0

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_request_existing_timeout_in_kwargs(self, mock_req, client):
        client._request("GET", "http://test.com", timeout=42)
        _, kwargs = mock_req.call_args
        assert kwargs["timeout"] == 42

    @patch("app.pipeline.services.grobid_client.requests.request")
    @patch("app.pipeline.services.grobid_client.pybreaker")
    def test_request_with_circuit_breaker(self, mock_pybreaker, mock_req, mock_settings):
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = True
        real_call = lambda fn: fn()
        mock_pybreaker.CircuitBreaker.return_value.call.side_effect = real_call
        c = GROBIDClient()
        assert c.breaker is not None
        c._request("GET", "http://test.com")
        mock_pybreaker.CircuitBreaker.return_value.call.assert_called_once()
        mock_req.assert_called_once()


class TestGROBIDClientProcessHeader:
    """Coverage gaps: 191-203, 220-243, 246"""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_transient_status_retry(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        resp_fail = MagicMock()
        resp_fail.status_code = 429
        resp_fail.text = ""
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.text = SAMPLE_TEI_XML
        mock_request.side_effect = [resp_fail, resp_ok]
        result = client.process_header_document(str(pdf))
        assert result["title"] == "Test Paper Title"

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_non_transient_status_break(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = ""
        mock_request.return_value = mock_resp
        result = client.process_header_document(str(pdf))
        assert result["title"] == ""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_request_exception_retry(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = RequestException("timeout")
        result = client.process_header_document(str(pdf))
        assert result["title"] == ""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_generic_exception_retry(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = ValueError("unexpected")
        result = client.process_header_document(str(pdf))
        assert result["title"] == ""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_failover_warning(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        client.base_urls = ["http://url1:8070", "http://url2:8070"]
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = ""
        mock_request.return_value = mock_resp
        with patch("app.pipeline.services.grobid_client.logger") as mock_logger:
            result = client.process_header_document(str(pdf))
            assert result["title"] == ""
            mock_logger.warning.assert_any_call(
                "GROBID failover: moving to next endpoint after failures (from=%s to=%s)",
                "http://url1:8070",
                "http://url2:8070",
            )


class TestGROBIDClientProcessReferences:
    """Coverage gaps: 279-282, 287-306"""

    @patch.object(GROBIDClient, "is_available", return_value=True)
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_references_transient_status_retry(self, mock_request, mock_avail, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        resp_fail = MagicMock()
        resp_fail.status_code = 429
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        mock_request.side_effect = [resp_fail, resp_ok]
        result = client.process_references(str(pdf))
        assert result == []

    @patch.object(GROBIDClient, "is_available", return_value=True)
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_references_non_transient_status_break(self, mock_request, mock_avail, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_request.return_value = mock_resp
        result = client.process_references(str(pdf))
        assert result == []

    @patch.object(GROBIDClient, "is_available", return_value=True)
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_references_generic_exception_retry(self, mock_request, mock_avail, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_request.side_effect = ValueError("unexpected error")
        result = client.process_references(str(pdf))
        assert result == []

    @patch.object(GROBIDClient, "is_available", return_value=True)
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_references_failover_warning(self, mock_request, mock_avail, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        client.base_urls = ["http://url1:8070", "http://url2:8070"]
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_request.return_value = mock_resp
        with patch("app.pipeline.services.grobid_client.logger") as mock_logger:
            result = client.process_references(str(pdf))
            assert result == []
            mock_logger.warning.assert_any_call(
                "GROBID reference failover: moving to next endpoint (from=%s to=%s)",
                "http://url1:8070",
                "http://url2:8070",
            )


class TestGROBIDClientExtractMetadata:
    """Coverage gaps: 320"""

    @patch.object(GROBIDClient, "is_available", return_value=True)
    @patch.object(GROBIDClient, "process_header_document", return_value={})
    def test_returns_empty_when_header_empty(self, mock_header, mock_avail, client):
        result = client.extract_metadata("test.pdf")
        assert result == {}


class TestGROBIDClientMarkLastGood:
    """Coverage gaps: 112"""

    def test_failover_switch_logs_warning(self, client):
        with patch("app.pipeline.services.grobid_client.logger") as mock_logger:
            client._mark_last_good_base_url("http://new.url", reason="test_failover")
            mock_logger.warning.assert_called_once_with(
                "GROBID failover switch: %s -> %s (reason=%s)",
                "http://localhost:8070",
                "http://new.url",
                "test_failover",
            )


class TestGROBIDClientAuthorExtraction:
    """Coverage gaps: 404->414, 408->410, 410->414, 420->398"""

    def test_author_without_persName_skips_name_extraction(self, client):
        xml = """<?xml version="1.0"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <fileDesc>
              <sourceDesc>
                <biblStruct>
                  <analytic>
                    <author>
                      <affiliation>
                        <orgName type="institution">MIT</orgName>
                      </affiliation>
                    </author>
                  </analytic>
                </biblStruct>
              </sourceDesc>
            </fileDesc>
          </teiHeader>
        </TEI>"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        authors, affiliations = client._extract_authors(root)
        assert authors == []
        assert "MIT" in affiliations

    def test_author_forename_only_skips_surname(self, client):
        xml = """<?xml version="1.0"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <fileDesc>
              <sourceDesc>
                <biblStruct>
                  <analytic>
                    <author>
                      <persName>
                        <forename type="first">John</forename>
                      </persName>
                    </author>
                    <author>
                      <persName>
                        <surname>Smith</surname>
                      </persName>
                    </author>
                  </analytic>
                </biblStruct>
              </sourceDesc>
            </fileDesc>
          </teiHeader>
        </TEI>"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        authors, affiliations = client._extract_authors(root)
        assert authors[0]["given"] == "John"
        assert authors[0]["family"] == ""
        assert authors[1]["given"] == ""
        assert authors[1]["family"] == "Smith"

    def test_affiliation_element_without_text_excluded(self, client):
        xml = """<?xml version="1.0"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <fileDesc>
              <sourceDesc>
                <biblStruct>
                  <analytic>
                    <author>
                      <persName>
                        <forename type="first">John</forename>
                        <surname>Smith</surname>
                      </persName>
                      <affiliation>
                        <orgName type="institution"/>
                      </affiliation>
                    </author>
                  </analytic>
                </biblStruct>
              </sourceDesc>
            </fileDesc>
          </teiHeader>
        </TEI>"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        authors, affiliations = client._extract_authors(root)
        assert authors[0]["affiliation"] == ""
        assert affiliations == []


class TestGROBIDClientAbstract:
    """Coverage gaps: 438-439"""

    def test_abstract_with_direct_text_no_paragraphs(self, client):
        xml = """<?xml version="1.0"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <profileDesc>
              <abstract>Direct abstract text here.</abstract>
            </profileDesc>
          </teiHeader>
        </TEI>"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        abstract = client._extract_abstract(root)
        assert abstract == "Direct abstract text here."


class TestGROBIDClientKeywords:
    """Coverage gaps: 447->446"""

    def test_skips_keyword_element_without_text(self, client):
        xml = """<?xml version="1.0"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <profileDesc>
              <textClass>
                <keywords>
                  <term>machine learning</term>
                  <term/>
                  <term>NLP</term>
                </keywords>
              </textClass>
            </profileDesc>
          </teiHeader>
        </TEI>"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        keywords = client._extract_keywords(root)
        assert keywords == ["machine learning", "NLP"]


class TestGROBIDClientConfidence:
    """Coverage gaps: 474->476"""

    def test_single_author_does_not_get_two_author_bonus(self, client):
        score = client._calculate_confidence("Long Title Here", [
            {"given": "John", "family": "Smith"},
        ])
        assert score == pytest.approx(0.9, abs=0.01)

    def test_incomplete_single_author_no_completeness_bonus(self, client):
        score = client._calculate_confidence("Long Title Here", [
            {"given": "John", "family": ""},
        ])
        expected = 0.4 + 0.2 + 0.2
        assert score == pytest.approx(expected, abs=0.01)


class TestGROBIDClientEndpointUrl:
    """Edge cases for _endpoint_url helper."""

    def test_path_with_leading_slash(self, client):
        url = client._endpoint_url("http://localhost:8070", "/api/test")
        assert url == "http://localhost:8070/api/test"

    def test_path_without_leading_slash(self, client):
        url = client._endpoint_url("http://localhost:8070", "api/test")
        assert url == "http://localhost:8070/api/test"
