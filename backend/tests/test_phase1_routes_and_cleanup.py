# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.models import FormatRequest, Manuscript
from app.routers.v1.format import format_manuscript
from app.main import _load_optional_routers, app
from app.models import DocumentMetadata
from app.models import PipelineDocument as Document
from app.pipeline.formatting.template_renderer import TemplateRenderer


@pytest.fixture
def client():
    _load_optional_routers(app)
    return TestClient(app)


def test_auth_me_endpoint_mounted():
    """Verify GET /api/v1/auth/me is mounted on the app router."""
    _load_optional_routers(app)
    routes = [route.path for route in app.routes]
    assert "/api/v1/auth/me" in routes


def test_auth_me_unauthorized(client):
    """Verify /api/v1/auth/me returns 401 when no auth token is supplied."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


def test_health_detailed_endpoint(client):
    """Verify GET /api/v1/health/detailed returns detailed health check payload."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data.get("error") is None
    payload = data.get("data", {})
    assert "components" in payload
    assert "status" in payload
    assert "version" in payload
    assert "python_version" in payload


def test_metrics_root_endpoint(client):
    """Verify GET /api/v1/metrics returns aggregated metrics summary."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data.get("error") is None
    payload = data.get("data", {})
    assert "status" in payload
    assert "model_metrics" in payload


def test_config_endpoint(client):
    """Verify GET /api/v1/config returns public system configuration."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert data.get("error") is None
    payload = data.get("data", {})
    assert "environment" in payload
    assert "version" in payload
    assert "max_upload_size" in payload
    assert "default_style" in payload


def test_format_download_url_signed_format():
    """Verify format endpoint generates signed download URL matching /api/v1/documents/{jobId}/download."""
    req = FormatRequest(
        manuscript=Manuscript(
            title="Signed Download URL Test",
            authors=[],
            sections=[],
        ),
        style_id="apa",
    )
    res = asyncio.run(format_manuscript(req))
    download_url = res.download_url

    assert "/api/v1/documents/" in download_url
    assert "/download" in download_url
    assert "token=" in download_url
    assert "expires=" in download_url
    assert "/api/v1/download/" not in download_url


def test_format_temp_file_cleanup_on_success():
    """Verify temporary .docx files created during manuscript formatting are cleaned up on success."""
    req = FormatRequest(
        manuscript=Manuscript(
            title="Cleanup Test",
            authors=[],
            sections=[],
        ),
        style_id="apa",
    )

    captured_paths = []
    from app.services.formatter import ManuscriptFormatter

    orig_format = ManuscriptFormatter.format

    def mock_format(self, manuscript, style, output_path, options=None):
        captured_paths.append(output_path)
        return orig_format(self, manuscript, style, output_path, options)

    with patch.object(ManuscriptFormatter, "format", side_effect=mock_format, autospec=True):
        asyncio.run(format_manuscript(req))
        assert len(captured_paths) == 1
        output_path = captured_paths[0]
        assert not os.path.exists(output_path), (
            f"Temp output file {output_path} was not cleaned up after format execution!"
        )


def test_format_temp_file_cleanup_on_exception():
    """Verify temporary .docx files are cleaned up even when formatting throws an exception."""
    req = FormatRequest(
        manuscript=Manuscript(
            title="Exception Cleanup Test",
            authors=[],
            sections=[],
        ),
        style_id="apa",
    )

    captured_paths = []
    from app.services.formatter import ManuscriptFormatter

    def mock_format_error(self, manuscript, style, output_path, options=None):
        captured_paths.append(output_path)
        raise RuntimeError("Simulated formatting failure")

    with patch.object(ManuscriptFormatter, "format", side_effect=mock_format_error, autospec=True):
        with pytest.raises(Exception):
            asyncio.run(format_manuscript(req))

        assert len(captured_paths) == 1
        output_path = captured_paths[0]
        assert not os.path.exists(output_path), f"Temp file {output_path} remained on disk after formatting exception!"


def test_template_renderer_temp_file_cleanup():
    """Verify TemplateRenderer cleans up temporary template docx files after rendering."""
    renderer = TemplateRenderer(templates_dir="app/templates")
    doc = Document(
        document_id="doc1",
        original_filename="test.docx",
        blocks=[],
        metadata=DocumentMetadata(title="Temp Test Title"),
    )

    created_temp_templates = []
    orig_fallback = renderer._build_fallback_template

    def tracking_fallback():
        path = orig_fallback()
        created_temp_templates.append(path)
        return path

    with patch.object(renderer, "_build_fallback_template", side_effect=tracking_fallback):
        renderer.render(doc, "non_existent_style")
        assert len(created_temp_templates) == 1
        temp_tpl_path = created_temp_templates[0]
        assert not temp_tpl_path.exists(), (
            f"Temporary fallback DOCX template {temp_tpl_path} was not deleted after render!"
        )
