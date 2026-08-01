# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import DatabaseUnavailableError, DocumentNotFoundError
from app.services.document_service import DocumentService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(*, data=None, count=None):
    r = MagicMock(spec=[])
    r.data = data
    r.count = count
    return r


def _self_chain(execute_return=None):
    """MagicMock where every method returns itself for fluent chaining."""
    c = MagicMock()
    c.table.return_value = c
    c.select.return_value = c
    c.eq.return_value = c
    c.order.return_value = c
    c.range.return_value = c
    c.maybe_single.return_value = c
    c.update.return_value = c
    c.delete.return_value = c
    c.upsert.return_value = c
    c.insert.return_value = c
    c.gte.return_value = c
    c.lt.return_value = c
    if execute_return is not None:
        c.execute.return_value = execute_return
    return c


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------

class TestIsTransientSupabaseError:
    def test_known_error_type(self):
        exc = type("RemoteProtocolError", (Exception,), {})()
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_connect_error(self):
        exc = type("ConnectError", (Exception,), {})()
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_read_timeout(self):
        exc = type("ReadTimeout", (Exception,), {})()
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_write_timeout(self):
        exc = type("WriteTimeout", (Exception,), {})()
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_message_marker_remoteprotocolerror(self):
        exc = Exception("RemoteProtocolError occurred")
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_message_marker_server_disconnected(self):
        exc = Exception("server disconnected")
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_message_marker_connection_reset(self):
        exc = Exception("connection reset")
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_message_marker_timed_out(self):
        exc = Exception("operation timed out")
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_non_transient_error(self):
        exc = ValueError("some other error")
        assert DocumentService._is_transient_supabase_error(exc) is False

    def test_empty_message(self):
        exc = Exception("")
        assert DocumentService._is_transient_supabase_error(exc) is False


class TestExecuteWithTransientRetry:
    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        op = MagicMock(return_value="ok")
        result = await DocumentService._execute_with_transient_retry("test", op)
        assert result == "ok"
        op.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_retry_on_transient_then_success(self):
        results = [Exception("connection reset"), Exception("timed out"), "ok"]
        op = MagicMock(side_effect=results)
        with patch.object(DocumentService, "_is_transient_supabase_error", side_effect=[True, True]):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                with patch("app.services.document_service.asyncio.sleep", AsyncMock()):
                    result = await DocumentService._execute_with_transient_retry("test", op)
        assert result == "ok"
        assert op.call_count == 3
        assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_non_transient_raised_immediately(self):
        op = MagicMock(side_effect=ValueError("boom"))
        with patch.object(DocumentService, "_is_transient_supabase_error", return_value=False):
            with pytest.raises(ValueError, match="boom"):
                await DocumentService._execute_with_transient_retry("test", op)
        op.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_transient_exhausts_retries(self):
        op = MagicMock(side_effect=Exception("connection reset"))
        with patch.object(DocumentService, "_is_transient_supabase_error", return_value=True):
            with patch("app.services.document_service.get_supabase_client"):
                with patch("app.services.document_service.asyncio.sleep", AsyncMock()):
                    with pytest.raises(Exception, match="connection reset"):
                        await DocumentService._execute_with_transient_retry("test", op, max_attempts=3)
        assert op.call_count == 3


class TestIsValidUuid:
    def test_valid_uuid(self):
        assert DocumentService._is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_none(self):
        assert DocumentService._is_valid_uuid(None) is False

    def test_empty_string(self):
        assert DocumentService._is_valid_uuid("") is False

    def test_short_string(self):
        assert DocumentService._is_valid_uuid("abc") is False

    def test_non_uuid_string(self):
        assert DocumentService._is_valid_uuid("not-a-uuid-at-all") is False

    def test_uuid_object_passed(self):
        import uuid
        assert DocumentService._is_valid_uuid(uuid.uuid4()) is True

    def test_integer(self):
        assert DocumentService._is_valid_uuid(12345) is False


class TestShouldQueryDocumentTables:
    def test_valid_uuid_returns_true(self):
        with patch.object(DocumentService, "_is_valid_uuid", return_value=True):
            assert DocumentService._should_query_document_tables("valid-uuid", "op") is True

    def test_invalid_uuid_returns_false_and_logs(self):
        with patch.object(DocumentService, "_is_valid_uuid", return_value=False):
            with patch("app.services.document_service.logger") as mock_log:
                result = DocumentService._should_query_document_tables("bad-id", "my_op")
        assert result is False
        mock_log.info.assert_called_once()


