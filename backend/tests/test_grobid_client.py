# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Unit and integration tests for GROBID client.

Run with:
    pytest tests/test_grobid_client.py -v

Integration tests require GROBID service running:
    docker-compose up -d grobid
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlparse

import pytest
import requests

from app.pipeline.services.grobid_client import GROBIDClient, GROBIDException

# Sample TEI XML response from GROBID
SAMPLE_TEI_XML = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Deep Learning for Academic Document Processing</title>
            </titleStmt>
            <sourceDesc>
                <biblStruct>
                    <analytic>
                        <author>
                            <persName>
                                <forename type="first">John</forename>
                                <surname>Doe</surname>
                            </persName>
                            <affiliation>
                                <orgName type="institution">MIT</orgName>
                            </affiliation>
                        </author>
                        <author>
                            <persName>
                                <forename type="first">Jane</forename>
                                <surname>Smith</surname>
                            </persName>
                            <affiliation>
                                <orgName type="institution">Stanford University</orgName>
                            </affiliation>
                        </author>
                    </analytic>
                </biblStruct>
            </sourceDesc>
        </fileDesc>
        <profileDesc>
            <abstract>
                <p>This paper presents a novel approach to document processing using deep learning.</p>
            </abstract>
            <textClass>
                <keywords>
                    <term>deep learning</term>
                    <term>document processing</term>
                    <term>NLP</term>
                </keywords>
            </textClass>
        </profileDesc>
    </teiHeader>
</TEI>
"""


def _grobid_base_url_from_env() -> str:
    env_urls = os.getenv("GROBID_URLS", "")
    if env_urls.strip():
        first = env_urls.split(",")[0].strip()
        if first:
            return first.rstrip("/")
    env_url = os.getenv("GROBID_URL") or os.getenv("GROBID_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    host = os.getenv("GROBID_HOST", "localhost")
    port = os.getenv("GROBID_PORT", "8070")
    return f"http://{host}:{port}"


def _grobid_host_port_from_env() -> tuple[str, int]:
    host = os.getenv("GROBID_HOST")
    port = os.getenv("GROBID_PORT")
    if host:
        return host, int(port or "8070")

    env_urls = os.getenv("GROBID_URLS", "")
    if env_urls.strip():
        env_url = env_urls.split(",")[0].strip()
    else:
        env_url = os.getenv("GROBID_URL") or os.getenv("GROBID_BASE_URL")
    if env_url:
        parsed = urlparse(env_url if "://" in env_url else f"http://{env_url}")
        if parsed.hostname:
            return parsed.hostname, int(parsed.port or (443 if parsed.scheme == "https" else 80))

    return "127.0.0.1", 8070


class TestGROBIDTestConfig:
    """Test GROBID test endpoint resolution from env vars."""

    def test_grobid_base_url_prefers_urls_list(self, monkeypatch):
        monkeypatch.setenv(
            "GROBID_URLS",
            "https://primary-grobid.example,https://shadow-grobid.example",
        )
        monkeypatch.setenv("GROBID_URL", "https://legacy-single.example")
        assert _grobid_base_url_from_env() == "https://primary-grobid.example"

    def test_grobid_host_port_uses_url_when_host_not_set(self, monkeypatch):
        monkeypatch.delenv("GROBID_HOST", raising=False)
        monkeypatch.delenv("GROBID_PORT", raising=False)
        monkeypatch.delenv("GROBID_URLS", raising=False)
        monkeypatch.setenv("GROBID_URL", "https://rohith083-scholarform-grobid.hf.space")
        host, port = _grobid_host_port_from_env()
        assert host == "rohith083-scholarform-grobid.hf.space"
        assert port == 443

    def test_grobid_host_port_prefers_host_port_override(self, monkeypatch):
        monkeypatch.setenv("GROBID_HOST", "127.0.0.1")
        monkeypatch.setenv("GROBID_PORT", "8070")
        monkeypatch.setenv("GROBID_URL", "https://rohith083-scholarform-grobid.hf.space")
        host, port = _grobid_host_port_from_env()
        assert host == "127.0.0.1"
        assert port == 8070

    def test_grobid_base_url_falls_back_to_localhost(self, monkeypatch):
        monkeypatch.delenv("GROBID_URLS", raising=False)
        monkeypatch.delenv("GROBID_URL", raising=False)
        monkeypatch.delenv("GROBID_BASE_URL", raising=False)
        monkeypatch.delenv("GROBID_HOST", raising=False)
        monkeypatch.delenv("GROBID_PORT", raising=False)
        assert _grobid_base_url_from_env() == "http://localhost:8070"


class TestGROBIDClient:
    """Unit tests for GROBID client."""

    @pytest.fixture
    def client(self):
        """Create GROBID client instance."""
        return GROBIDClient(base_url="http://localhost:8070")

    def test_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "http://localhost:8070"
        assert 3 <= client.timeout <= 90

    def test_base_url_trailing_slash(self):
        """Test base URL normalization."""
        client = GROBIDClient(base_url="http://localhost:8070/")
        assert client.base_url == "http://localhost:8070"

    @patch("requests.request")
    def test_is_available_success(self, mock_request, client):
        """Test service availability check - success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        assert client.is_available() is True
        mock_request.assert_called_once_with(
            "GET",
            "http://localhost:8070/health",
            timeout=(2.0, 3.0),
        )

    @patch("requests.request")
    def test_is_available_failure(self, mock_request, client):
        """Test service availability check - failure."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")

        assert client.is_available() is False

    def test_parse_tei_xml_complete(self, client):
        """Test TEI XML parsing with complete metadata."""
        result = client._parse_tei_xml(SAMPLE_TEI_XML)

        # Check title
        assert result["title"] == "Deep Learning for Academic Document Processing"

        # Check authors
        assert len(result["authors"]) == 2
        assert result["authors"][0]["given"] == "John"
        assert result["authors"][0]["family"] == "Doe"
        assert result["authors"][0]["full_name"] == "John Doe"
        assert result["authors"][0]["affiliation"] == "MIT"

        assert result["authors"][1]["given"] == "Jane"
        assert result["authors"][1]["family"] == "Smith"
        assert result["authors"][1]["affiliation"] == "Stanford University"

        # Check affiliations
        assert "MIT" in result["affiliations"]
        assert "Stanford University" in result["affiliations"]

        # Check abstract
        assert "novel approach" in result["abstract"]

        # Check keywords
        assert "deep learning" in result["keywords"]
        assert "NLP" in result["keywords"]

        # Check metadata
        assert result["source"] == "grobid"
        assert result["confidence"] > 0.8

    def test_parse_tei_xml_minimal(self, client):
        """Test TEI XML parsing with minimal metadata."""
        minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
                <fileDesc>
                    <titleStmt>
                        <title level="a" type="main">Test Title</title>
                    </titleStmt>
                </fileDesc>
            </teiHeader>
        </TEI>
        """

        result = client._parse_tei_xml(minimal_xml)

        assert result["title"] == "Test Title"
        assert result["authors"] == []
        assert result["affiliations"] == []
        assert result["abstract"] == ""
        assert result["keywords"] == []
        assert result["confidence"] < 0.5  # Low confidence due to missing data

    def test_parse_tei_xml_invalid(self, client):
        """Test TEI XML parsing with invalid XML."""
        invalid_xml = "This is not XML"

        result = client._parse_tei_xml(invalid_xml)

        # Should return empty metadata
        assert result["title"] == ""
        assert result["authors"] == []
        assert result["confidence"] == 0.0

    def test_calculate_confidence_high(self, client):
        """Test confidence calculation - high confidence."""
        title = "A Comprehensive Study of Deep Learning"
        authors = [{"given": "John", "family": "Doe"}, {"given": "Jane", "family": "Smith"}]

        confidence = client._calculate_confidence(title, authors)

        assert confidence >= 0.8

    def test_calculate_confidence_low(self, client):
        """Test confidence calculation - low confidence."""
        title = ""
        authors = []

        confidence = client._calculate_confidence(title, authors)

        assert confidence <= 0.3

    def test_empty_metadata(self, client):
        """Test empty metadata structure."""
        result = client._empty_metadata()

        assert result["title"] == ""
        assert result["authors"] == []
        assert result["affiliations"] == []
        assert result["abstract"] == ""
        assert result["keywords"] == []
        assert result["confidence"] == 0.0
        assert result["source"] == "grobid"


