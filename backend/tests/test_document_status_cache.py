# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.routers.v1 import documents_impl as legacy_documents


@pytest.fixture(autouse=True)
def reset_document_status_cache():
    legacy_documents._reset_document_status_cache_for_tests()
    yield
    legacy_documents._reset_document_status_cache_for_tests()


def _configure_status_cache(monkeypatch, ttl_seconds: float) -> None:
    monkeypatch.setattr(
        legacy_documents.settings,
        "DOCUMENT_STATUS_CACHE_TTL_SECONDS",
        ttl_seconds,
        raising=False,
    )


def _mock_document(*, owner: str = "user-1", status: str = "PROCESSING") -> dict:
    return {
        "id": "job-1",
        "user_id": owner,
        "status": status,
        "current_stage": "EXTRACTION",
        "progress": 42,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:10+00:00",
    }


@pytest.mark.asyncio
async def test_document_status_cache_hits_within_ttl(monkeypatch):
    _configure_status_cache(monkeypatch, ttl_seconds=5.0)
    user = SimpleNamespace(id="user-1")

    with patch(
        "app.services.document_crud_service.DocumentCrudService.get_document",
        return_value=_mock_document(),
    ) as mock_get_doc, patch(
        "app.services.document_crud_service.DocumentCrudService.get_processing_statuses",
        return_value=[{"phase": "EXTRACTION", "status": "running", "message": "extracting"}],
    ) as mock_get_statuses, patch(
        "app.services.document_crud_service.DocumentCrudService.get_document_result",
        return_value={"validation_results": {"quality_summary": {"quality_score": 0.8}}},
    ) as mock_get_result:
        first_payload = await legacy_documents.get_status("job-1", current_user=user)
        second_payload = await legacy_documents.get_status("job-1", current_user=user)

    assert first_payload == second_payload
    assert mock_get_doc.call_count == 1
    assert mock_get_statuses.call_count == 1
    assert mock_get_result.call_count == 0


@pytest.mark.asyncio
async def test_document_status_cache_scoped_by_user(monkeypatch):
    _configure_status_cache(monkeypatch, ttl_seconds=10.0)
    owner = SimpleNamespace(id="user-1")
    intruder = SimpleNamespace(id="user-2")

    with patch(
        "app.services.document_crud_service.DocumentCrudService.get_document",
        return_value=_mock_document(owner="user-1"),
    ) as mock_get_doc, patch(
        "app.services.document_crud_service.DocumentCrudService.get_processing_statuses",
        return_value=[{"phase": "EXTRACTION", "status": "running"}],
    ) as mock_get_statuses, patch(
        "app.services.document_crud_service.DocumentCrudService.get_document_result",
        return_value=None,
    ) as mock_get_result:
        await legacy_documents.get_status("job-1", current_user=owner)
        with pytest.raises(HTTPException) as exc_info:
            await legacy_documents.get_status("job-1", current_user=intruder)

    assert exc_info.value.status_code == 403
    assert mock_get_doc.call_count == 2
    assert mock_get_statuses.call_count == 1
    assert mock_get_result.call_count == 0


@pytest.mark.asyncio
async def test_document_status_cache_expires_after_ttl(monkeypatch):
    _configure_status_cache(monkeypatch, ttl_seconds=0.01)
    user = SimpleNamespace(id="user-1")

    with patch(
        "app.services.document_crud_service.DocumentCrudService.get_document",
        return_value=_mock_document(),
    ) as mock_get_doc, patch(
        "app.services.document_crud_service.DocumentCrudService.get_processing_statuses",
        return_value=[{"phase": "EXTRACTION", "status": "running"}],
    ) as mock_get_statuses, patch(
        "app.services.document_crud_service.DocumentCrudService.get_document_result",
        return_value=None,
    ) as mock_get_result:
        await legacy_documents.get_status("job-1", current_user=user)
        await asyncio.sleep(0.02)
        await legacy_documents.get_status("job-1", current_user=user)

    assert mock_get_doc.call_count == 2
    assert mock_get_statuses.call_count == 2
    assert mock_get_result.call_count == 0


@pytest.mark.asyncio
async def test_document_status_cache_fetches_result_for_terminal_status(monkeypatch):
    _configure_status_cache(monkeypatch, ttl_seconds=5.0)
    user = SimpleNamespace(id="user-1")

    with patch(
        "app.services.document_crud_service.DocumentCrudService.get_document",
        return_value=_mock_document(status="COMPLETED"),
    ) as mock_get_doc, patch(
        "app.services.document_crud_service.DocumentCrudService.get_processing_statuses",
        return_value=[{"phase": "PERSISTENCE", "status": "done", "message": "saved"}],
    ) as mock_get_statuses, patch(
        "app.services.document_crud_service.DocumentCrudService.get_document_result",
        return_value={"validation_results": {"quality_summary": {"quality_score": 0.91}}},
    ) as mock_get_result:
        await legacy_documents.get_status("job-1", current_user=user)
        await legacy_documents.get_status("job-1", current_user=user)

    assert mock_get_doc.call_count == 1
    assert mock_get_statuses.call_count == 1
    assert mock_get_result.call_count == 1


