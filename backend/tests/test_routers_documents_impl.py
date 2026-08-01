import pytest
import hashlib
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, UploadFile



# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_cache():
    from app.routers.v1.documents_impl import _reset_document_status_cache_for_tests
    _reset_document_status_cache_for_tests()


# ── Helpers ───────────────────────────────────────────────────────────────────

class TestStatusCacheKey:
    def test_with_user(self):
        from app.routers.v1.documents_impl import _status_cache_key
        user = MagicMock(id="user-123")
        assert _status_cache_key("job-456", user) == "user-123|job-456"

    def test_with_none_user(self):
        from app.routers.v1.documents_impl import _status_cache_key
        assert _status_cache_key("job-456", None) == "__anon__|job-456"

    def test_user_no_id(self):
        from app.routers.v1.documents_impl import _status_cache_key
        user = MagicMock(spec=[])  # no id attr
        result = _status_cache_key("job-456", user)
        assert "__anon__" in result


class TestCloneStatusPayload:
    def test_deep_copy(self):
        from app.routers.v1.documents_impl import _clone_status_payload
        payload = {"a": {"b": [1, 2]}}
        cloned = _clone_status_payload(payload)
        assert cloned == payload
        assert cloned["a"] is not payload["a"]


class TestDocumentStatusTTL:
    def test_default(self):
        with patch("app.routers.v1.documents_impl.settings") as mock_s:
            del mock_s.DOCUMENT_STATUS_CACHE_TTL_SECONDS
            from app.routers.v1.documents_impl import _document_status_ttl_seconds
            assert _document_status_ttl_seconds() == 1.0

    def test_custom(self):
        with patch("app.routers.v1.documents_impl.settings") as mock_s:
            mock_s.DOCUMENT_STATUS_CACHE_TTL_SECONDS = 30
            from app.routers.v1.documents_impl import _document_status_ttl_seconds
            assert _document_status_ttl_seconds() == 30.0

    def test_invalid_literal(self):
        with patch("app.routers.v1.documents_impl.settings") as mock_s:
            mock_s.DOCUMENT_STATUS_CACHE_TTL_SECONDS = "abc"
            from app.routers.v1.documents_impl import _document_status_ttl_seconds
            assert _document_status_ttl_seconds() == 1.0

    def test_negative_clamped(self):
        with patch("app.routers.v1.documents_impl.settings") as mock_s:
            mock_s.DOCUMENT_STATUS_CACHE_TTL_SECONDS = -5
            from app.routers.v1.documents_impl import _document_status_ttl_seconds
            assert _document_status_ttl_seconds() == 0.0


class TestCacheHelpers:
    @pytest.mark.asyncio
    async def test_get_cached_ttl_zero(self):
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=0):
            from app.routers.v1.documents_impl import _get_cached_status_response, _STATUS_CACHE_MISS
            assert await _get_cached_status_response("key") is _STATUS_CACHE_MISS

    @pytest.mark.asyncio
    async def test_get_cached_miss(self):
        from app.routers.v1.documents_impl import _get_cached_status_response, _STATUS_CACHE_MISS
        assert await _get_cached_status_response("nonexistent") is _STATUS_CACHE_MISS

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        from app.routers.v1.documents_impl import _set_cached_status_response, _get_cached_status_response
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=30):
            payload = {"status": "PROCESSING"}
            await _set_cached_status_response("key1", payload)
            cached = await _get_cached_status_response("key1")
        assert cached == payload
        assert cached is not payload

    @pytest.mark.asyncio
    async def test_set_ttl_zero_evicts(self):
        from app.routers.v1.documents_impl import _set_cached_status_response, _get_cached_status_response, _STATUS_CACHE_MISS
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=30):
            await _set_cached_status_response("key2", {"status": "OK"})
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=0):
            await _set_cached_status_response("key2", {"status": "OK"})
            assert await _get_cached_status_response("key2") is _STATUS_CACHE_MISS

    @pytest.mark.asyncio
    async def test_stale_returns_within_max_stale(self):
        from app.routers.v1.documents_impl import _set_cached_status_response, _get_stale_status_response, _STATUS_CACHE_MISS
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=1):
            await _set_cached_status_response("key3", {"status": "OK"})
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=1):
            stale = await _get_stale_status_response("key3", max_stale_seconds=999)
        assert stale != _STATUS_CACHE_MISS

    @pytest.mark.asyncio
    async def test_stale_past_max_stale_evicts(self):
        from app.routers.v1.documents_impl import _set_cached_status_response, _get_stale_status_response, _STATUS_CACHE_MISS
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=1):
            await _set_cached_status_response("key4", {"status": "OLD"})
        with patch("app.routers.v1.documents_impl._document_status_ttl_seconds", return_value=0):
            assert await _get_stale_status_response("key4", max_stale_seconds=0) is _STATUS_CACHE_MISS


