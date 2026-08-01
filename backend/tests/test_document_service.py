import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestTransientError:
    def test_transient_by_type_name(self):
        from app.services.document_service import DocumentService
        exc = type("RemoteProtocolError", (Exception,), {})()
        assert DocumentService._is_transient_supabase_error(exc) is True

    def test_non_transient_type(self):
        from app.services.document_service import DocumentService
        assert DocumentService._is_transient_supabase_error(ValueError()) is False

    def test_transient_by_message_marker(self):
        from app.services.document_service import DocumentService
        exc = RuntimeError("Server disconnected")
        assert DocumentService._is_transient_supabase_error(exc) is True
        exc2 = RuntimeError("permanent failure")
        assert DocumentService._is_transient_supabase_error(exc2) is False

    def test_transient_connection_refused(self):
        from app.services.document_service import DocumentService
        exc = OSError("connection refused")
        assert DocumentService._is_transient_supabase_error(exc) is True


class TestValidUuid:
    def test_valid_uuid(self):
        from app.services.document_service import DocumentService
        assert DocumentService._is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_invalid_uuid(self):
        from app.services.document_service import DocumentService
        assert DocumentService._is_valid_uuid("not-a-uuid") is False

    def test_empty_string(self):
        from app.services.document_service import DocumentService
        assert DocumentService._is_valid_uuid("") is False


class TestShouldQuery:
    def test_valid_uuid_returns_true(self):
        from app.services.document_service import DocumentService
        assert DocumentService._should_query_document_tables("550e8400-e29b-41d4-a716-446655440000", "test") is True

    def test_invalid_uuid_returns_false(self):
        from app.services.document_service import DocumentService
        assert DocumentService._should_query_document_tables("bad-id", "test") is False


class TestBuildSignedDownloadScope:
    def test_basic_scope(self):
        from app.services.document_service import DocumentService
        scope = DocumentService._build_signed_download_scope(
            file_path="/files/doc.pdf", download_format="docx", expires=9999999999
        )
        assert "/files/doc.pdf|docx|9999999999" in scope

    def test_normalizes_format(self):
        from app.services.document_service import DocumentService
        scope = DocumentService._build_signed_download_scope(
            file_path="/f.pdf", download_format="  PDF  ", expires=1000
        )
        assert "|pdf|" in scope


class TestGenerateSignedDownloadUrl:
    def test_generates_url(self):
        from app.services.document_service import DocumentService
        result = DocumentService.generate_signed_download_url(
            file_url="https://storage.com/file.pdf",
            file_path="/files/file.pdf",
            secret="my-secret",
            expires_in_seconds=3600,
        )
        assert "url" in result
        assert "expires" in result
        assert result["url"].startswith("https://storage.com/file.pdf?")
        assert "token=" in result["url"]
        assert "expires=" in result["url"]

    def test_empty_secret_raises(self):
        from app.services.document_service import DocumentService
        with pytest.raises(ValueError, match="SIGNED_URL_SECRET"):
            DocumentService.generate_signed_download_url(
                file_url="https://s.com/f.pdf", file_path="/f.pdf", secret=""
            )


class TestVerifySignedDownload:
    def test_verify_valid(self):
        from app.services.document_service import DocumentService
        result = DocumentService.generate_signed_download_url(
            file_url="https://s.com/f.pdf", file_path="/f.pdf", secret="s", expires_in_seconds=3600
        )
        token = result["url"].split("token=")[1].split("&")[0]
        expires = result["url"].split("expires=")[1]
        assert DocumentService.verify_signed_download(
            file_path="/f.pdf", token=token, expires=expires, secret="s"
        ) is True

    def test_expired_returns_false(self):
        from app.services.document_service import DocumentService
        assert DocumentService.verify_signed_download(
            file_path="/f.pdf", token="t", expires=1, secret="s"
        ) is False

    def test_empty_params_returns_false(self):
        from app.services.document_service import DocumentService
        assert DocumentService.verify_signed_download(
            file_path="/f.pdf", token="", expires="1000", secret=""
        ) is False

    def test_invalid_expires_returns_false(self):
        from app.services.document_service import DocumentService
        assert DocumentService.verify_signed_download(
            file_path="/f.pdf", token="t", expires="bad", secret="s"
        ) is False


class TestExecuteWithTransientRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        from app.services.document_service import DocumentService
        op = MagicMock(return_value="ok")
        result = await DocumentService._execute_with_transient_retry("test", op)
        assert result == "ok"
        op.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        from app.services.document_service import DocumentService
        call_count = [0]
        def op():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Server disconnected")
            return "ok"

        with patch.object(DocumentService, "_is_transient_supabase_error", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
                with patch("asyncio.sleep", AsyncMock()):
                    result = await DocumentService._execute_with_transient_retry("test", op, max_attempts=3)
        assert result == "ok"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_raises_on_non_transient_error(self):
        from app.services.document_service import DocumentService
        op = MagicMock(side_effect=ValueError("permanent"))
        with pytest.raises(ValueError):
            await DocumentService._execute_with_transient_retry("test", op)
        op.assert_called_once()


class TestGetDocument:
    @pytest.mark.asyncio
    async def test_returns_data(self, ds):
        mock_client = MagicMock()
        mock_query = MagicMock()
        mock_query.maybe_single.return_value.execute.return_value = MagicMock(data={"id": "doc-1"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_query
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.get_document("550e8400-e29b-41d4-a716-446655440000")
        assert result == {"id": "doc-1"}

    @pytest.mark.asyncio
    async def test_non_uuid_returns_none(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            result = await ds.get_document("bad-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception):
                await ds.get_document("550e8400-e29b-41d4-a716-446655440000")


class TestListDocuments:
    @pytest.mark.asyncio
    async def test_returns_data(self, ds):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = [{"id": "doc-1"}]
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()
        mock_range.execute.return_value = mock_exec
        mock_order.range.return_value = mock_range
        mock_eq.order.return_value = mock_order
        mock_select.eq.return_value = mock_eq
        mock_table.select.return_value = mock_select
        mock_client.table.return_value = mock_table
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.list_documents("user-1")
        assert result == [{"id": "doc-1"}]

    @pytest.mark.asyncio
    async def test_with_status_filter(self, ds):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = []
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()
        mock_eq_after_range = MagicMock()
        mock_eq_after_range.execute.return_value = mock_exec
        mock_range.eq.return_value = mock_eq_after_range
        mock_order.range.return_value = mock_range
        mock_eq.order.return_value = mock_order
        mock_select.eq.return_value = mock_eq
        mock_table.select.return_value = mock_select
        mock_client.table.return_value = mock_table
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.list_documents("user-1", status="processing")
        assert result == []


class TestCreateDocument:
    @pytest.mark.asyncio
    async def test_creates_document(self, ds):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "doc-1"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            ds._supports_file_hash = True
            result = await ds.create_document("doc-1", "user-1", "test.pdf", "ieee")
        assert result == {"id": "doc-1"}


@pytest.fixture
def ds():
    from app.services.document_service import DocumentService
    ds = DocumentService()
    ds._supports_file_hash = None
    ds._file_hash_warning_logged = False
    ds._supports_output_hash = None
    ds._output_hash_warning_logged = False
    return ds


class TestCountDocuments:
    @pytest.fixture(autouse=True)
    def _reset_class_state(self):
        from app.services.document_service import DocumentService
        DocumentService._supports_output_hash = None
        DocumentService._supports_file_hash = None

    @pytest.mark.asyncio
    async def test_returns_count(self, ds):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.count = 5
        table = MagicMock()
        sel = MagicMock()
        sel.eq.return_value = MagicMock(execute=MagicMock(return_value=mock_exec))
        table.select.return_value = sel
        mock_client.table.return_value = table
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.count_documents("user-1")
        assert result == 5

    @pytest.mark.asyncio
    async def test_with_filters(self, ds):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.count = 3
        chain = MagicMock()
        chain.execute.return_value = mock_exec
        chain.eq.return_value = chain
        sel = MagicMock()
        sel.eq.return_value = chain
        table = MagicMock()
        table.select.return_value = sel
        mock_client.table.return_value = table
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.count_documents("user-1", status="completed", template="ieee")
        assert result == 3

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception):
                await ds.count_documents("user-1")

    @pytest.mark.asyncio
    async def test_api_error_raises(self, ds):
        mock_client = MagicMock()
        err = type("E", (Exception,), {})({"message": "fail"})
        chain = MagicMock()
        chain.execute.side_effect = err
        mock_client.table.return_value.select.return_value.eq.return_value = chain
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(Exception):
                await ds.count_documents("user-1")


class TestCountUploadsToday:
    @pytest.mark.asyncio
    async def test_returns_count(self, ds):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.count = 2
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lt.return_value.execute.return_value = mock_exec
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.count_uploads_today("user-1")
        assert result == 2

    @pytest.mark.asyncio
    async def test_zero_when_none(self, ds):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lt.return_value.execute.return_value = MagicMock(count=0)
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.count_uploads_today("user-1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception):
                await ds.count_uploads_today("user-1")


class TestUpdateDocument:
    @pytest.mark.asyncio
    async def test_updates_and_returns(self, ds):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "doc-1", "status": "COMPLETED"}]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.update_document("doc-1", {"status": "COMPLETED"})
        assert result == {"id": "doc-1", "status": "COMPLETED"}

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception):
                await ds.update_document("doc-1", {})

    @pytest.mark.asyncio
    async def test_api_error_raises(self, ds):
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = type("APIError", (Exception,), {})({"message": "fail"})
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(Exception):
                await ds.update_document("doc-1", {})


class TestDeleteDocument:
    @pytest.mark.asyncio
    async def test_deletes_successfully(self, ds):
        from app.services.document_service import DocumentService
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = [{"id": "doc-1"}]

        chain = MagicMock()
        chain.execute.return_value = mock_exec
        mock_client.table.return_value.delete.return_value.eq.return_value = chain

        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            with patch.object(DocumentService, "get_document", return_value={"id": "doc-1", "output_path": None}):
                result = await ds.delete_document("doc-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_doc_not_found_raises(self, ds):
        from app.services.document_service import DocumentService
        with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
            with patch.object(DocumentService, "get_document", return_value=None):
                with pytest.raises(Exception):
                    await ds.delete_document("nonexistent")

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception):
                await ds.delete_document("doc-1")


class TestUpdateOutputHash:
    @pytest.fixture(autouse=True)
    def _reset_class_state(self):
        from app.services.document_service import DocumentService
        DocumentService._supports_output_hash = None
        DocumentService._supports_file_hash = None

    @pytest.mark.asyncio
    async def test_empty_hash_returns_false(self, ds):
        result = await ds.update_output_hash("doc-1", "")
        assert result is False

    @pytest.mark.asyncio
    async def test_supports_false_returns_false(self, ds):
        ds._supports_output_hash = False
        result = await ds.update_output_hash("doc-1", "abc123")
        assert result is False

    @pytest.mark.asyncio
    async def test_supabase_none_returns_false(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            result = await ds.update_output_hash("doc-1", "abc123")
        assert result is False

    @pytest.mark.asyncio
    async def test_success_returns_true(self, ds):
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.update_output_hash("doc-1", "abc123")
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_column_handled(self, ds):
        from app.services.document_service import DocumentService
        mock_client = MagicMock()
        err = type("E", (Exception,), {})('column "output_hash" does not exist (PGRST204)')
        mock_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = err
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.update_output_hash("doc-1", "abc123")
        assert result is False
        assert DocumentService._supports_output_hash is False


class TestExecuteWithTransientRetryExtended:
    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        from app.services.document_service import DocumentService
        call_count = [0]
        def op():
            call_count[0] += 1
            raise ConnectionError("Server disconnected")
        with patch.object(DocumentService, "_is_transient_supabase_error", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=MagicMock()):
                with patch("asyncio.sleep", AsyncMock()):
                    with pytest.raises(ConnectionError):
                        await DocumentService._execute_with_transient_retry("test", op, max_attempts=3)
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_refreshes_client_on_retry(self):
        from app.services.document_service import DocumentService
        call_count = [0]
        client_mock = MagicMock()
        def op():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Server disconnected")
            return "ok"
        with patch.object(DocumentService, "_is_transient_supabase_error", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=client_mock):
                with patch("asyncio.sleep", AsyncMock()):
                    result = await DocumentService._execute_with_transient_retry("test", op, max_attempts=3)
        assert result == "ok"
        assert call_count[0] == 2


class TestGetDocument:
    @pytest.mark.asyncio
    async def test_returns_document(self, ds):
        from app.services.document_service import DocumentService
        mock_client = MagicMock()
        doc_data = {"id": "doc-1", "filename": "test.pdf"}
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=doc_data)
        chain.maybe_single.return_value = chain
        chain.eq.return_value = chain
        mock_client.table.return_value.select.return_value = chain
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
                result = await ds.get_document("doc-1")
        assert result == doc_data

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, ds):
        from app.services.document_service import DocumentService
        mock_client = MagicMock()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=None)
        chain.maybe_single.return_value = chain
        chain.eq.return_value = chain
        mock_client.table.return_value.select.return_value = chain
        with patch.object(DocumentService, "_should_query_document_tables", return_value=True):
            with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
                result = await ds.get_document("doc-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_should_query_returns_none(self, ds):
        from app.services.document_service import DocumentService
        with patch.object(DocumentService, "_should_query_document_tables", return_value=False):
            result = await ds.get_document("doc-1")
        assert result is None


class TestListDocuments:
    @pytest.mark.asyncio
    async def test_returns_list(self, ds):
        mock_client = MagicMock()
        docs = [{"id": "doc-1"}, {"id": "doc-2"}]
        mock_result = MagicMock()
        mock_result.data = docs

        range_mock = MagicMock()
        range_mock.execute.return_value = mock_result

        order_mock = MagicMock()
        order_mock.range.return_value = range_mock

        eq_mock = MagicMock()
        eq_mock.order.return_value = order_mock
        eq_mock.eq.return_value = eq_mock

        sel = MagicMock()
        sel.eq.return_value = eq_mock

        tbl = MagicMock()
        tbl.select.return_value = sel
        mock_client.table.return_value = tbl

        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.list_documents("user-1")
        assert result == docs

    @pytest.mark.asyncio
    async def test_with_filters(self, ds):
        mock_client = MagicMock()
        docs = [{"id": "doc-1"}]
        mock_result = MagicMock()
        mock_result.data = docs

        range_mock = MagicMock()
        range_mock.execute.return_value = mock_result
        range_mock.eq.return_value = range_mock

        order_mock = MagicMock()
        order_mock.range.return_value = range_mock

        eq_mock = MagicMock()
        eq_mock.order.return_value = order_mock
        eq_mock.eq.return_value = eq_mock

        sel = MagicMock()
        sel.eq.return_value = eq_mock

        tbl = MagicMock()
        tbl.select.return_value = sel
        mock_client.table.return_value = tbl

        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.list_documents("user-1", status="completed", template="ieee")
        assert result == docs

    @pytest.mark.asyncio
    async def test_empty_list(self, ds):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []

        range_mock = MagicMock()
        range_mock.execute.return_value = mock_result

        order_mock = MagicMock()
        order_mock.range.return_value = range_mock

        eq_mock = MagicMock()
        eq_mock.order.return_value = order_mock
        eq_mock.eq.return_value = eq_mock

        sel = MagicMock()
        sel.eq.return_value = eq_mock

        tbl = MagicMock()
        tbl.select.return_value = sel
        mock_client.table.return_value = tbl

        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.list_documents("user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_none_data_returns_empty(self, ds):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None

        range_mock = MagicMock()
        range_mock.execute.return_value = mock_result

        order_mock = MagicMock()
        order_mock.range.return_value = range_mock

        eq_mock = MagicMock()
        eq_mock.order.return_value = order_mock
        eq_mock.eq.return_value = eq_mock

        sel = MagicMock()
        sel.eq.return_value = eq_mock

        tbl = MagicMock()
        tbl.select.return_value = sel
        mock_client.table.return_value = tbl

        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.list_documents("user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception):
                await ds.list_documents("user-1")


class TestMarkDocumentFailed:
    @pytest.mark.asyncio
    async def test_marks_failed(self, ds):
        mock_client = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = MagicMock(execute=MagicMock())
        chain.update.return_value = chain
        mock_client.table.return_value = chain
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.mark_document_failed("doc-1", "error reason")
        assert result is None

    @pytest.mark.asyncio
    async def test_supabase_none_logs_error(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with patch("app.services.document_service.logger") as mock_logger:
                result = await ds.mark_document_failed("doc-1", "error reason")
        assert result is None
        mock_logger.error.assert_called_once()


class TestMarkDocumentCompleted:
    @pytest.mark.asyncio
    async def test_marks_completed(self, ds):
        mock_client = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = MagicMock(execute=MagicMock())
        chain.update.return_value = chain
        mock_client.table.return_value = chain
        with patch("app.services.document_service.get_supabase_client", return_value=mock_client):
            result = await ds.mark_document_completed("doc-1", "/tmp/output.pdf")
        assert result is None

    @pytest.mark.asyncio
    async def test_supabase_none_logs_error(self, ds):
        with patch("app.services.document_service.get_supabase_client", return_value=None):
            with patch("app.services.document_service.logger") as mock_logger:
                result = await ds.mark_document_completed("doc-1", "/tmp/output.pdf")
        assert result is None
        mock_logger.error.assert_called_once()
