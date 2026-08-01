# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import base64
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# ── Pure utility tests ─────────────────────────────────────────────────────────


class TestCursorEncoding:
    def test_cursor_encoding_decoding(self):
        from app.utils.pagination import decode_cursor, encode_cursor

        original = "2026-07-08T12:34:56.789000"
        encoded = encode_cursor(original)
        assert isinstance(encoded, str)
        assert "=" not in encoded.rstrip("=")
        decoded = decode_cursor(encoded)
        assert decoded == original

    def test_encode_cursor_with_timestamp(self):
        from app.utils.pagination import encode_cursor

        ts = datetime(2026, 7, 8, 12, 34, 56, tzinfo=UTC)
        encoded = encode_cursor(ts.isoformat())
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_decode_padded_cursor(self):
        from app.utils.pagination import decode_cursor

        raw = b"2026-07-08T12:00:00"
        encoded = base64.urlsafe_b64encode(raw).decode("utf-8")
        decoded = decode_cursor(encoded)
        assert decoded == "2026-07-08T12:00:00"

    def test_invalid_cursor_raises_422(self):
        from app.utils.pagination import decode_cursor

        with pytest.raises(HTTPException) as exc:
            decode_cursor("not-valid-base64!!!")
        assert exc.value.status_code == 422

    def test_empty_string_cursor_decodes_to_empty(self):
        from app.utils.pagination import decode_cursor

        result = decode_cursor("")
        assert result == ""

    def test_encode_empty_string(self):
        from app.utils.pagination import encode_cursor

        encoded = encode_cursor("")
        assert isinstance(encoded, str)


class TestCursorPageBuilding:
    def test_empty_page(self):
        from app.utils.pagination import build_cursor_response

        params = type("_", (), {"limit": 50, "cursor": None, "order_dir": "desc"})()
        result = build_cursor_response([], params)
        assert result["items"] == []
        assert result["next_cursor"] is None
        assert result["has_more"] is False
        assert result["total"] is None

    def test_page_with_items(self):
        from app.utils.pagination import build_cursor_response

        items = [
            {"id": "1", "created_at": "2026-07-08T12:00:00"},
            {"id": "2", "created_at": "2026-07-08T11:00:00"},
        ]
        params = type("_", (), {"limit": 50, "cursor": None, "order_dir": "desc"})()
        result = build_cursor_response(items, params)
        assert len(result["items"]) == 2
        assert result["has_more"] is False

    def test_next_cursor_generated_when_more_items(self):
        from app.utils.pagination import build_cursor_response

        items = [
            {"id": str(i), "created_at": f"2026-07-08T{12 - i // 60:02d}:{i % 60:02d}:00"}
            for i in range(51)
        ]
        params = type("_", (), {"limit": 50, "cursor": None, "order_dir": "desc"})()
        result = build_cursor_response(items, params)
        assert len(result["items"]) == 50
        assert result["has_more"] is True
        assert result["next_cursor"] is not None

    def test_no_next_cursor_when_under_limit(self):
        from app.utils.pagination import build_cursor_response

        items = [{"id": "1", "created_at": "2026-07-08T12:00:00"}]
        params = type("_", (), {"limit": 50, "cursor": None, "order_dir": "desc"})()
        result = build_cursor_response(items, params)
        assert len(result["items"]) == 1
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    def test_exactly_limit_items_no_next_cursor(self):
        from app.utils.pagination import build_cursor_response

        items = [{"id": str(i), "created_at": f"2026-07-08T12:{i:02d}:00"} for i in range(50)]
        params = type("_", (), {"limit": 50, "cursor": None, "order_dir": "desc"})()
        result = build_cursor_response(items, params)
        assert len(result["items"]) == 50
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    def test_cursor_with_datetime_objects(self):
        from app.utils.pagination import build_cursor_response

        items = [
            {"id": "1", "created_at": datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)},
            {"id": "2", "created_at": datetime(2026, 7, 8, 11, 0, 0, tzinfo=UTC)},
            {"id": "3", "created_at": datetime(2026, 7, 8, 10, 0, 0, tzinfo=UTC)},
        ]
        params = type("_", (), {"limit": 2, "cursor": None, "order_dir": "desc"})()
        result = build_cursor_response(items, params)
        assert len(result["items"]) == 2
        assert result["has_more"] is True
        assert result["next_cursor"] is not None


