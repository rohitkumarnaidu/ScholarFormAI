import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

BACKEND_DIR = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def _make_mock_response(data: dict, status: int = 200):
    mr = MagicMock()
    mr.status_code = status
    mr.json.return_value = data
    mr.raise_for_status.return_value = None
    return mr


@pytest.fixture(autouse=True)
def mock_api():
    styles_data = [
        {"id": "apa", "name": "APA 7th Edition", "version": "7.0", "description": "", "citation_format": "apa"},
        {"id": "mla", "name": "MLA 9th Edition", "version": "9.0", "description": "", "citation_format": "mla"},
    ]
    format_data = {"download_url": "/api/v1/download/test.docx", "pages": 5, "style_applied": "apa"}
    preview_data = {"html": "<html><body>Test</body></html>", "style_applied": "mla"}
    validate_data = {"valid": True, "errors": [], "warnings": []}

    with patch("requests.post") as mock_post:
        def _side_effect(url, **kw):
            if "/format" in url:
                return _make_mock_response(format_data)
            if "/preview" in url:
                return _make_mock_response(preview_data)
            if "/validate" in url:
                return _make_mock_response(validate_data)
            return _make_mock_response({})
        mock_post.side_effect = _side_effect

        with patch("requests.get") as mock_get:
            mock_get.side_effect = lambda url, **kw: _make_mock_response(styles_data) if "styles" in url else _make_mock_response({})
            yield


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_manuscript(temp_dir):
    path = temp_dir / "test_manuscript.md"
    path.write_text("""# Test Manuscript

## Abstract
This is a test.

## Introduction
Test content here.""")
    return path
