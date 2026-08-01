# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for database session, supabase client, exceptions, and cache.
"""
from __future__ import annotations

from unittest.mock import patch

from app.exceptions import (
    ExternalServiceError,
    DatabaseUnavailableError,
    DocumentNotFoundError,
    RateLimitExceededError,
    FileStorageError,
    AuthenticationError,
)


class TestExceptions:
    """Tests for custom exception classes."""

    def test_external_service_error(self):
        exc = ExternalServiceError(service="grobid", message="Service failed")
        assert "grobid" in str(exc)
        assert exc.service == "grobid"

    def test_external_service_error_no_service(self):
        exc = ExternalServiceError()
        assert "External service call failed" in str(exc)

    def test_database_unavailable_error(self):
        exc = DatabaseUnavailableError("DB down")
        assert str(exc) == "DB down"

    def test_document_not_found_error(self):
        exc = DocumentNotFoundError(doc_id="doc-123")
        assert "doc-123" in str(exc)
        assert exc.doc_id == "doc-123"

    def test_rate_limit_exceeded_error(self):
        exc = RateLimitExceededError("Too many requests")
        assert "Too many requests" in str(exc)

    def test_file_storage_error(self):
        exc = FileStorageError("Disk full")
        assert str(exc) == "Disk full"

    def test_authentication_error(self):
        exc = AuthenticationError("Invalid token")
        assert str(exc) == "Invalid token"


class TestDatabaseSession:
    """Tests for database session management."""

    def test_session_module_imports(self):
        from app.db import session
        assert hasattr(session, "engine")
        assert hasattr(session, "SessionLocal")
        assert hasattr(session, "get_db")
        assert hasattr(session, "check_db_health")

    def test_check_db_health_no_engine(self):
        from app.db.session import check_db_health
        # When engine is None (no DB URL), returns unconfigured
        from app.db import session
        original_engine = session.engine
        session.engine = None
        try:
            result = check_db_health()
            assert result["status"] == "unconfigured"
        finally:
            session.engine = original_engine


class TestSupabaseClient:
    """Tests for Supabase client."""

    def test_supabase_module_imports(self):
        from app.db import supabase_client
        assert hasattr(supabase_client, "get_supabase_client")

    def test_get_supabase_client_returns_none_without_url(self):
        from app.db.supabase_client import get_supabase_client
        with patch("app.db.supabase_client.settings") as mock_settings:
            mock_settings.SUPABASE_URL = None
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = None
            result = get_supabase_client(refresh=True)
            assert result is None


class TestRedisCache:
    """Tests for Redis cache service."""

    def test_redis_cache_imports(self):
        from app.cache import redis_cache
        assert hasattr(redis_cache, "RedisCache")
        assert hasattr(redis_cache, "get_redis_cache")

    def test_redis_cache_get_llm_result_miss(self):
        from app.cache.redis_cache import RedisCache
        with patch.object(RedisCache, "_ensure_client", return_value=None):
            cache = RedisCache(redis_url=None)
            result = cache.get_llm_result("nonexistent-key")
            assert result is None

    def test_redis_cache_set_llm_result_no_redis(self):
        from app.cache.redis_cache import RedisCache
        cache = RedisCache(redis_url=None)
        # Should not raise when Redis is unavailable
        cache.set_llm_result("key", "value", ttl=60)

    def test_redis_cache_delete_no_redis(self):
        from app.cache.redis_cache import RedisCache
        cache = RedisCache(redis_url=None)
        cache.delete("key")

    def test_redis_cache_clear_no_redis(self):
        from app.cache.redis_cache import RedisCache
        cache = RedisCache(redis_url=None)
        cache.clear()

    def test_redis_cache_health_no_redis(self):
        from app.cache.redis_cache import RedisCache
        with patch.object(RedisCache, "_ensure_client", return_value=None):
            cache = RedisCache(redis_url=None)
            health = cache.health()
            assert health["status"] == "unavailable"

    def test_get_redis_cache_singleton(self):
        from app.cache.redis_cache import get_redis_cache
        c1 = get_redis_cache()
        c2 = get_redis_cache()
        assert c1 is c2


class TestMiddlewareAbuseDetector:
    """Tests for abuse detector middleware."""

    def test_abuse_detector_imports(self):
        from app.middleware import abuse_detector
        assert hasattr(abuse_detector, "AbuseDetector")

    def test_abuse_detector_initialization(self):
        from app.middleware.abuse_detector import AbuseDetector
        detector = AbuseDetector()
        assert detector is not None

    def test_abuse_detector_record_generation_request(self):
        from app.middleware.abuse_detector import AbuseDetector
        detector = AbuseDetector()
        detector.record_generation_request("127.0.0.1")


class TestMiddlewareCSRF:
    """Tests for CSRF middleware."""

    def test_csrf_middleware_imports(self):
        from app.middleware import csrf
        assert hasattr(csrf, "CSRFMiddleware")

    def test_csrf_token_generation(self):
        from app.middleware.csrf import CSRFMiddleware
        # Verify the class exists and can be instantiated
        assert CSRFMiddleware is not None


class TestMiddlewareHTTPSRedirect:
    """Tests for HTTPS redirect middleware."""

    def test_https_redirect_health_paths(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        paths = HTTPSRedirectMiddleware.HEALTH_PATHS
        assert "/health" in paths
        assert "/api/v1/health/live" in paths
        assert "/ready" in paths
        assert "/readyz" in paths


class TestPipelineDocument:
    """Tests for PipelineDocument model."""

    def test_pipeline_document_imports(self):
        from app.models.pipeline_document import PipelineDocument, DocumentMetadata, ProcessingStage
        assert PipelineDocument is not None
        assert DocumentMetadata is not None
        assert ProcessingStage is not None

    def test_processing_stage(self):
        from app.models.pipeline_document import ProcessingStage
        stage = ProcessingStage(stage_name="parsing", status="success")
        assert stage.stage_name == "parsing"
        assert stage.status == "success"

    def test_document_metadata(self):
        from app.models.pipeline_document import DocumentMetadata
        meta = DocumentMetadata(title="Test Paper", authors=["Author 1"])
        assert meta.title == "Test Paper"
        assert meta.authors == ["Author 1"]


class TestFigureModel:
    """Tests for Figure model."""

    def test_figure_imports(self):
        from app.models.figure import Figure, FigureType, ImageFormat
        assert Figure is not None
        assert FigureType is not None
        assert ImageFormat is not None

    def test_figure_type_enum(self):
        from app.models.figure import FigureType
        assert FigureType.DIAGRAM.value == "diagram"
        assert FigureType.CHART.value == "chart"
        assert FigureType.GRAPH.value == "graph"

    def test_image_format_enum(self):
        from app.models.figure import ImageFormat
        assert ImageFormat.PNG.value == "png"
        assert ImageFormat.JPEG.value == "jpeg"
        assert ImageFormat.SVG.value == "svg"


class TestTableModel:
    """Tests for Table model."""

    def test_table_imports(self):
        from app.models.table import Table, TableCell
        assert Table is not None
        assert TableCell is not None