class TestBuildSignedDownloadScope:
    def test_basic_scope(self):
        scope = DocumentService._build_signed_download_scope(
            file_path="/uploads/doc.docx", download_format="docx", expires=1234567890,
        )
        assert scope == "/uploads/doc.docx|docx|1234567890"

    def test_normalizes_format(self):
        scope = DocumentService._build_signed_download_scope(
            file_path="/path/file.pdf", download_format="  PDF ", expires=100,
        )
        assert scope == "/path/file.pdf|pdf|100"

    def test_none_format_defaults_to_docx(self):
        scope = DocumentService._build_signed_download_scope(
            file_path="/path/file", download_format=None, expires=100,
        )
        assert scope == "/path/file|docx|100"


class TestGenerateSignedDownloadUrl:
    def test_generates_url(self):
        result = DocumentService.generate_signed_download_url(
            file_url="https://storage.example.com/files/doc.pdf?token=abc",
            file_path="/files/doc.pdf", secret="my-secret-key",
            expires_in_seconds=3600, download_format="pdf",
        )
        assert "url" in result
        assert "expires" in result
        assert result["url"].startswith("https://storage.example.com/files/doc.pdf")
        assert "token=" in result["url"]
        assert "expires=" in result["url"]

    def test_no_secret_raises(self):
        with pytest.raises(ValueError, match="SIGNED_URL_SECRET is required"):
            DocumentService.generate_signed_download_url(
                file_url="https://example.com/f", file_path="/f", secret="",
            )

    def test_uses_custom_expiry(self):
        result = DocumentService.generate_signed_download_url(
            file_url="https://example.com/f", file_path="/f",
            secret="secret", expires_in_seconds=60,
        )
        assert result["expires"] > int(time.time())
        assert result["expires"] < int(time.time()) + 120

    def test_integrity_signature_changes_with_file_path(self):
        r1 = DocumentService.generate_signed_download_url(
            file_url="https://example.com/a", file_path="/a", secret="s",
        )
        r2 = DocumentService.generate_signed_download_url(
            file_url="https://example.com/b", file_path="/b", secret="s",
        )
        assert r1["url"] != r2["url"]


class TestVerifySignedDownload:
    def test_valid_token(self):
        result = DocumentService.generate_signed_download_url(
            file_url="https://example.com/f", file_path="/f",
            secret="s", expires_in_seconds=3600,
        )
        url = result["url"]
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        assert DocumentService.verify_signed_download(
            file_path="/f", token=qs["token"][0], expires=qs["expires"][0], secret="s",
        ) is True

    def test_expired_token(self):
        assert DocumentService.verify_signed_download(
            file_path="/f", token="any", expires="1", secret="s",
        ) is False

    def test_invalid_token(self):
        expires = int(time.time()) + 3600
        assert DocumentService.verify_signed_download(
            file_path="/f", token="wrong", expires=str(expires), secret="s",
        ) is False

    def test_empty_secret(self):
        assert DocumentService.verify_signed_download(
            file_path="/f", token="t", expires="9999999999", secret="",
        ) is False

    def test_empty_token(self):
        assert DocumentService.verify_signed_download(
            file_path="/f", token="", expires="9999999999", secret="s",
        ) is False

    def test_bad_expires_string(self):
        assert DocumentService.verify_signed_download(
            file_path="/f", token="t", expires="not-a-number", secret="s",
        ) is False


# ---------------------------------------------------------------------------
# get_document
# ---------------------------------------------------------------------------