class TestBuildCursorQuery:
    def _make_chainable_mock(self):
        """Return a MagicMock where every method returns self for chaining."""
        m = MagicMock()
        m.lt.return_value = m
        m.gt.return_value = m
        m.order.return_value = m
        m.limit.return_value = m
        return m

    def test_applies_lt_for_desc_order(self):
        from app.utils.pagination import build_cursor_query, encode_cursor

        mock_query = self._make_chainable_mock()
        cursor_val = encode_cursor("2026-07-08T12:00:00")
        params = type("_", (), {"cursor": cursor_val, "limit": 50, "order_by": "created_at", "order_dir": "desc"})()
        build_cursor_query(mock_query, params)
        mock_query.lt.assert_called_once_with("created_at", "2026-07-08T12:00:00")
        mock_query.order.assert_called_once_with("created_at", desc=True)
        mock_query.limit.assert_called_once_with(51)

    def test_applies_gt_for_asc_order(self):
        from app.utils.pagination import build_cursor_query, encode_cursor

        mock_query = self._make_chainable_mock()
        cursor_val = encode_cursor("2026-07-08T12:00:00")
        params = type("_", (), {"cursor": cursor_val, "limit": 50, "order_by": "created_at", "order_dir": "asc"})()
        build_cursor_query(mock_query, params)
        mock_query.gt.assert_called_once_with("created_at", "2026-07-08T12:00:00")
        mock_query.order.assert_called_once_with("created_at", desc=False)
        mock_query.limit.assert_called_once_with(51)

    def test_no_cursor_first_page(self):
        from app.utils.pagination import build_cursor_query

        mock_query = self._make_chainable_mock()
        params = type("_", (), {"cursor": None, "limit": 50, "order_by": "created_at", "order_dir": "desc"})()
        build_cursor_query(mock_query, params)
        mock_query.lt.assert_not_called()
        mock_query.gt.assert_not_called()
        mock_query.order.assert_called_once_with("created_at", desc=True)
        mock_query.limit.assert_called_once_with(51)


# ── Integration-style endpoint tests ─────────────────────────────────────────


def _make_mock_user():
    user = MagicMock()
    user.id = "user-123"
    return user


def _make_chainable_query():
    """Return a MagicMock that returns self for all chaining methods."""
    m = MagicMock()
    m.select.return_value = m
    m.eq.return_value = m
    m.lt.return_value = m
    m.gt.return_value = m
    m.order.return_value = m
    m.limit.return_value = m
    m.execute = MagicMock(return_value=MagicMock(data=[]))
    return m


@pytest.fixture
def client():
    from app.main import app

    mock_user = _make_mock_user()
    app.dependency_overrides = {}

    from app.utils.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_sb = MagicMock()

    with (
        TestClient(app) as test_client,
    ):
        test_client.mock_sb = mock_sb
        yield test_client

    app.dependency_overrides = {}


