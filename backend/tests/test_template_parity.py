# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _canonical_template_id(raw_name: str) -> str:
    return "_".join(str(raw_name or "").strip().lower().split())


def _template_ids_from_disk() -> list[str]:
    templates_dir = Path(__file__).resolve().parents[1] / "app" / "templates"
    return sorted(
        _canonical_template_id(entry.name)
        for entry in templates_dir.iterdir()
        if entry.is_dir() and not entry.name.startswith("__")
    )


def test_builtin_template_api_matches_disk_and_v1_contract(client: TestClient):
    legacy_response = client.get("/api/templates")
    v1_response = client.get("/api/v1/templates")

    # Hard-cut migration: legacy templates endpoint is intentionally removed.
    assert legacy_response.status_code == 404
    assert v1_response.status_code == 200

    v1_templates = v1_response.json()["data"]["templates"]
    expected_ids = _template_ids_from_disk()

    assert [item["id"] for item in v1_templates] == expected_ids

    for item in v1_templates:
        assert item["id"] == item["id"].lower()
        assert item["id"] == _canonical_template_id(item["id"])
        assert item["source"] == "built_in"