class TestGetDocument:
    @pytest.mark.asyncio
    async def test_returns_document(self):
        doc_data = {"id": "doc-1", "filename": "test.docx"}
        mock_result = _result(data=doc_data)
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", return_value=mock_result):
                    result = await DocumentService.get_document("550e8400-e29b-41d4-a716-446655440000")
        assert result == doc_data

    @pytest.mark.asyncio
    async def test_scoped_by_user_id(self):
        mock_result = _result(data={"id": "doc-1", "user_id": "user-1"})
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", return_value=mock_result):
                    result = await DocumentService.get_document(
                        "550e8400-e29b-41d4-a716-446655440000", "user-1",
                    )
        assert result == {"id": "doc-1", "user_id": "user-1"}

    @pytest.mark.asyncio
    async def test_none_when_should_not_query(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=False):
            result = await DocumentService.get_document("bad-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=None):
                with pytest.raises(DatabaseUnavailableError, match="not configured"):
                    await DocumentService.get_document("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.asyncio
    async def test_api_error_raises_database_unavailable(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", side_effect=Exception("db error")):
                    with pytest.raises(DatabaseUnavailableError):
                        await DocumentService.get_document("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.asyncio
    async def test_generic_exception_raises_database_unavailable(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", side_effect=RuntimeError("unexpected")):
                    with pytest.raises(DatabaseUnavailableError):
                        await DocumentService.get_document("550e8400-e29b-41d4-a716-446655440000")


# ---------------------------------------------------------------------------
# list_documents
# ---------------------------------------------------------------------------

class TestListDocuments:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        docs = [{"id": "1"}, {"id": "2"}]
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(data=docs)):
                result = await DocumentService.list_documents("user-1")
        assert result == docs

    @pytest.mark.asyncio
    async def test_empty_list_when_no_data(self):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(data=[])):
                result = await DocumentService.list_documents("user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_none_data_becomes_empty(self):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(data=None)):
                result = await DocumentService.list_documents("user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_filters_by_status(self):
        doc = _result(data=[])
        client = _self_chain(execute_return=doc)

        def run_to_thread(fn, *a, **kw):
            return fn(*a, **kw) if callable(fn) else fn

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=run_to_thread):
                await DocumentService.list_documents("user-1", status="processing")

        eq_calls = [c.args for c in client.eq.call_args_list]
        assert ("status", "PROCESSING") in eq_calls

    @pytest.mark.asyncio
    async def test_filters_by_template(self):
        doc = _result(data=[])
        client = _self_chain(execute_return=doc)

        def run_to_thread(fn, *a, **kw):
            return fn(*a, **kw) if callable(fn) else fn

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=run_to_thread):
                await DocumentService.list_documents("user-1", template="ieee")

        eq_calls = [c.args for c in client.eq.call_args_list]
        assert ("template", "IEEE") in eq_calls

    @pytest.mark.asyncio
    async def test_uses_correct_range(self):
        doc = _result(data=[])
        client = _self_chain(execute_return=doc)

        def run_to_thread(fn, *a, **kw):
            return fn(*a, **kw) if callable(fn) else fn

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=run_to_thread):
                await DocumentService.list_documents("user-1", limit=10, offset=20)

        client.order.assert_called_with("created_at", desc=True)
        client.range.assert_called_with(20, 29)

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError, match="not configured"):
                await DocumentService.list_documents("user-1")

    @pytest.mark.asyncio
    async def test_api_error_raises(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("API fail")):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.list_documents("user-1")

    @pytest.mark.asyncio
    async def test_exception_raises(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=RuntimeError("fail")):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.list_documents("user-1")


# ---------------------------------------------------------------------------
# count_documents
# ---------------------------------------------------------------------------

class TestCountDocuments:
    @pytest.mark.asyncio
    async def test_returns_count(self):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(count=5)):
                result = await DocumentService.count_documents("user-1")
        assert result == 5

    @pytest.mark.asyncio
    async def test_zero_when_none_count(self):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(count=None)):
                result = await DocumentService.count_documents("user-1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_filters_status(self):
        doc = _result(count=0)
        client = _self_chain(execute_return=doc)

        def run_to_thread(fn, *a, **kw):
            return fn(*a, **kw) if callable(fn) else fn

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=run_to_thread):
                await DocumentService.count_documents("user-1", status="completed")

        eq_calls = [c.args for c in client.eq.call_args_list]
        assert ("status", "COMPLETED") in eq_calls

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError):
                await DocumentService.count_documents("user-1")

    @pytest.mark.asyncio
    async def test_api_error(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("fail")):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.count_documents("user-1")


# ---------------------------------------------------------------------------
# count_uploads_today
# ---------------------------------------------------------------------------

class TestCountUploadsToday:
    @pytest.mark.asyncio
    async def test_returns_count(self):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(count=3)):
                result = await DocumentService.count_uploads_today("user-1")
        assert result == 3

    @pytest.mark.asyncio
    async def test_gte_and_lt_used(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lt.return_value.execute.return_value = _result(count=0)

        def run_to_thread(fn, *a, **kw):
            return fn(*a, **kw) if callable(fn) else fn

        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=run_to_thread):
                await DocumentService.count_uploads_today("user-1")

        base_chain = mock_client.table.return_value.select.return_value
        base_chain.eq.assert_called_with("user_id", "user-1")
        base_chain.eq.return_value.gte.assert_called_once()
        base_chain.eq.return_value.gte.return_value.lt.assert_called_once()

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError):
                await DocumentService.count_uploads_today("user-1")

    @pytest.mark.asyncio
    async def test_exception_handled(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("fail")):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.count_uploads_today("user-1")


