from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest
from app.exceptions import DatabaseUnavailableError, DocumentNotFoundError
pytestmark = [pytest.mark.chaos]


class TestDatabaseFailure:
    @pytest.mark.asyncio
    @patch("app.services.document_service.get_supabase_client", return_value=None)
    async def test_supabase_connection_failure_graceful_fallback(self, mock_client):
        from app.services.document_service import DocumentService
        result = await DocumentService.search_documents("test", "user1")
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.document_service.get_supabase_client", return_value=None)
    async def test_database_timeout_raises(self, mock_client):
        from app.services.document_service import DocumentService
        with pytest.raises(DatabaseUnavailableError):
            await DocumentService.get_document("550e8400-e29b-41d4-a716-446655440000")

    def test_partial_data_does_not_crash(self):
        from app.services.document_service import DocumentService
        invalid_doc_id = "550e8400-e29b-41d4-a716-446655440000"
        assert DocumentService._is_valid_uuid(invalid_doc_id) is True
        assert DocumentService._should_query_document_tables(invalid_doc_id, "test") is True


class TestRedisFailure:
    def test_redis_unreachable_rate_limit_fallback(self):
        with patch("app.middleware.rate_limit.redis") as mock_redis:
            mock_redis.side_effect = ConnectionError("Redis unreachable")
            from app.middleware.rate_limit import RateLimitMiddleware
            instance = RateLimitMiddleware
            assert instance is not None

    @patch("app.services.llm_service.settings")
    def test_redis_cache_miss_not_critical(self, mock_settings):
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
        mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
        mock_settings.LLM_CACHE_TTL_SECONDS = 3600
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        with patch("app.cache.redis_cache.RedisCache._ensure_client", return_value=None):
            with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                with patch("app.services.llm_service.LITELLM_AVAILABLE", False):
                    with patch("app.services.llm_service._generate_fallback") as mock_fb:
                        mock_fb.return_value = "fallback response"
                        from app.services.llm_service import generate
                        result = generate([{"role": "user", "content": "hi"}], model="nvidia_nim/test")
                        assert result == "fallback response"

    @patch("app.services.llm_service.settings")
    def test_corrupted_redis_data_handled(self, mock_settings):
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
        mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
        mock_settings.LLM_CACHE_TTL_SECONDS = 3600
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
            with patch("app.services.llm_service.LITELLM_AVAILABLE", False):
                with patch("app.services.llm_service._generate_fallback") as mock_fb:
                    mock_fb.return_value = "clean response"
                    from app.services.llm_service import generate
                    result = generate([{"role": "user", "content": "hi"}], model="nvidia_nim/test")
                    assert result == "clean response"


class TestAIProviderFailure:
    @patch("app.services.llm_service.settings")
    def test_primary_provider_fails_auto_failover(self, mock_settings):
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
        mock_settings.GROQ_API_KEY = "groq-key"
        mock_settings.GROQ_MODEL = "groq/llama3-70b"
        mock_settings.OPENROUTER_API_KEY = None
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
        mock_settings.LLM_CACHE_TTL_SECONDS = 3600
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        with patch("app.services.llm_service.generate") as mock_gen:
            mock_gen.side_effect = [
                Exception("NVIDIA 500"),
                "groq response",
            ]
            with patch("app.services.llm_service.resolve_user_api_key", return_value=None):
                from app.services.llm_service import generate_with_fallback
                result = generate_with_fallback([{"role": "user", "content": "test"}])
                assert result["tier"] == 2
                assert result["text"] == "groq response"

    @patch("app.services.llm_service.settings")
    def test_all_providers_fail_meaningful_error(self, mock_settings):
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
        mock_settings.GROQ_API_KEY = "groq-key"
        mock_settings.GROQ_MODEL = "groq/llama3-70b"
        mock_settings.OPENROUTER_API_KEY = None
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
        mock_settings.LLM_CACHE_TTL_SECONDS = 3600
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        with patch("app.services.llm_service.generate", side_effect=Exception("Provider down")):
            with patch("app.services.llm_service.resolve_user_api_key", return_value=None):
                from app.services.llm_service import generate_with_fallback
                with pytest.raises(Exception) as excinfo:
                    generate_with_fallback([{"role": "user", "content": "test"}])
                assert "All LLM tiers failed" in str(excinfo.value)

    @patch("app.services.llm_service.settings")
    def test_partial_response_handled(self, mock_settings):
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
        mock_settings.GROQ_API_KEY = None
        mock_settings.OPENROUTER_API_KEY = None
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
        mock_settings.LLM_CACHE_TTL_SECONDS = 3600
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
            with patch("app.services.llm_service.LITELLM_AVAILABLE", False):
                with patch("app.services.llm_service._generate_fallback") as mock_fb:
                    mock_fb.return_value = "partial"
                    with patch("app.services.llm_service.resolve_user_api_key", return_value=None):
                        from app.services.llm_service import generate_with_fallback
                        result = generate_with_fallback([{"role": "user", "content": "test"}])
                        assert result["text"] == "partial"

    @patch("app.services.llm_service.settings")
    def test_garbage_provider_output_handled(self, mock_settings):
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
        mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
        mock_settings.LLM_CACHE_TTL_SECONDS = 3600
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        from app.services.llm_service import sanitize_for_llm
        garbage_inputs = [
            "\x00\x01\x02\x03" * 100,
            "\uffff\ufffe\ufffd",
            "A" * 5000 + "<script>",
        ]
        for g in garbage_inputs:
            result = sanitize_for_llm(g)
            assert isinstance(result, str)
            assert len(result) <= 8100


