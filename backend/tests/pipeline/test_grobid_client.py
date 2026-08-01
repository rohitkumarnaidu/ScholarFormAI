# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock

from app.pipeline.services.grobid_client import GROBIDClient, GROBIDException


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
    def test_init_default_url(self, mock_settings):
        c = GROBIDClient()
        assert "localhost:8070" in c.base_url

    def test_init_with_base_url(self, mock_settings):
        c = GROBIDClient(base_url="http://grobid.example.com")
        assert "grobid.example.com" in c.base_url

    def test_init_with_empty_urls_fallback(self, mock_settings):
        mock_settings.get_grobid_urls.return_value = [""]
        c = GROBIDClient()
        assert c.base_urls
        assert all(url for url in c.base_urls)


class TestGROBIDClientIsAvailable:
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_available(self, mock_request, client):
        mock_request.return_value.status_code = 200
        assert client.is_available() is True

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_unavailable(self, mock_request, client):
        mock_request.return_value.status_code = 503
        assert client.is_available() is False

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_network_error(self, mock_request, client):
        mock_request.side_effect = Exception("Connection refused")
        assert client.is_available() is False

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_failover_to_next_url(self, mock_request, client):
        client.base_urls = ["http://url1:8070", "http://url2:8070"]
        mock_request.return_value.status_code = 503
        assert client.is_available() is False


class TestGROBIDClientProcessHeader:
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_success(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_TEI_XML
        mock_request.return_value = mock_resp

        result = client.process_header_document(str(pdf))
        assert result["title"] == "Test Paper Title"
        assert len(result["authors"]) == 2
        assert result["authors"][0]["given"] == "John"
        assert result["authors"][1]["family"] == "Doe"
        assert result["abstract"] == "This is an abstract."
        assert "machine learning" in result["keywords"]

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_no_authors(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title>No Author</title></titleStmt><sourceDesc/></fileDesc></teiHeader></TEI>'
        mock_request.return_value = mock_resp

        result = client.process_header_document(str(pdf))
        assert result["title"] == "No Author"
        assert result["authors"] == []

    def test_header_file_not_found(self, client):
        result = client.process_header_document("/nonexistent/file.pdf")
        assert result["title"] == ""

    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_header_non_xml_response(self, mock_request, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Not XML"
        mock_request.return_value = mock_resp

        result = client.process_header_document(str(pdf))
        assert result["title"] == ""


class TestGROBIDClientProcessReferences:
    @patch.object(GROBIDClient, "is_available", return_value=True)
    @patch("app.pipeline.services.grobid_client.requests.request")
    def test_references_success(self, mock_request, mock_avail, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_request.return_value = mock_resp

        result = client.process_references(str(pdf))
        assert result == []

    @patch.object(GROBIDClient, "is_available", return_value=False)
    def test_references_service_unavailable(self, mock_avail, client, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        result = client.process_references(str(pdf))
        assert result == []

    def test_references_file_not_found(self, client):
        result = client.process_references("/nonexistent/file.pdf")
        assert result == []


class TestGROBIDClientExtractMetadata:
    @patch.object(GROBIDClient, "is_available", return_value=True)
    @patch.object(GROBIDClient, "process_header_document")
    @patch.object(GROBIDClient, "process_references")
    def test_extract_metadata(self, mock_refs, mock_header, mock_avail, client):
        mock_header.return_value = {"title": "Test", "authors": []}
        mock_refs.return_value = [{"id": "ref1"}]
        result = client.extract_metadata("test.pdf")
        assert result["title"] == "Test"
        assert result["references"] == [{"id": "ref1"}]

    @patch.object(GROBIDClient, "is_available", return_value=False)
    def test_extract_metadata_not_available(self, mock_avail, client):
        with pytest.raises(GROBIDException):
            client.extract_metadata("test.pdf")


class TestGROBIDClientTEIParsing:
    def test_parse_full_tei(self, client):
        result = client._parse_tei_xml(SAMPLE_TEI_XML)
        assert result["title"] == "Test Paper Title"
        assert result["confidence"] > 0.0
        assert result["source"] == "grobid"

    def test_parse_empty_xml(self, client):
        result = client._parse_tei_xml("")
        assert result["title"] == ""
        assert result["confidence"] == 0.0

    def test_parse_invalid_xml(self, client):
        result = client._parse_tei_xml("<<<not xml>>>")
        assert result["title"] == ""

    def test_parse_non_xml_payload(self, client):
        result = client._parse_tei_xml("   plain text   ")
        assert result["title"] == ""

    def test_parse_bom_prefixed(self, client):
        result = client._parse_tei_xml("\ufeff" + SAMPLE_TEI_XML)
        assert result["title"] == "Test Paper Title"

    def test_extract_title_from_any(self, client):
        xml = '<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title>Fallback Title</title></titleStmt></fileDesc></teiHeader></TEI>'
        root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(xml)
        title = client._extract_title(root)
        assert title == "Fallback Title"

    def test_extract_title_no_title(self, client):
        xml = '<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader/></TEI>'
        root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(xml)
        assert client._extract_title(root) == ""


class TestGROBIDClientConfidence:
    def test_confidence_full(self, client):
        score = client._calculate_confidence("Long Title Here", [
            {"given": "John", "family": "Smith"},
            {"given": "Jane", "family": "Doe"},
        ])
        assert score == pytest.approx(1.0, abs=0.01)

    def test_confidence_no_title(self, client):
        score = client._calculate_confidence("", [])
        assert score == 0.2

    def test_confidence_short_title(self, client):
        score = client._calculate_confidence("Short", [])
        assert score == 0.4

    def test_confidence_one_author_incomplete(self, client):
        score = client._calculate_confidence("Good Title Here", [
            {"given": "", "family": "Smith"},
        ])
        assert score > 0.0