class TestV2DocumentsEndpoint:
    def test_v2_list_documents(self, client):
        mock_query = _make_chainable_query()
        mock_query.execute.return_value = MagicMock(data=[
            {"id": "doc-1", "filename": "paper.docx", "template": "IEEE", "status": "COMPLETED", "progress": 100,
             "current_stage": "DONE", "error_message": None, "created_at": "2026-07-08T12:00:00",
             "updated_at": "2026-07-08T12:30:00"},
            {"id": "doc-2", "filename": "draft.docx", "template": "APA", "status": "PROCESSING", "progress": 50,
             "current_stage": "FORMATTING", "error_message": None, "created_at": "2026-07-08T11:00:00",
             "updated_at": "2026-07-08T11:30:00"},
        ])

        client.mock_sb.table.return_value = mock_query

        with patch("app.db.supabase_client.get_supabase_client", return_value=client.mock_sb):
            response = client.get("/api/v2/documents")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == "doc-1"
        assert data["items"][0]["filename"] == "paper.docx"
        assert data["items"][1]["id"] == "doc-2"
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "2"

    def test_v2_list_documents_empty(self, client):
        mock_query = _make_chainable_query()
        mock_query.execute.return_value = MagicMock(data=[])

        client.mock_sb.table.return_value = mock_query

        with patch("app.db.supabase_client.get_supabase_client", return_value=client.mock_sb):
            response = client.get("/api/v2/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_v2_list_documents_with_filters(self, client):
        mock_query = _make_chainable_query()
        mock_query.execute.return_value = MagicMock(data=[
            {"id": "doc-1", "filename": "paper.docx", "template": "IEEE", "status": "COMPLETED", "progress": 100,
             "current_stage": "DONE", "error_message": None, "created_at": "2026-07-08T12:00:00",
             "updated_at": "2026-07-08T12:30:00"},
        ])

        client.mock_sb.table.return_value = mock_query

        with patch("app.db.supabase_client.get_supabase_client", return_value=client.mock_sb):
            response = client.get("/api/v2/documents?status=COMPLETED&template=IEEE")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "COMPLETED"

    def test_v2_list_documents_with_cursor(self, client):
        from app.utils.pagination import encode_cursor

        mock_query = _make_chainable_query()
        mock_query.execute.return_value = MagicMock(data=[
            {"id": "doc-3", "filename": "older.docx", "template": "Springer", "status": "COMPLETED", "progress": 100,
             "current_stage": "DONE", "error_message": None, "created_at": "2026-07-07T10:00:00",
             "updated_at": "2026-07-07T10:30:00"},
        ])

        client.mock_sb.table.return_value = mock_query
        cursor = encode_cursor("2026-07-08T12:00:00")

        with patch("app.db.supabase_client.get_supabase_client", return_value=client.mock_sb):
            response = client.get(f"/api/v2/documents?cursor={cursor}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    def test_v2_list_documents_limit_validation(self, client):
        response = client.get("/api/v2/documents?limit=0")
        assert response.status_code == 422

        response = client.get("/api/v2/documents?limit=101")
        assert response.status_code == 422

        with patch("app.db.supabase_client.get_supabase_client", return_value=client.mock_sb):
            mock_q = _make_chainable_query()
            mock_q.execute.return_value = MagicMock(data=[])
            client.mock_sb.table.return_value = mock_q
            response = client.get("/api/v2/documents?limit=50")
        assert response.status_code == 200

    def test_v2_list_documents_invalid_cursor(self, client):
        with patch("app.db.supabase_client.get_supabase_client", return_value=client.mock_sb):
            response = client.get("/api/v2/documents?cursor=invalid!!!")
        assert response.status_code == 422


class TestV2DocumentsEndpointAuth:
    def test_v2_list_documents_no_auth(self):
        from app.main import app

        app.dependency_overrides = {}
        with TestClient(app) as test_client:
            response = test_client.get("/api/v2/documents")

        assert response.status_code == 401
        app.dependency_overrides = {}

    def test_v2_list_documents_with_auth_override(self):
        from app.main import app
        from app.utils.dependencies import get_current_user

        mock_user = _make_mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_query = _make_chainable_query()
        mock_query.execute.return_value = MagicMock(data=[])
        mock_sb = MagicMock()
        mock_sb.table.return_value = mock_query

        with (
            patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb),
            TestClient(app) as test_client,
        ):
            response = test_client.get("/api/v2/documents")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        app.dependency_overrides = {}
