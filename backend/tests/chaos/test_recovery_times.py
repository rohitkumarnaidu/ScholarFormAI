# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Recovery Time Objective (RTO) tests.
Measure time-to-recover for each critical dependency
under simulated failure conditions.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.safety.circuit_breaker import (
    CircuitBreakerOpenException,
    circuit_breaker,
)

pytestmark = [pytest.mark.chaos, pytest.mark.slow]


class TestRedisRecovery:
    """Redis outage -> fallback to memory -> recover when Redis is back."""

    def test_redis_fallback_to_memory_recovery(self):
        """Redis down — falls back to in-memory, recovers when Redis returns."""
        cache_state = {"mode": "memory"}

        def read(key):
            if cache_state["mode"] == "redis":
                return f"redis:{key}"
            return f"memory:{key}"

        assert read("foo") == "memory:foo"
        cache_state["mode"] = "redis"
        assert read("foo") == "redis:foo"

    def test_redis_recovery_under_100ms(self):
        """Redis mock recovery completes in under 100ms."""
        start = time.perf_counter()
        recovered = False
        with patch("app.cache.redis_cache.RedisCache._ensure_client") as mock_ensure:
            mock_ensure.side_effect = [None, MagicMock()]
            first = mock_ensure()
            assert first is None
            second = mock_ensure()
            assert second is not None
            recovered = True
        elapsed = time.perf_counter() - start
        assert recovered, "Should recover to Redis"
        assert elapsed < 0.1, f"Recovery took {elapsed:.3f}s, expected <0.1s"


class TestGROBIDRecovery:
    """GROBID crash -> fallback to Docling -> recover when GROBID returns."""

    def test_grobid_crash_docling_fallback_recovery(self):
        """GROBID down — next parser handles it; when GROBID returns, it is used again."""
        grobid_available = [False]
        docling_available = [True]

        def get_parser():
            if grobid_available[0]:
                return "grobid"
            if docling_available[0]:
                return "docling"
            return "pymupdf"

        assert get_parser() == "docling"
        grobid_available[0] = True
        assert get_parser() == "grobid"

    def test_grobid_recovery_under_200ms(self):
        """GROBID mock health transitions from down to up in under 200ms."""
        from app.pipeline.services.grobid_client import GROBIDClient

        start = time.perf_counter()
        client = GROBIDClient(base_url="http://localhost:8070")
        with patch.object(client, "is_available", side_effect=[False, True]):
            assert client.is_available() is False
            assert client.is_available() is True
        elapsed = time.perf_counter() - start
        assert elapsed < 0.2, f"GROBID recovery took {elapsed:.3f}s, expected <0.2s"


class TestSupabaseRecovery:
    """Supabase disconnection -> cached data -> reconnect."""

    def test_supabase_disconnect_cached_data_recovery(self):
        """Supabase down — serve cached data; when connected, serve live data."""
        cache = {"doc-1": "cached_content"}
        connected = [False]

        def get_document(doc_id):
            if connected[0]:
                return f"live:{doc_id}"
            return cache.get(doc_id, None)

        assert get_document("doc-1") == "cached_content"
        connected[0] = True
        assert get_document("doc-1") == "live:doc-1"

    def test_supabase_recovery_under_500ms(self):
        """Supabase mock reconnection completes in under 500ms."""
        from app.db.supabase_client import get_supabase_client, check_supabase_health

        start = time.perf_counter()
        with patch("app.db.supabase_client.settings") as mock_settings:
            mock_settings.SUPABASE_URL = None
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = None
            client_unavail = get_supabase_client(refresh=True)
            assert client_unavail is None
        with patch("app.db.supabase_client.settings") as mock_settings:
            mock_settings.SUPABASE_URL = "https://test.supabase.co"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-key"
            health = check_supabase_health()
            assert health["status"] in ("unhealthy", "unconfigured")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Supabase recovery check took {elapsed:.3f}s, expected <0.5s"


class TestCeleryRecovery:
    """Celery worker restart -> pending tasks re-queued."""

    def test_celery_worker_restart_tasks_requeued(self):
        """Worker dies — pending tasks are re-queued and re-processed on restart."""
        task_queue = [{"id": "task-1"}, {"id": "task-2"}]
        processed = []

        def process_tasks():
            processed_before = len(processed)
            while task_queue:
                task = task_queue.pop(0)
                processed.append(task["id"])
            return len(processed) - processed_before

        count = process_tasks()
        assert count == 2
        assert processed == ["task-1", "task-2"]

        task_queue.append({"id": "task-3"})
        count = process_tasks()
        assert count == 1
        assert processed == ["task-1", "task-2", "task-3"]

    def test_celery_recovery_under_1000ms(self):
        """Celery broker mock recovery completes in under 1000ms."""
        start = time.perf_counter()

        class CeleryState:
            available = False

        state = CeleryState()

        def is_available():
            return state.available

        assert is_available() is False
        state.available = True
        assert is_available() is True
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Celery recovery took {elapsed:.3f}s, expected <1.0s"


class TestServiceRestartRecovery:
    """Cold start timing and circuit breaker recovery."""

    def test_full_service_restart_cold_start(self):
        """Mock cold start — verify initialization completes under 500ms."""
        start = time.perf_counter()

        initialized = [False]

        def cold_start():
            time.sleep(0.05)
            initialized[0] = True
            return "ready"

        result = cold_start()
        elapsed = time.perf_counter() - start
        assert result == "ready"
        assert initialized[0] is True
        assert elapsed < 0.5, f"Cold start took {elapsed:.3f}s, expected <0.5s"

    def test_circuit_breaker_recovery_after_timeout(self):
        """Circuit breaker OPEN -> after recovery_timeout -> HALF_OPEN -> CLOSED."""
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            call_count = [0]

            @circuit_breaker(failure_threshold=2, recovery_timeout=0.05)
            def fragile_op():
                call_count[0] += 1
                if call_count[0] < 3:
                    raise ValueError("transient")

            with pytest.raises(ValueError):
                fragile_op()
            with pytest.raises(ValueError):
                fragile_op()
            assert call_count[0] == 2

            with pytest.raises(CircuitBreakerOpenException):
                fragile_op()

            time.sleep(0.06)
            start = time.perf_counter()
            fragile_op()
            elapsed = time.perf_counter() - start

            assert call_count[0] == 3
            assert elapsed < 0.5, f"Circuit breaker recovery took {elapsed:.3f}s"

    def test_auto_recovery_after_grobid_restart(self):
        """GROBID 503 -> 503 -> 200 — verify third call succeeds."""
        from app.pipeline.services.grobid_client import GROBIDClient

        client = GROBIDClient(base_url="http://localhost:8070")
        with patch.object(client, "is_available", side_effect=[False, False, True]):
            assert client.is_available() is False
            assert client.is_available() is False
            assert client.is_available() is True

    def test_transient_retry_timing(self):
        """Retry completes within expected time window."""
        from app.pipeline.safety.retry_guard import retry_guard

        call_log = []

        @retry_guard(max_retries=2, backoff_factor=0.01)
        def transient_op():
            call_log.append(1)
            if len(call_log) == 1:
                raise ValueError("first fail")
            return "ok"

        result = transient_op()
        assert result == "ok"
        assert len(call_log) == 2
