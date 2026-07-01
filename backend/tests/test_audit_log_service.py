from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest


class TestGetUserById:
    @pytest.mark.asyncio
    async def test_returns_user(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        svc._audit_table_available = None
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch("app.services.audit_log_service.get_supabase_client", return_value=mock_client):
            await svc.log("user-1", "create", "document", "doc-1", "127.0.0.1", {"key": "val"})
        assert svc._audit_table_available is True

    @pytest.mark.asyncio
    async def test_skips_when_table_unavailable(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        svc._audit_table_available = False
        with patch("app.services.audit_log_service.get_supabase_client") as mock_get:
            await svc.log("user-1", "create", "document", "doc-1", "127.0.0.1")
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_marks_table_unavailable_on_insert_error(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        svc._audit_table_available = None
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
            'Could not find the table "audit_log"'
        )
        with patch("app.services.audit_log_service.get_supabase_client", return_value=mock_client):
            await svc.log("user-1", "create", "document", "doc-1", "127.0.0.1")
        assert svc._audit_table_available is False

    @pytest.mark.asyncio
    async def test_skips_when_supabase_unavailable(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        svc._audit_table_available = None
        with patch("app.services.audit_log_service.get_supabase_client", return_value=None):
            await svc.log("user-1", "create", "document", "doc-1", "127.0.0.1")
        assert svc._audit_table_available is None


class TestExtractResource:
    def test_api_v1_path(self):
        from app.services.audit_log_service import AuditLogService
        rtype, rid = AuditLogService._extract_resource("/api/v1/documents/doc-123")
        assert rtype == "documents"
        assert rid == "doc-123"

    def test_no_segments(self):
        from app.services.audit_log_service import AuditLogService
        rtype, rid = AuditLogService._extract_resource("")
        assert rtype == "root"
        assert rid is None


class TestExtractUserId:
    def test_valid_bearer(self):
        from app.services.audit_log_service import AuditLogService
        with patch("app.services.audit_log_service.AuthService.decode_token", return_value={"sub": "user-1"}):
            with patch("app.services.audit_log_service.AuthService.get_user_id_from_payload", return_value="user-1"):
                uid = AuditLogService._extract_user_id_from_auth_header("Bearer token123")
        assert uid == "user-1"

    def test_no_header(self):
        from app.services.audit_log_service import AuditLogService
        assert AuditLogService._extract_user_id_from_auth_header(None) is None

    def test_non_bearer(self):
        from app.services.audit_log_service import AuditLogService
        assert AuditLogService._extract_user_id_from_auth_header("Basic abc") is None


class TestUtcNowIso:
    def test_returns_iso_string(self):
        from app.services.audit_log_service import AuditLogService
        iso = AuditLogService._utc_now_iso()
        assert "T" in iso


class TestLogHttpWrite:
    @pytest.mark.asyncio
    async def test_skips_get_method(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/v1/documents/doc-123"
        with patch.object(svc, "log", MagicMock()) as mock_log:
            await svc.log_http_write(request, status_code=200)
        mock_log.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_post(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents"
        request.url.query = ""
        request.headers = {"authorization": "Bearer test-token", "x-request-id": "req-123"}
        request.client.host = "1.2.3.4"
        with patch.object(svc, "log", AsyncMock()) as mock_log:
            with patch.object(svc, "_extract_user_id_from_auth_header", return_value="user-1"):
                await svc.log_http_write(request, status_code=201, details={"extra": "info"})
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["action"] == "post_documents"
        assert call_kwargs["resource_type"] == "documents"
        assert call_kwargs["ip_address"] == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_logs_delete(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        request = MagicMock()
        request.method = "DELETE"
        request.url.path = "/api/v1/documents/doc-123"
        request.url.query = ""
        request.headers = {}
        request.client.host = None
        with patch.object(svc, "log", AsyncMock()) as mock_log:
            with patch.object(svc, "_extract_user_id_from_auth_header", return_value=None):
                await svc.log_http_write(request, status_code=204)
        mock_log.assert_called_once()
        assert mock_log.call_args[1]["resource_id"] == "doc-123"
        assert mock_log.call_args[1]["action"] == "delete_documents"
        assert mock_log.call_args[1]["ip_address"] is None

    @pytest.mark.asyncio
    async def test_logs_without_details(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        request = MagicMock()
        request.method = "PUT"
        request.url.path = "/api/v1/documents/doc-123"
        request.url.query = "version=2"
        request.headers = {}
        request.client.host = "5.6.7.8"
        with patch.object(svc, "log", AsyncMock()) as mock_log:
            with patch.object(svc, "_extract_user_id_from_auth_header", return_value=None):
                await svc.log_http_write(request, status_code=200)
        mock_log.assert_called_once()
        assert mock_log.call_args[1]["details"]["method"] == "PUT"
        assert mock_log.call_args[1]["details"]["query"] == "version=2"


class TestExtractResourceExtended:
    def test_root_path(self):
        from app.services.audit_log_service import AuditLogService
        rtype, rid = AuditLogService._extract_resource("/")
        assert rtype == "root"
        assert rid is None

    def test_deep_nested_path(self):
        from app.services.audit_log_service import AuditLogService
        rtype, rid = AuditLogService._extract_resource("/api/v1/users/user-1/settings/theme")
        assert rtype == "users"
        assert rid == "user-1"


class TestExtractUserIdExtended:
    def test_empty_token_after_bearer(self):
        from app.services.audit_log_service import AuditLogService
        uid = AuditLogService._extract_user_id_from_auth_header("Bearer ")
        assert uid is None

    def test_decode_exception_returns_none(self):
        from app.services.audit_log_service import AuditLogService
        with patch("app.services.audit_log_service.AuthService.decode_token", side_effect=ValueError("bad token")):
            uid = AuditLogService._extract_user_id_from_auth_header("Bearer invalid")
        assert uid is None


class TestLogMissingAuditTable:
    @pytest.mark.asyncio
    async def test_non_audit_table_error_still_logs(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        svc._audit_table_available = None
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
            'Could not find something else'
        )
        with patch("app.services.audit_log_service.get_supabase_client", return_value=mock_client):
            await svc.log("user-1", "create", "document", "doc-1", "127.0.0.1")
        assert svc._audit_table_available is None

    @pytest.mark.asyncio
    async def test_missing_audit_table_sets_unavailable(self):
        from app.services.audit_log_service import AuditLogService
        svc = AuditLogService()
        svc._audit_table_available = None
        svc._audit_table_warning_logged = False
        mock_client = MagicMock()
        text = 'Could not find the table "audit_log" in the current session'
        mock_client.table.return_value.insert.return_value.execute.side_effect = RuntimeError(text)
        with patch("app.services.audit_log_service.get_supabase_client", return_value=mock_client):
            await svc.log("user-1", "create", "document", "doc-1", "127.0.0.1")
        assert svc._audit_table_available is False
        assert svc._audit_table_warning_logged is True
