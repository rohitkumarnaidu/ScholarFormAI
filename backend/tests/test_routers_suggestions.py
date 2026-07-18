# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def get_enveloped_data(response):
    return response.json()["data"]


@pytest.fixture
def client():
    from app.main import app
    from app.utils.dependencies import get_current_user

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.role = "authenticated"
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_svc = MagicMock()
    mock_svc.generate_suggestion = AsyncMock()
    mock_svc.get_suggestions = AsyncMock()
    mock_svc.accept_suggestion = AsyncMock()
    mock_svc.reject_suggestion = AsyncMock()
    mock_svc.dismiss_suggestion = AsyncMock()
    mock_svc.apply_suggestion = AsyncMock()
    mock_svc.get_suggestion_history = AsyncMock()

    with patch("app.routers.v1.suggestions.suggestion_service", mock_svc):
        with TestClient(app) as test_client:
            test_client.headers.update({"Authorization": "Bearer test-token"})
            test_client.mock_svc = mock_svc
            yield test_client

    app.dependency_overrides = {}


class TestGenerateSuggestion:
    def test_generate_success(self, client):
        client.mock_svc.generate_suggestion.return_value = {"id": "sg-1", "text": "Improved text"}
        response = client.post(
            "/api/v1/suggestions/generate",
            json={"document_id": "doc-1", "block": {"text": "old text"}, "suggestion_type": "clarity"},
        )
        assert response.status_code == 201
        data = get_enveloped_data(response)
        assert data["id"] == "sg-1"

    def test_generate_failure_returns_400(self, client):
        client.mock_svc.generate_suggestion.return_value = None
        response = client.post(
            "/api/v1/suggestions/generate",
            json={"document_id": "doc-1", "block": {"text": "old"}, "suggestion_type": "clarity"},
        )
        assert response.status_code == 400

    def test_generate_invalid_body_returns_422(self, client):
        response = client.post(
            "/api/v1/suggestions/generate",
            json={"document_id": "doc-1"},
        )
        assert response.status_code == 422

    def test_generate_with_session_id(self, client):
        client.mock_svc.generate_suggestion.return_value = {"id": "sg-2"}
        response = client.post(
            "/api/v1/suggestions/generate",
            json={"document_id": "doc-1", "block": {"text": "old"}, "suggestion_type": "clarity", "session_id": "sess-1"},
        )
        assert response.status_code == 201
        client.mock_svc.generate_suggestion.assert_called_with(
            document_id="doc-1", block={"text": "old"}, suggestion_type="clarity",
            user_id="user-123", session_id="sess-1",
        )


class TestGetDocumentSuggestions:
    def test_list_suggestions(self, client):
        client.mock_svc.get_suggestions.return_value = [{"id": "sg-1", "status": "pending"}]
        response = client.get("/api/v1/suggestions/document/doc-1")
        assert response.status_code == 200
        data = get_enveloped_data(response)
        assert data["total"] == 1

    def test_list_suggestions_with_status_filter(self, client):
        client.mock_svc.get_suggestions.return_value = []
        response = client.get("/api/v1/suggestions/document/doc-1?status=accepted&limit=10")
        assert response.status_code == 200
        client.mock_svc.get_suggestions.assert_called_with(document_id="doc-1", status="accepted", limit=10)

    def test_list_suggestions_empty(self, client):
        client.mock_svc.get_suggestions.return_value = []
        response = client.get("/api/v1/suggestions/document/doc-1")
        assert response.status_code == 200
        assert get_enveloped_data(response)["total"] == 0

    def test_list_suggestions_invalid_status(self, client):
        response = client.get("/api/v1/suggestions/document/doc-1?status=invalid")
        assert response.status_code == 422


class TestAcceptSuggestion:
    def test_accept_success(self, client):
        client.mock_svc.accept_suggestion.return_value = {"id": "sg-1", "status": "accepted"}
        response = client.post("/api/v1/suggestions/sg-1/accept")
        assert response.status_code == 200
        assert get_enveloped_data(response)["status"] == "accepted"

    def test_accept_not_found(self, client):
        client.mock_svc.accept_suggestion.return_value = None
        response = client.post("/api/v1/suggestions/sg-999/accept")
        assert response.status_code == 404


class TestRejectSuggestion:
    def test_reject_success(self, client):
        client.mock_svc.reject_suggestion.return_value = {"id": "sg-1", "status": "rejected"}
        response = client.post("/api/v1/suggestions/sg-1/reject")
        assert response.status_code == 200

    def test_reject_not_found(self, client):
        client.mock_svc.reject_suggestion.return_value = None
        response = client.post("/api/v1/suggestions/sg-999/reject")
        assert response.status_code == 404


class TestDismissSuggestion:
    def test_dismiss_success(self, client):
        client.mock_svc.dismiss_suggestion.return_value = {"id": "sg-1", "status": "dismissed"}
        response = client.post("/api/v1/suggestions/sg-1/dismiss")
        assert response.status_code == 200

    def test_dismiss_not_found(self, client):
        client.mock_svc.dismiss_suggestion.return_value = None
        response = client.post("/api/v1/suggestions/sg-999/dismiss")
        assert response.status_code == 404


class TestApplySuggestion:
    def test_apply_success(self, client):
        client.mock_svc.apply_suggestion.return_value = {"id": "sg-1", "applied": True}
        response = client.post("/api/v1/suggestions/sg-1/apply?document_id=doc-1")
        assert response.status_code == 200

    def test_apply_not_found(self, client):
        client.mock_svc.apply_suggestion.return_value = None
        response = client.post("/api/v1/suggestions/sg-999/apply?document_id=doc-1")
        assert response.status_code == 404

    def test_apply_missing_document_id(self, client):
        response = client.post("/api/v1/suggestions/sg-1/apply")
        assert response.status_code == 422


class TestGetSuggestionHistory:
    def test_history_success(self, client):
        client.mock_svc.get_suggestion_history.return_value = [{"id": "sg-1", "type": "clarity"}]
        response = client.get("/api/v1/suggestions/history")
        assert response.status_code == 200
        data = get_enveloped_data(response)
        assert data["total"] == 1

    def test_history_empty(self, client):
        client.mock_svc.get_suggestion_history.return_value = []
        response = client.get("/api/v1/suggestions/history")
        assert response.status_code == 200
        assert get_enveloped_data(response)["total"] == 0

    def test_history_with_limit(self, client):
        client.mock_svc.get_suggestion_history.return_value = []
        response = client.get("/api/v1/suggestions/history?limit=5")
        assert response.status_code == 200
        client.mock_svc.get_suggestion_history.assert_called_with(user_id="user-123", limit=5)

    def test_history_invalid_limit(self, client):
        response = client.get("/api/v1/suggestions/history?limit=200")
        assert response.status_code == 422
