import pytest

from amf_sdk import AMFClient
from amf_sdk.models import FormattingStyle, Manuscript


def test_client_initialization():
    client = AMFClient(base_url="http://test:8000")
    assert client.base_url == "http://test:8000"
    client.close()


def test_client_default_url():
    client = AMFClient()
    assert client.base_url == "http://localhost:8000"
    client.close()


def test_client_with_api_key():
    client = AMFClient(api_key="test-key-123")
    assert client.api_key == "test-key-123"
    client.close()


def test_manuscript_model(sample_manuscript):
    data = sample_manuscript.model_dump()
    assert data["title"] == "Test Manuscript"
    assert len(data["authors"]) == 1
    assert data["authors"][0]["first_name"] == "Jane"
    assert len(data["sections"]) == 1


def test_manuscript_invalid():
    with pytest.raises(Exception):
        Manuscript()


def test_formatting_style_model():
    style = FormattingStyle(
        id="apa",
        name="APA 7th Edition",
        version="7.0",
        description="Test description",
        citation_format="apa",
    )
    assert style.font_family == "Times New Roman"
    assert style.font_size == 12
    assert style.line_spacing == 2.0


def test_client_format_raises_on_no_server():
    client = AMFClient(base_url="http://localhost:1")
    with pytest.raises(Exception):
        client.format_manuscript(Manuscript(title="Test"))
    client.close()


def test_client_get_styles_raises_on_no_server():
    client = AMFClient(base_url="http://localhost:1")
    with pytest.raises(Exception):
        client.get_styles()
    client.close()


def test_context_manager():
    with AMFClient() as client:
        assert client is not None