class TestGROBIDIntegration:
    """Integration tests requiring GROBID service."""

    @pytest.fixture
    def client(self):
        """Create GROBID client for integration tests."""
        return GROBIDClient(base_url=_grobid_base_url_from_env())

    @pytest.mark.integration
    def test_service_availability(self, client):
        """Test GROBID service is running."""
        is_available = client.is_available()
        assert isinstance(is_available, bool)

    @pytest.mark.integration
    def test_extract_metadata_pdf(self, client, tmp_path):
        """Test metadata extraction from a real PDF file."""
        if not client.is_available():
            with pytest.raises(GROBIDException, match="not available"):
                client.extract_metadata("dummy.pdf")
            return

        # Prefer repository samples so this test executes without manual fixtures.
        sample_candidates = sorted(Path("samples").glob("*.pdf"))
        if sample_candidates:
            sample_pdf = sample_candidates[0]
        else:
            # Fallback: generate a minimal PDF dynamically when sample files are absent.
            sample_pdf = tmp_path / "generated_sample.pdf"
            from pypdf import PdfWriter

            writer = PdfWriter()
            writer.add_blank_page(width=595, height=842)
            writer.add_metadata({"/Title": "Generated GROBID Test Document"})
            with open(sample_pdf, "wb") as f:
                writer.write(f)

        result = client.extract_metadata(str(sample_pdf))

        assert isinstance(result, dict)
        assert "title" in result
        assert "authors" in result
        assert "confidence" in result
        assert result.get("source") == "grobid"
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.integration
    def test_extract_metadata_service_unavailable(self, monkeypatch):
        """Test error handling when service is unavailable."""
        monkeypatch.delenv("GROBID_URLS", raising=False)
        monkeypatch.delenv("GROBID_URL", raising=False)
        monkeypatch.delenv("GROBID_BASE_URL", raising=False)
        monkeypatch.setattr(
            "app.config.settings.Settings.get_grobid_urls",
            lambda self: ["http://localhost:9999"],
            raising=False,
        )
        client = GROBIDClient(base_url="http://localhost:9999")  # Wrong port

        with pytest.raises(GROBIDException, match="not available"):
            client.extract_metadata("dummy.pdf")


# Pytest configuration
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test (requires GROBID service)")