# ---------------------------------------------------------------------------
# create_document
# ---------------------------------------------------------------------------

class TestCreateDocument:
    @pytest.mark.asyncio
    async def test_creates_and_returns(self):
        mock_result = _result(data=[{"id": "doc-1", "status": "PROCESSING"}])
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=mock_result):
                result = await DocumentService.create_document(
                    doc_id="550e8400-e29b-41d4-a716-446655440000",
                    user_id="user-1", filename="test.docx", template="ieee",
                )
        assert result == {"id": "doc-1", "status": "PROCESSING"}

    @pytest.mark.asyncio
    async def test_none_when_result_data_empty(self):
        mock_result = _result(data=[])
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=mock_result):
                result = await DocumentService.create_document(
                    doc_id="550e8400-e29b-41d4-a716-446655440000",
                    user_id="user-1", filename="test.docx", template=None,
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_none_user_id_omitted(self):
        def fake_thread(fn, payload=None):
            if payload is not None:
                return _result(data=[{"id": "x"}])
            return _result(data=[{"id": "x"}])

        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_thread) as mock_thread:
                await DocumentService.create_document(
                    doc_id="550e8400-e29b-41d4-a716-446655440000",
                    user_id=None, filename="test.docx", template=None,
                )
        payload = mock_thread.call_args[0][1]
        assert "user_id" not in payload

    @pytest.mark.asyncio
    async def test_file_hash_included_when_supported(self):
        DocumentService._supports_file_hash = None
        mock_result = _result(data=[{"id": "x"}])
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=mock_result) as mock_thread:
                await DocumentService.create_document(
                    doc_id="550e8400-e29b-41d4-a716-446655440000",
                    user_id="u", filename="f", template=None, file_hash="abc123",
                )
        payload = mock_thread.call_args[0][1]
        assert payload.get("file_hash") == "abc123"

    @pytest.mark.asyncio
    async def test_file_hash_retry_on_schema_miss(self):
        DocumentService._supports_file_hash = None
        DocumentService._file_hash_warning_logged = False

        exc = Exception('column "file_hash" of relation "documents" does not exist (PGRST204)')
        success_result = _result(data=[{"id": "x"}])
        call_count = 0

        async def fake_to_thread(fn, data=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise exc
            return success_result

        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_to_thread):
                result = await DocumentService.create_document(
                    doc_id="550e8400-e29b-41d4-a716-446655440000",
                    user_id="u", filename="f", template=None, file_hash="abc123",
                )
        assert result == {"id": "x"}
        assert DocumentService._supports_file_hash is False
        assert DocumentService._file_hash_warning_logged is True

    @pytest.mark.asyncio
    async def test_non_hash_error_raised(self):
        DocumentService._supports_file_hash = None
        exc = Exception("constraint violation")
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=exc):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.create_document(
                        doc_id="550e8400-e29b-41d4-a716-446655440000",
                        user_id="u", filename="f", template=None, file_hash="abc123",
                    )

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError):
                await DocumentService.create_document(
                    doc_id="550e8400-e29b-41d4-a716-446655440000",
                    user_id="u", filename="f", template=None,
                )

    @pytest.mark.asyncio
    async def test_retry_without_hash_fails_raises(self):
        DocumentService._supports_file_hash = None
        DocumentService._file_hash_warning_logged = False
        column_error = Exception('column "file_hash" does not exist (PGRST204)')
        retry_error = Exception("still broken after retry")
        call_count = 0

        async def fake_to_thread(fn, data=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise column_error
            raise retry_error

        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_to_thread):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.create_document(
                        doc_id="550e8400-e29b-41d4-a716-446655440000",
                        user_id="u", filename="f", template=None, file_hash="abc123",
                    )


# ---------------------------------------------------------------------------
# update_document
# ---------------------------------------------------------------------------

