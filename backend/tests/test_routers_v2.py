# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class TestToDocumentListItem:
    def test_empty_dict(self):
        from app.routers.v2.documents import _to_document_list_item

        result = _to_document_list_item({})
        assert result == {
            "id": "None",
            "filename": None,
            "template": None,
            "status": None,
            "progress": 0,
            "current_stage": None,
            "error_message": None,
            "created_at": None,
            "updated_at": None,
        }

    def test_full_dict(self):
        from app.routers.v2.documents import _to_document_list_item

        doc = {
            "id": "doc-42",
            "filename": "paper.pdf",
            "template": "IEEE",
            "status": "COMPLETED",
            "progress": 100,
            "current_stage": "done",
            "error_message": None,
            "created_at": "2026-06-01T00:00:00",
            "updated_at": "2026-06-02T00:00:00",
        }
        result = _to_document_list_item(doc)
        assert result == doc

    def test_partial_dict(self):
        from app.routers.v2.documents import _to_document_list_item

        result = _to_document_list_item({"id": "doc-1", "filename": "draft.docx"})
        assert result["id"] == "doc-1"
        assert result["filename"] == "draft.docx"
        assert result["template"] is None
        assert result["status"] is None

    def test_progress_defaults_to_zero(self):
        from app.routers.v2.documents import _to_document_list_item

        result = _to_document_list_item({"id": "x"})
        assert result["progress"] == 0

    def test_progress_preserved_when_present(self):
        from app.routers.v2.documents import _to_document_list_item

        result = _to_document_list_item({"id": "x", "progress": 75})
        assert result["progress"] == 75

    def test_status_and_template_preserved_as_is(self):
        from app.routers.v2.documents import _to_document_list_item

        result = _to_document_list_item({"id": "x", "status": "processing", "template": "apa7"})
        assert result["status"] == "processing"
        assert result["template"] == "apa7"

    def test_id_is_stringified(self):
        from app.routers.v2.documents import _to_document_list_item

        result = _to_document_list_item({"id": 42})
        assert result["id"] == "42"


class TestRequireDb:
    def test_no_client_raises(self):
        from app.routers.v2.documents import _require_db

        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            with pytest.raises(HTTPException) as exc:
                _require_db()
        assert exc.value.status_code == 503
        assert "Database not configured" in exc.value.detail

    def test_with_client_ok(self):
        from app.routers.v2.documents import _require_db

        with patch("app.db.supabase_client.get_supabase_client", return_value=MagicMock()):
            _require_db()


class TestV2WebhooksReexport:
    def test_router_is_v1_router(self):
        from app.routers.v1.webhooks import router as v1_router
        from app.routers.v2.webhooks import router as v2_router

        assert v2_router is v1_router