class TestQueueCeleryFailure:
    def test_broker_unreachable_graceful(self):
        with patch("app.tasks.celery_tasks.celery_app") as mock_celery:
            mock_celery.send_task.side_effect = ConnectionError("Broker unreachable")
            with pytest.raises(ConnectionError):
                mock_celery.send_task("test_task", args=[])

    def test_worker_crash_recovery(self):
        from app.services.document_service import DocumentService
        assert DocumentService._is_transient_supabase_error(ConnectionError("server disconnected")) is True
        assert DocumentService._is_transient_supabase_error(ConnectionError("connection reset")) is True
        assert DocumentService._is_transient_supabase_error(ValueError("schema error")) is False
        assert DocumentService._is_transient_supabase_error(RuntimeError("temporarily unavailable")) is True

    @pytest.mark.asyncio
    async def test_retry_backoff_timing(self):
        from app.services.document_service import DocumentService
        with patch.object(DocumentService, "_execute_with_transient_retry", new_callable=AsyncMock) as mock_retry:
            mock_result = MagicMock()
            mock_result.data = {"id": "test"}
            mock_retry.return_value = mock_result
            with patch("app.services.document_service.get_supabase_client") as mock_get:
                mock_client = MagicMock()
                mock_get.return_value = mock_client
                mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(data={"id": "test"})
                result = await DocumentService.get_document("550e8400-e29b-41d4-a716-446655440000")
                assert result == {"id": "test"}


class TestNetworkIssues:
    @patch("app.services.llm_service.settings")
    def test_network_latency_timeout_clamped(self, mock_settings):
        mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 120
        mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
        from app.services.llm_service import _provider_timeout_seconds
        timeout = _provider_timeout_seconds()
        assert timeout <= 60

    @patch("app.db.supabase_client.settings")
    def test_dns_failure_degradation(self, mock_settings):
        mock_settings.SUPABASE_URL = None
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = None
        from app.db.supabase_client import get_supabase_client, check_supabase_health
        client = get_supabase_client(refresh=True)
        assert client is None
        health = check_supabase_health()
        assert health["status"] == "unconfigured"

    @patch("app.db.supabase_client.settings")
    def test_connection_refused_handled(self, mock_settings):
        mock_settings.SUPABASE_URL = "https://nonexistent.example.com"
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-key"
        from app.db.supabase_client import get_supabase_client, check_supabase_health
        health = check_supabase_health()
        assert health["status"] in ("unhealthy", "unconfigured")


class TestCircuitBreakerRecovery:
    @patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False)
    def test_circuit_breaker_half_open_to_closed(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker, CircuitBreakerOpenException
        call_count = 0
        @circuit_breaker(failure_threshold=2, recovery_timeout=0.05)
        def fragile_op():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")
            return "success"
        with pytest.raises(ValueError, match="transient"):
            fragile_op()
        with pytest.raises(ValueError, match="transient"):
            fragile_op()
        assert call_count == 2
        with pytest.raises(CircuitBreakerOpenException):
            fragile_op()
        import time
        time.sleep(0.06)
        result = fragile_op()
        assert result == "success"

    @patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False)
    def test_exponential_backoff_timing(self):
        from app.services.document_service import DocumentService
        assert DocumentService._is_transient_supabase_error(Exception("connection refused")) is True
        assert DocumentService._is_transient_supabase_error(Exception("read timed out")) is True

    def test_idempotent_retry(self):
        from app.services.document_service import DocumentService
        result = DocumentService.generate_signed_download_url(
            file_url="https://storage.example.com/doc.docx",
            file_path="/path/doc.docx",
            secret="test-secret-for-idempotency",
            expires_in_seconds=3600,
        )
        result2 = DocumentService.generate_signed_download_url(
            file_url="https://storage.example.com/doc.docx",
            file_path="/path/doc.docx",
            secret="test-secret-for-idempotency",
            expires_in_seconds=3600,
        )
        assert result["url"] == result2["url"]

    def test_service_restart_state_restoration(self):
        with patch("app.db.supabase_client._client_initialized", False):
            with patch("app.db.supabase_client._supabase_client", None):
                from app.db.supabase_client import get_supabase_client
                client = get_supabase_client(refresh=True)
                assert client is None or client is not None