class TestRequireDB:
    def test_require_db_configured(self):
        with patch("app.db.supabase_client.get_supabase_client", return_value=MagicMock()):
            from app.routers.v1.documents_impl import _require_db
            _require_db()

    def test_require_db_not_configured(self):
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            from app.routers.v1.documents_impl import _require_db
            with pytest.raises(HTTPException) as exc:
                _require_db()
            assert exc.value.status_code == 503


class TestComputeSHA256:
    def test_compute_sha256(self, tmp_path):
        from app.routers.v1.documents_impl import _compute_sha256
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert _compute_sha256(str(f)) == expected

    def test_compute_sha256_no_file(self):
        from app.routers.v1.documents_impl import _compute_sha256
        with pytest.raises(FileNotFoundError):
            _compute_sha256("nonexistent")


class TestNormalizeProviderName:
    def test_none(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name(None) is None
        assert _normalize_provider_name("") is None

    def test_nvidia(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("nvidia_nim/test") == "nvidia"

    def test_groq(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("groq/llama") == "groq"

    def test_ollama(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("ollama/deepseek") == "ollama"
        assert _normalize_provider_name("deepseek-r1") == "ollama"

    def test_openai(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("gpt-4") == "openai"
        assert _normalize_provider_name("openai/gpt4") == "openai"

    def test_anthropic(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("claude-3") == "anthropic"
        assert _normalize_provider_name("anthropic/claude") == "anthropic"

    def test_rule_based(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("rule_based") == "rule_based"

    def test_unknown(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("custom") == "custom"


class TestExtractQualityPayload:
    def test_no_validation_results(self):
        from app.routers.v1.documents_impl import _extract_quality_payload
        result = _extract_quality_payload(None)
        assert result["quality_score"] is None
        assert result["quality"] is None

    def test_full_quality_data(self):
        from app.routers.v1.documents_impl import _extract_quality_payload
        result_in = {
            "validation_results": {
                "quality_score": 85.0,
                "quality_summary": {
                    "overall_score": 85.0,
                    "template_compliance": 90.0,
                    "content_quality": 80.0,
                    "citation_count": 25,
                    "missing_sections": ["acknowledgments"],
                    "llm_provider_used": "nvidia_nim/test",
                },
            }
        }
        result = _extract_quality_payload(result_in)
        assert result["quality_score"] == 85.0
        assert result["quality"]["overall_score"] == 85.0
        assert result["quality"]["llm_provider_used"] == "nvidia"

    def test_ai_semantic_audit_fallback(self):
        from app.routers.v1.documents_impl import _extract_quality_payload
        result_in = {
            "validation_results": {
                "ai_semantic_audit": {"llm_provider": "groq/mixtral"},
            }
        }
        result = _extract_quality_payload(result_in)
        assert result["quality"]["llm_provider_used"] == "groq"


class TestBuildInitialStatusPayload:
    def test_build(self):
        from app.routers.v1.documents_impl import _build_initial_status_payload
        payload = _build_initial_status_payload("job-1")
        assert payload["job_id"] == "job-1"
        assert payload["status"] == "PROCESSING"
        assert payload["progress_percentage"] == 0


class TestValidateMagicBytes:
    @pytest.mark.asyncio
    async def test_valid_docx(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        content = b"\x50\x4b\x03\x04" + b"\x00" * 20
        file = MagicMock(spec=UploadFile, filename="test.docx")
        result = await _validate_magic_bytes(file, content=content, file_ext=".docx")
        assert result == content

    @pytest.mark.asyncio
    async def test_invalid_extension(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        file = MagicMock(spec=UploadFile, filename="test.exe")
        with pytest.raises(HTTPException) as exc:
            await _validate_magic_bytes(file, content=b"data", file_ext=".exe")
        assert exc.value.status_code == 400
        assert "Invalid file type" in exc.value.detail

    @pytest.mark.asyncio
    async def test_invalid_utf8_text(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        file = MagicMock(spec=UploadFile, filename="test.txt")
        with pytest.raises(HTTPException) as exc:
            await _validate_magic_bytes(file, content=b"\xff\xfe", file_ext=".txt")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_spoofed_extension(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        file = MagicMock(spec=UploadFile, filename="fake.pdf")
        content = b"\x00\x00\x00\x00" + b"\x00" * 20
        with pytest.raises(HTTPException) as exc:
            await _validate_magic_bytes(file, content=content, file_ext=".pdf")
        assert exc.value.status_code == 400
        assert "spoofed" in exc.value.detail


class TestScanUploadedFile:
    @pytest.mark.asyncio
    async def test_clean_file(self):
        with patch("app.routers.v1.documents_impl.virus_scanner") as mock_scanner:
            mock_scanner.scan = AsyncMock(return_value={"clean": True})
            from app.routers.v1.documents_impl import _scan_uploaded_file
            result = await _scan_uploaded_file("/tmp/test.pdf")
            assert result["clean"] is True

    @pytest.mark.asyncio
    async def test_malware_detected(self):
        with patch("app.routers.v1.documents_impl.virus_scanner") as mock_scanner, \
             patch("app.routers.v1.documents_impl.os.remove"):
            mock_scanner.scan = AsyncMock(return_value={"clean": False, "result": "EICAR"})
            from app.routers.v1.documents_impl import _scan_uploaded_file
            with pytest.raises(HTTPException) as exc:
                await _scan_uploaded_file("/tmp/bad.pdf")
            assert exc.value.status_code == 422


# ── Main endpoints ────────────────────────────────────────────────────────────

class TestUploadDocument:
    @pytest.mark.asyncio
    async def test_upload_success(self):
        from app.routers.v1.documents_impl import upload_document
        content = b"\x50\x4b\x03\x04" + b"\x00" * 100
        file = MagicMock(spec=UploadFile, filename="paper.docx")
        file.read = AsyncMock(return_value=content)
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_user = MagicMock(id="user-1")

        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"), \
             patch("app.routers.v1.documents_impl._validate_magic_bytes", return_value=content), \
             patch("app.routers.v1.documents_impl._scan_uploaded_file", return_value={"clean": True}), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds, \
             patch("app.routers.v1.documents_impl.PipelineOrchestrator") as mock_po, \
             patch("app.routers.v1.documents_impl.enhancement_manager") as mock_em, \
             patch("app.routers.v1.documents_impl.audit_log_service") as mock_audit, \
             patch("app.routers.v1.documents_impl._set_cached_status_response"), \
             patch("app.routers.v1.documents_impl._record_upload_ack_duration"), \
             patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760), \
             patch("app.routers.v1.documents_impl.settings.DEFAULT_TEMPLATE", "ieee"), \
             patch("app.routers.v1.documents_impl.uuid.uuid4", return_value="job-abc"):

            mock_ds.create_document = AsyncMock(return_value={"id": "job-abc"})
            mock_em.dispatch_document_pipeline.return_value = {"mode": "background"}
            mock_audit.log = AsyncMock()

            result = await upload_document(
                request=mock_request,
                background_tasks=MagicMock(),
                file=file,
                template="ieee",
                add_page_numbers=True,
                add_borders=False,
                add_cover_page=False,
                generate_toc=False,
                add_line_numbers=False,
                line_spacing=None,
                page_size="Letter",
                fast_mode=False,
                current_user=mock_user,
            )
            assert result["job_id"] == "job-abc"
            assert result["status"] == "PROCESSING"
            mock_ds.create_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_db_unavailable(self):
        from app.routers.v1.documents_impl import upload_document
        content = b"\x50\x4b\x03\x04" + b"\x00" * 100
        file = MagicMock(spec=UploadFile, filename="paper.docx")
        file.read = AsyncMock(return_value=content)
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_user = MagicMock(id="user-1")

        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"), \
             patch("app.routers.v1.documents_impl._validate_magic_bytes", return_value=content), \
             patch("app.routers.v1.documents_impl._scan_uploaded_file", return_value={"clean": True}), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds, \
             patch("app.routers.v1.documents_impl._record_upload_ack_duration"), \
             patch("app.routers.v1.documents_impl.os.remove"), \
             patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760), \
             patch("app.routers.v1.documents_impl.settings.DEFAULT_TEMPLATE", "ieee"), \
             patch("app.routers.v1.documents_impl.uuid.uuid4", return_value="job-abc"):

            mock_ds.create_document = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc:
                await upload_document(
                    request=mock_request,
                    background_tasks=MagicMock(),
                    file=file,
                    template="ieee",
                    current_user=mock_user,
                )
            assert exc.value.status_code == 503

    @pytest.mark.asyncio
    async def test_upload_anonymous(self):
        from app.routers.v1.documents_impl import upload_document
        content = b"\x50\x4b\x03\x04" + b"\x00" * 100
        file = MagicMock(spec=UploadFile, filename="paper.docx")
        file.read = AsyncMock(return_value=content)
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"), \
             patch("app.routers.v1.documents_impl._validate_magic_bytes", return_value=content), \
             patch("app.routers.v1.documents_impl._scan_uploaded_file", return_value={"clean": True}), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds, \
             patch("app.routers.v1.documents_impl._record_upload_ack_duration"), \
             patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760), \
             patch("app.routers.v1.documents_impl.settings.DEFAULT_TEMPLATE", "ieee"), \
             patch("app.routers.v1.documents_impl.uuid.uuid4", return_value="job-abc"):

            mock_ds.create_document = AsyncMock(return_value={"id": "job-abc"})

            result = await upload_document(
                request=mock_request,
                background_tasks=MagicMock(),
                file=file,
                template="ieee",
                current_user=None,
            )
            assert result["job_id"] == "job-abc"


class TestListDocuments:
    @pytest.mark.asyncio
    async def test_anonymous_returns_empty(self):
        from app.routers.v1.documents_impl import list_documents
        with patch("app.routers.v1.documents_impl._require_db"):
            result = await list_documents(current_user=None)
        assert result["documents"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_with_user(self):
        from app.routers.v1.documents_impl import list_documents
        mock_user = MagicMock(id="user-1")
        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds:
            mock_ds.list_documents = AsyncMock(return_value=[{"id": "doc1", "filename": "test.docx"}])
            mock_ds.count_documents = AsyncMock(return_value=1)
            result = await list_documents(
                status="COMPLETED", template="ieee",
                limit=10, offset=0, current_user=mock_user,
            )
        assert len(result["documents"]) == 1
        assert result["total"] == 1


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_status_cached(self):
        from app.routers.v1.documents_impl import get_status
        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl._get_stale_status_response") as mock_stale:
            mock_stale.return_value = {"status": "PROCESSING"}
            result = await get_status(job_id="job-1", current_user=None)
        assert result["status"] == "PROCESSING"

    @pytest.mark.asyncio
    async def test_status_from_db(self):
        from app.routers.v1.documents_impl import get_status
        mock_user = MagicMock(id="user-1")
        mock_doc = {
            "status": "COMPLETED",
            "processing_status": {"progress_pct": 100},
            "result": {},
        }
        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl._get_stale_status_response", return_value=None), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds, \
             patch("app.routers.v1.documents_impl._set_cached_status_response"), \
             patch("app.routers.v1.documents_impl._extract_quality_payload", return_value={"quality_score": 90, "quality_summary": None, "quality": None}):
            mock_ds.get_document = AsyncMock(return_value=mock_doc)
            mock_ds.get_processing_statuses = AsyncMock(return_value=[])
            mock_ds.get_document_result = AsyncMock(return_value=None)
            result = await get_status(job_id="job-1", current_user=mock_user)
        assert result["status"] == "COMPLETED"


class TestGetDocumentSummary:
    @pytest.mark.asyncio
    async def test_summary_success(self):
        from app.routers.v1.documents_impl import get_document_summary
        mock_user = MagicMock(id="user-1")
        mock_doc = {
            "id": "doc-1",
            "filename": "paper.docx",
            "template": "ieee",
            "status": "COMPLETED",
        }
        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds:
            mock_ds.get_document = AsyncMock(return_value=mock_doc)
            mock_ds.get_document_result = AsyncMock(return_value=None)
            result = await get_document_summary(job_id="doc-1", current_user=mock_user)
        assert result["id"] == "doc-1"
        assert result["filename"] == "paper.docx"

    @pytest.mark.asyncio
    async def test_summary_not_found(self):
        from app.routers.v1.documents_impl import get_document_summary
        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds:
            mock_ds.get_document = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc:
                await get_document_summary(job_id="nonexistent", current_user=None)
            assert exc.value.status_code == 404


class TestDeleteDocument:
    @pytest.mark.asyncio
    async def test_delete_success(self):
        from app.routers.v1.documents_impl import delete_document
        mock_user = MagicMock(id="user-1")
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds, \
             patch("app.routers.v1.documents_impl.audit_log_service") as mock_audit, \
             patch("app.routers.v1.documents_impl.os.path.exists", return_value=True), \
             patch("app.routers.v1.documents_impl.os.remove"):

            mock_ds.get_document = AsyncMock(return_value={"id": "doc-1", "original_file_path": "/tmp/doc.pdf"})
            mock_ds.delete_document = AsyncMock(return_value=True)
            mock_audit.log = AsyncMock()

            result = await delete_document(request=mock_request, job_id="doc-1", current_user=mock_user)
        assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        from app.routers.v1.documents_impl import delete_document
        mock_user = MagicMock(id="user-1")
        mock_request = MagicMock()

        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds:
            mock_ds.get_document = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc:
                await delete_document(request=mock_request, job_id="nonexistent", current_user=mock_user)
            assert exc.value.status_code == 404


    @pytest.mark.asyncio
    async def test_status_not_found(self):
        from app.routers.v1.documents_impl import get_status, _STATUS_CACHE_MISS
        with patch("app.routers.v1.documents_impl._require_db"), \
             patch("app.routers.v1.documents_impl._get_stale_status_response", return_value=_STATUS_CACHE_MISS), \
             patch("app.routers.v1.documents_impl.DocumentService") as mock_ds:
            mock_ds.get_document = AsyncMock(return_value=None)
            mock_ds.get_processing_statuses = AsyncMock(return_value=[])
            with pytest.raises(HTTPException) as exc:
                await get_status(job_id="nonexistent", current_user=None)
            assert exc.value.status_code == 404