class TestUpdateDocument:
    @pytest.mark.asyncio
    async def test_updates_and_returns(self):
        mock_result = _result(data=[{"id": "doc-1", "status": "COMPLETED"}])
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=mock_result):
                result = await DocumentService.update_document(
                    "550e8400-e29b-41d4-a716-446655440000", {"status": "COMPLETED"},
                )
        assert result == {"id": "doc-1", "status": "COMPLETED"}

    @pytest.mark.asyncio
    async def test_none_when_empty_data(self):
        mock_result = _result(data=[])
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=mock_result):
                result = await DocumentService.update_document(
                    "550e8400-e29b-41d4-a716-446655440000", {"status": "COMPLETED"},
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError):
                await DocumentService.update_document("550e8400-e29b-41d4-a716-446655440000", {})

    @pytest.mark.asyncio
    async def test_api_error(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("fail")):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.update_document("550e8400-e29b-41d4-a716-446655440000", {})


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    @pytest.mark.asyncio
    async def test_deletes_successfully(self):
        doc = {"id": "doc-1", "output_path": None, "original_file_path": None}
        mock_result = _result(data=[{"id": "doc-1"}])
        with patch.object(DocumentService, "get_document", return_value=doc):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                client = MagicMock()
                client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
                mock_get.return_value = client
                with patch("app.services.document_service.os.remove"):
                    result = await DocumentService.delete_document("550e8400-e29b-41d4-a716-446655440000")
        assert result is True

    @pytest.mark.asyncio
    async def test_removes_files(self):
        doc = {"id": "doc-1", "output_path": "/tmp/output.docx", "original_file_path": "/tmp/original.docx"}
        mock_result = _result(data=[{"id": "doc-1"}])
        with patch.object(DocumentService, "get_document", return_value=doc):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                client = MagicMock()
                client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
                mock_get.return_value = client
                with patch("app.services.document_service.os.path.isfile", return_value=True):
                    with patch("app.services.document_service.os.remove") as mock_remove:
                        await DocumentService.delete_document("550e8400-e29b-41d4-a716-446655440000")
        assert mock_remove.call_count == 2

    @pytest.mark.asyncio
    async def test_file_remove_error_logged(self):
        doc = {"id": "doc-1", "output_path": "/tmp/output.docx", "original_file_path": None}
        mock_result = _result(data=[{"id": "doc-1"}])
        with patch.object(DocumentService, "get_document", return_value=doc):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                client = MagicMock()
                client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
                mock_get.return_value = client
                with patch("app.services.document_service.os.path.isfile", return_value=True):
                    with patch("app.services.document_service.os.remove", side_effect=OSError("permission denied")):
                        with patch("app.services.document_service.logger") as mock_log:
                            await DocumentService.delete_document("550e8400-e29b-41d4-a716-446655440000")
        mock_log.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        with patch.object(DocumentService, "get_document", return_value=None):
            with pytest.raises(DocumentNotFoundError):
                await DocumentService.delete_document("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with patch.object(DocumentService, "get_document", return_value={"id": "x"}):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.delete_document("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.asyncio
    async def test_zero_rows_affected_raises(self):
        mock_result = _result(data=[])
        with patch.object(DocumentService, "get_document", return_value={"id": "x"}):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                client = MagicMock()
                client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
                mock_get.return_value = client
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.delete_document("550e8400-e29b-41d4-a716-446655440000")


# ---------------------------------------------------------------------------
# update_output_hash
# ---------------------------------------------------------------------------

class TestUpdateOutputHash:
    @pytest.mark.asyncio
    async def test_success(self):
        DocumentService._supports_output_hash = None
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(data=None)):
                result = await DocumentService.update_output_hash("doc-1", "sha256abc")
        assert result is True
        assert DocumentService._supports_output_hash is True

    @pytest.mark.asyncio
    async def test_empty_hash_returns_false(self):
        assert await DocumentService.update_output_hash("doc-1", "") is False

    @pytest.mark.asyncio
    async def test_previously_failed_returns_false(self):
        DocumentService._supports_output_hash = False
        assert await DocumentService.update_output_hash("doc-1", "abc") is False

    @pytest.mark.asyncio
    async def test_no_supabase_returns_false(self):
        DocumentService._supports_output_hash = None
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            result = await DocumentService.update_output_hash("doc-1", "abc")
        assert result is False

    @pytest.mark.asyncio
    async def test_schema_miss_sets_flag(self):
        DocumentService._supports_output_hash = None
        DocumentService._output_hash_warning_logged = False
        exc = Exception('column "output_hash" does not exist (PGRST204)')
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=exc):
                result = await DocumentService.update_output_hash("doc-1", "abc")
        assert result is False
        assert DocumentService._supports_output_hash is False
        assert DocumentService._output_hash_warning_logged is True

    @pytest.mark.asyncio
    async def test_generic_exception_logged_returns_false(self):
        DocumentService._supports_output_hash = None
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("random error")):
                with patch("app.services.document_service.logger") as mock_log:
                    result = await DocumentService.update_output_hash("doc-1", "abc")
        assert result is False
        mock_log.error.assert_called_once()


