# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from app.services.audit_log_service import AuditLogService


def _mock_supabase():
    sb = MagicMock()
    table = sb.table.return_value
    table.insert.return_value = table
    table.execute.return_value = None
    return sb, table


def _request(method: str, path: str, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_log_includes_timestamp_and_fields():
    service = AuditLogService()
    sb, table = _mock_supabase()

    with patch("app.services.audit_log_service.get_supabase_client", return_value=sb):
        await service.log(
            user_id="user-1",
            action="post_documents",
            resource_type="documents",
            resource_id="abc",
            ip_address="127.0.0.1",
            details={"status_code": 200},
        )

    payload = table.insert.call_args.args[0]
    assert payload["user_id"] == "user-1"
    assert payload["action"] == "post_documents"
    assert payload["resource_type"] == "documents"
    assert payload["resource_id"] == "abc"
    assert payload["ip_address"] == "127.0.0.1"
    assert payload["details"]["status_code"] == 200
    assert payload["details"]["timestamp"]
    assert payload["created_at"]


@pytest.mark.asyncio
async def test_log_http_write_derives_action_and_user():
    service = AuditLogService()
    sb, table = _mock_supabase()
    request = _request(
        "POST",
        "/api/v1/documents/upload",
        headers=[(b"authorization", b"Bearer token-123")],
    )

    with (
        patch("app.services.audit_log_service.get_supabase_client", return_value=sb),
        patch("app.services.audit_log_service.AuthService.decode_token", return_value={"sub": "user-9"}),
        patch("app.services.audit_log_service.AuthService.get_user_id_from_payload", return_value="user-9"),
    ):
        await service.log_http_write(request, status_code=202)

    payload = table.insert.call_args.args[0]
    assert payload["user_id"] == "user-9"
    assert payload["action"] == "post_documents"
    assert payload["resource_type"] == "documents"
    assert payload["resource_id"] == "upload"
    assert payload["details"]["path"] == "/api/v1/documents/upload"
    assert payload["details"]["status_code"] == 202


@pytest.mark.asyncio
async def test_log_http_write_skips_read_methods():
    service = AuditLogService()
    sb, table = _mock_supabase()
    request = _request("GET", "/api/v1/documents")

    with patch("app.services.audit_log_service.get_supabase_client", return_value=sb):
        await service.log_http_write(request, status_code=200)

    assert not table.insert.called