class TestListDocuments:
    def _make_query_chain(self, mock_result):
        """Build a chainable mock that returns itself from .eq() and has a sync .execute."""
        chain = MagicMock()
        chain.execute = MagicMock(return_value=mock_result)
        chain.eq = MagicMock(return_value=chain)
        return chain

    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v2.documents import list_documents

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "d1", "filename": "a.pdf", "status": "DONE", "progress": 100},
        ]

        chain = self._make_query_chain(mock_result)
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value = chain

        with (
            patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb),
            patch("app.utils.pagination.build_cursor_query", return_value=chain),
            patch(
                "app.utils.pagination.build_cursor_response",
                return_value={
                    "items": [{"id": "d1", "filename": "a.pdf", "status": "DONE", "progress": 100}],
                    "next_cursor": None,
                    "has_more": False,
                },
            ),
        ):
            response = await list_documents(
                request=MagicMock(),
                cursor=None,
                limit=50,
                order_by="created_at",
                order_dir="desc",
                status=None,
                template=None,
                current_user=MagicMock(id="user-1"),
            )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "2"
        import json

        data = json.loads(response.body)
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "d1"
        assert data["next_cursor"] is None
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_with_status_filter(self):
        from app.routers.v2.documents import list_documents

        mock_result = MagicMock()
        mock_result.data = []
        chain = self._make_query_chain(mock_result)
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value = chain

        with (
            patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb),
            patch("app.utils.pagination.build_cursor_query", return_value=chain),
            patch(
                "app.utils.pagination.build_cursor_response",
                return_value={"items": [], "next_cursor": None, "has_more": False},
            ),
        ):
            response = await list_documents(
                request=MagicMock(),
                cursor=None,
                limit=50,
                order_by="created_at",
                order_dir="desc",
                status="processing",
                template=None,
                current_user=MagicMock(id="user-1"),
            )

        assert response.status_code == 200
        # Verify the status filter was applied (second .eq call)
        eq_calls = chain.eq.call_args_list
        assert any(call[0] == ("status", "PROCESSING") for call in eq_calls)

    @pytest.mark.asyncio
    async def test_with_template_filter(self):
        from app.routers.v2.documents import list_documents

        mock_result = MagicMock()
        mock_result.data = []
        chain = self._make_query_chain(mock_result)
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value = chain

        with (
            patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb),
            patch("app.utils.pagination.build_cursor_query", return_value=chain),
            patch(
                "app.utils.pagination.build_cursor_response",
                return_value={"items": [], "next_cursor": None, "has_more": False},
            ),
        ):
            response = await list_documents(
                request=MagicMock(),
                cursor=None,
                limit=50,
                order_by="created_at",
                order_dir="desc",
                status=None,
                template="ieee",
                current_user=MagicMock(id="user-1"),
            )

        assert response.status_code == 200
        eq_calls = chain.eq.call_args_list
        assert any(call[0] == ("template", "IEEE") for call in eq_calls)

    @pytest.mark.asyncio
    async def test_supabase_none_raises_503(self):
        from app.routers.v2.documents import list_documents

        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        with patch("app.db.supabase_client.get_supabase_client", side_effect=[MagicMock(), None]):
            with pytest.raises(HTTPException) as exc:
                await list_documents(
                    request=mock_request,
                    cursor=None,
                    limit=50,
                    order_by="created_at",
                    order_dir="desc",
                    status=None,
                    template=None,
                    current_user=mock_user,
                )
        assert exc.value.status_code == 503
        assert "Database not available" in exc.value.detail

    @pytest.mark.asyncio
    async def test_execute_failure_raises_500(self):
        from app.routers.v2.documents import list_documents

        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        mock_sb = MagicMock()

        query_chain = self._make_query_chain(MagicMock())
        query_chain.execute = MagicMock(side_effect=Exception("connection lost"))

        mock_sb.table.return_value.select.return_value = query_chain

        with (
            patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb),
            patch("app.utils.pagination.build_cursor_query", return_value=query_chain),
        ):
            with pytest.raises(HTTPException) as exc:
                await list_documents(
                    request=mock_request,
                    cursor=None,
                    limit=50,
                    order_by="created_at",
                    order_dir="desc",
                    status=None,
                    template=None,
                    current_user=mock_user,
                )
        assert exc.value.status_code == 500
        assert "Internal server error" in exc.value.detail

    @pytest.mark.asyncio
    async def test_with_cursor_pagination(self):
        from app.routers.v2.documents import list_documents

        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "d1", "filename": "a.pdf", "created_at": "2026-06-01T00:00:00"},
            {"id": "d2", "filename": "b.pdf", "created_at": "2026-06-02T00:00:00"},
        ]

        chain = self._make_query_chain(mock_result)
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value = chain

        with (
            patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb),
            patch("app.utils.pagination.build_cursor_query", return_value=chain),
            patch(
                "app.utils.pagination.build_cursor_response",
                return_value={
                    "items": [
                        {"id": "d1", "filename": "a.pdf", "created_at": "2026-06-01T00:00:00"},
                        {"id": "d2", "filename": "b.pdf", "created_at": "2026-06-02T00:00:00"},
                    ],
                    "next_cursor": "cursor-abc",
                    "has_more": True,
                },
            ),
        ):
            response = await list_documents(
                request=mock_request,
                cursor="previous-cursor-value",
                limit=50,
                order_by="created_at",
                order_dir="desc",
                status=None,
                template=None,
                current_user=mock_user,
            )

        assert response.status_code == 200
        import json

        data = json.loads(response.body)
        assert data["next_cursor"] == "cursor-abc"
        assert data["has_more"] is True
        assert len(data["items"]) == 2