# ---------------------------------------------------------------------------
# mark_document_failed  (never raises)
# ---------------------------------------------------------------------------

class TestMarkDocumentFailed:
    @pytest.mark.asyncio
    async def test_marks_failed(self):
        mock_result = _result(data=None)
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=mock_result):
                result = await DocumentService.mark_document_failed(
                    "550e8400-e29b-41d4-a716-446655440000", "error msg",
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_supabase_logs_and_returns(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with patch("app.services.document_service.logger") as mock_log:
                await DocumentService.mark_document_failed("550e8400-e29b-41d4-a716-446655440000", "err")
        mock_log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_logged_not_raised(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("db error")):
                with patch("app.services.document_service.logger") as mock_log:
                    await DocumentService.mark_document_failed(
                        "550e8400-e29b-41d4-a716-446655440000", "err",
                    )
        mock_log.error.assert_called_once()


# ---------------------------------------------------------------------------
# mark_document_completed  (never raises)
# ---------------------------------------------------------------------------

class TestMarkDocumentCompleted:
    @pytest.mark.asyncio
    async def test_marks_completed(self):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(data=None)):
                result = await DocumentService.mark_document_completed(
                    "550e8400-e29b-41d4-a716-446655440000", "/tmp/out.docx", raw_text="full text",
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_supabase_logs_and_returns(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with patch("app.services.document_service.logger") as mock_log:
                await DocumentService.mark_document_completed("550e8400-e29b-41d4-a716-446655440000", "/tmp/out.docx")
        mock_log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_none_raw_text_not_included(self):
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = _result(data=None)

        def fake_to_thread(fn, *a, **kw):
            return fn()

        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_to_thread):
                await DocumentService.mark_document_completed(
                    "550e8400-e29b-41d4-a716-446655440000", "/tmp/out.docx", raw_text=None,
                )

        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert "raw_text" not in update_call

    @pytest.mark.asyncio
    async def test_exception_logged_not_raised(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("db error")):
                with patch("app.services.document_service.logger") as mock_log:
                    await DocumentService.mark_document_completed(
                        "550e8400-e29b-41d4-a716-446655440000", "/tmp/out.docx",
                    )
        mock_log.error.assert_called_once()


# ---------------------------------------------------------------------------
# get_document_result
# ---------------------------------------------------------------------------

class TestGetDocumentResult:
    @pytest.mark.asyncio
    async def test_returns_data(self):
        result_data = {"document_id": "doc-1", "structured_data": {"key": "val"}}
        mock_result = SimpleNamespace(data=result_data)
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", return_value=mock_result):
                    result = await DocumentService.get_document_result("550e8400-e29b-41d4-a716-446655440000")
        assert result == result_data

    @pytest.mark.asyncio
    async def test_none_when_should_not_query(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=False):
            result = await DocumentService.get_document_result("bad-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_none_when_retry_returns_none(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", return_value=None):
                    result = await DocumentService.get_document_result("550e8400-e29b-41d4-a716-446655440000")
        assert result is None

    @pytest.mark.asyncio
    async def test_dict_result_extracts_data(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", return_value={"data": {"id": "x"}}):
                    result = await DocumentService.get_document_result("550e8400-e29b-41d4-a716-446655440000")
        assert result == {"id": "x"}

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=None):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.get_document_result("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.asyncio
    async def test_api_error(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", side_effect=Exception("fail")):
                    with pytest.raises(DatabaseUnavailableError):
                        await DocumentService.get_document_result("550e8400-e29b-41d4-a716-446655440000")


# ---------------------------------------------------------------------------
# upsert_document_result
# ---------------------------------------------------------------------------

class TestUpsertDocumentResult:
    @pytest.mark.asyncio
    async def test_upserts(self):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch("app.services.document_service.asyncio.to_thread", return_value=_result(data=None)):
                result = await DocumentService.upsert_document_result(
                    "550e8400-e29b-41d4-a716-446655440000", structured_data={"key": "val"},
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_structured_data_omitted(self):
        doc = _result(data=None)
        client = _self_chain(execute_return=doc)

        def fake_to_thread(fn, *a, **kw):
            return fn()

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_to_thread):
                await DocumentService.upsert_document_result("550e8400-e29b-41d4-a716-446655440000")

        payload = client.upsert.call_args[0][0]
        assert "structured_data" not in payload
        assert "validation_results" not in payload

    @pytest.mark.asyncio
    async def test_with_validation_results(self):
        doc = _result(data=None)
        client = _self_chain(execute_return=doc)

        def fake_to_thread(fn, *a, **kw):
            return fn()

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_to_thread):
                await DocumentService.upsert_document_result(
                    "550e8400-e29b-41d4-a716-446655440000", validation_results={"score": 0.9},
                )

        payload = client.upsert.call_args[0][0]
        assert payload.get("validation_results") == {"score": 0.9}

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError):
                await DocumentService.upsert_document_result("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.asyncio
    async def test_api_error(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("fail")):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.upsert_document_result("550e8400-e29b-41d4-a716-446655440000")


# ---------------------------------------------------------------------------
# get_processing_statuses
# ---------------------------------------------------------------------------

class TestGetProcessingStatuses:
    @pytest.mark.asyncio
    async def test_returns_statuses(self):
        status_data = [{"phase": "EXTRACTION", "status": "running"}]
        mock_result = _result(data=status_data)
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", return_value=mock_result):
                    result = await DocumentService.get_processing_statuses("550e8400-e29b-41d4-a716-446655440000")
        assert result == status_data

    @pytest.mark.asyncio
    async def test_empty_when_should_not_query(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=False):
            result = await DocumentService.get_processing_statuses("bad-id")
        assert result == []

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=None):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.get_processing_statuses("550e8400-e29b-41d4-a716-446655440000")

    @pytest.mark.asyncio
    async def test_api_error(self):
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_get.return_value = MagicMock()
                with patch.object(DocumentService, "_execute_with_transient_retry", side_effect=Exception("fail")):
                    with pytest.raises(DatabaseUnavailableError):
                        await DocumentService.get_processing_statuses("550e8400-e29b-41d4-a716-446655440000")


# ---------------------------------------------------------------------------
# upsert_processing_status
# ---------------------------------------------------------------------------

class TestUpsertProcessingStatus:
    @pytest.mark.asyncio
    async def test_upserts_with_all_fields(self):
        doc = _result(data=None)
        client = _self_chain(execute_return=doc)

        def fake_to_thread(fn, *a, **kw):
            return fn()

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_to_thread):
                await DocumentService.upsert_processing_status(
                    "550e8400-e29b-41d4-a716-446655440000",
                    phase="EXTRACTION", status="running",
                    progress_percentage=50, message="extracting text",
                )

        payload = client.upsert.call_args[0][0]
        assert payload["document_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert payload["phase"] == "EXTRACTION"
        assert payload["status"] == "running"
        assert payload["progress_percentage"] == 50
        assert payload["message"] == "extracting text"

    @pytest.mark.asyncio
    async def test_optional_fields_omitted(self):
        doc = _result(data=None)
        client = _self_chain(execute_return=doc)

        def fake_to_thread(fn, *a, **kw):
            return fn()

        with patch("app.services.document_service.get_supabase_client", return_value=client):
            with patch("app.services.document_service.asyncio.to_thread", side_effect=fake_to_thread):
                await DocumentService.upsert_processing_status(
                    "550e8400-e29b-41d4-a716-446655440000",
                    phase="EXTRACTION", status="running",
                )

        payload = client.upsert.call_args[0][0]
        assert "progress_percentage" not in payload
        assert "message" not in payload

    @pytest.mark.asyncio
    async def test_supabase_unavailable(self):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError):
                await DocumentService.upsert_processing_status(
                    "550e8400-e29b-41d4-a716-446655440000", "EXTRACTION", "running",
                )

    @pytest.mark.asyncio
    async def test_api_error(self):
        with patch("app.services.document_service.get_supabase_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch("app.services.document_service.asyncio.to_thread", side_effect=Exception("fail")):
                with pytest.raises(DatabaseUnavailableError):
                    await DocumentService.upsert_processing_status(
                        "550e8400-e29b-41d4-a716-446655440000", "EXTRACTION", "running",
                    )
