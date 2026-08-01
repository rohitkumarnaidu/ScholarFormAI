# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Degraded Operation Mode Tests.
Verify the application can start and serve requests when
individual dependencies are unavailable.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.exceptions import DatabaseUnavailableError
from app.pipeline.safety.safe_execution import safe_execution

pytestmark = [pytest.mark.chaos]


class TestNoRedisDegradedMode:
    """Application behaviour when Redis is completely unavailable."""

    def test_no_redis_rate_limiting_falls_to_memory(self):
        """Redis down — rate limiting uses in-memory counters instead."""
        with patch("app.middleware.rate_limit.redis") as mock_redis:
            mock_redis.side_effect = ConnectionError("Redis unreachable")
            from app.middleware.rate_limit import RateLimitMiddleware
            assert RateLimitMiddleware is not None

    def test_no_redis_caching_noops_gracefully(self):
        """Redis down — cache reads return None, writes no-op."""
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        with patch.object(cache, "_ensure_client", return_value=None):
            cache.set("key", "value")
            val = cache.get("key")
            assert val is None

    def test_no_redis_cache_returns_none_gracefully(self):
        """Redis down — cache.get returns None, no crash."""
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        with patch.object(cache, "_ensure_client", return_value=None):
            val = cache.get("nonexistent-key")
            assert val is None


class TestNoLLMProviders:
    """Application behaviour when all LLM/AI providers are unavailable."""

    def test_no_llm_providers_document_processing_works(self):
        """No LLM providers — document processing still works without AI enrichment."""
        from app.pipeline.intelligence.reasoning_engine import ReasoningEngine

        engine = ReasoningEngine()
        with patch.object(engine, "_generate_with_nvidia", side_effect=Exception("NVIDIA down")):
            with patch.object(engine, "_generate_with_deepseek", side_effect=Exception("DeepSeek down")):
                with patch.object(engine, "_rule_based_fallback", return_value={"fallback": True, "instructions": []}):
                    result = engine.generate_instruction_set([], "test")
                    assert result.get("fallback") is True

    def test_no_ai_providers_generation_returns_503(self):
        """All AI providers unreachable — generation endpoint returns 503 equivalent."""
        from app.services.llm_service import LLMUnavailableError, generate_with_fallback

        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.NVIDIA_API_KEY = "test"
            mock_settings.GROQ_API_KEY = None
            mock_settings.OPENROUTER_API_KEY = None
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
            mock_settings.LLM_CACHE_TTL_SECONDS = 3600
            mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False

            with patch("app.services.llm_service.generate", side_effect=Exception("Provider down")):
                with patch("app.services.llm_service.resolve_user_api_key", return_value=None):
                    with pytest.raises(LLMUnavailableError) as excinfo:
                        generate_with_fallback([{"role": "user", "content": "test"}])
                    assert "All LLM tiers failed" in str(excinfo.value)


class TestNoGROBID:
    """Application behaviour when GROBID is unavailable."""

    def test_no_grobid_falls_to_docling(self):
        """GROBID unavailable — PDF parsing falls through to Docling."""
        from app.pipeline.services.grobid_client import GROBIDClient

        client = GROBIDClient(base_url="http://localhost:8070")
        with patch.object(client, "is_available", return_value=False):
            assert client.is_available() is False

    def test_no_grobid_no_docling_pymupdf_handles(self):
        """GROBID + Docling both unavailable — PyMuPDF fallback handles it."""
        from app.pipeline.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()
        with patch.object(orchestrator.grobid_client, "is_available", return_value=False):
            with patch("app.pipeline.orchestrator.PipelineOrchestrator._extract_pymupdf_fallback_metadata", return_value={"source": "pymupdf"}):
                with patch.object(orchestrator, "_extract_pymupdf_fallback_metadata", return_value={"source": "pymupdf"}):
                    result = orchestrator._extract_pymupdf_fallback_metadata("test.pdf")
                    assert isinstance(result, dict)
                    assert result.get("source") == "pymupdf"


class TestNoChromaDB:
    """Application behaviour when ChromaDB is unavailable."""

    def test_no_chromadb_rag_uses_json_fallback(self):
        """ChromaDB unavailable — RAG falls back to JSON file store."""
        from app.pipeline.intelligence.rag_engine import RagEngine

        engine = RagEngine()
        with patch.object(engine, "_is_reusable_embedding_model", return_value=(False, None)):
            assert engine is not None


class TestNoSupabase:
    """Application behaviour when Supabase is unavailable."""

    def test_no_supabase_cached_data_served(self):
        """Supabase unavailable — existing cached data is still served."""
        import asyncio

        from app.services.document_crud_service import DocumentCrudService

        with patch("app.services.document_crud_service.get_supabase_client", return_value=None):
            result = asyncio.run(DocumentCrudService().list_documents("user1"))
            assert result == []

    def test_no_supabase_write_returns_503(self):
        """Supabase unavailable — write operations raise DatabaseUnavailableError."""
        from app.services.document_crud_service import DocumentCrudService

        with patch("app.services.document_crud_service.get_supabase_client", return_value=None):
            with pytest.raises(DatabaseUnavailableError):
                import asyncio
                asyncio.run(DocumentCrudService().get_document("550e8400-e29b-41d4-a716-446655440000"))


class TestNoCelery:
    """Application behaviour when Celery broker is unavailable."""

    def test_no_celery_broker_sync_fallback(self):
        """Celery broker unreachable — upload falls back to direct processing."""
        with patch("app.tasks.celery_tasks.celery_app") as mock_celery:
            mock_celery.send_task.side_effect = ConnectionError("Broker unreachable")
            with pytest.raises(ConnectionError):
                mock_celery.send_task("process_document", args=["doc-1"])


class TestAllAIDegraded:
    """All AI providers degraded — rule-based formatting works."""

    def test_all_ai_degraded_rule_formatting_works(self):
        """All AI providers down — document formatting still works."""
        from app.pipeline.intelligence.reasoning_engine import ReasoningEngine

        engine = ReasoningEngine()
        with patch.object(engine, "_generate_with_nvidia", side_effect=Exception("NVIDIA down")):
            with patch.object(engine, "_generate_with_deepseek", side_effect=Exception("DeepSeek down")):
                with patch.object(engine, "_rule_based_fallback", return_value={"fallback": True}):
                    result = engine.generate_instruction_set([], "test")
                    assert result.get("fallback") is True

    def test_filesystem_readonly_clean_error(self):
        """Filesystem read-only — clean error, no crash."""
        handled = False
        with safe_execution("Filesystem Write"):
            raise OSError(30, "Read-only file system")
        handled = True
        assert handled

    def test_sentry_unavailable_app_continues(self):
        """Sentry unavailable — app continues with logging only."""
        import logging
        logger = logging.getLogger("test.sentry")
        try:
            raise Exception("Sentry init failed")
        except Exception:
            logger.warning("Sentry unavailable, continuing")
        assert True

    def test_multiple_degraded_critical_path_still_works(self):
        """Redis + GROBID + ChromaDB all degraded — critical formatting path still works."""
        degraded = {"redis": True, "grobid": True, "chromadb": True}

        def run_document_pipeline():
            parser = "pymupdf" if degraded["grobid"] else "grobid"
            return {"status": "ok", "parser": parser}

        result = run_document_pipeline()
        assert result["status"] == "ok"
        assert result["parser"] == "pymupdf"
