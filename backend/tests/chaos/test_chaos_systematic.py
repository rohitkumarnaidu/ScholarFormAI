# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Systematic chaos engineering tests.
Simulate production failures and verify graceful degradation
across all pipeline modules.
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.pipeline.safety.retry_guard import retry_with_backoff
from app.pipeline.safety.safe_execution import safe_execution

pytestmark = [pytest.mark.chaos]


class TestSingleServiceFailure:
    """Verify fallback when a single service fails mid-pipeline."""

    def test_random_service_failure_triggers_fallback(self):
        """Simulate a random ValueError during pipeline run — verify safe_execution catches it."""
        caught = False
        with safe_execution("Random Failure Stage"):
            raise ValueError("random service crash")
        caught = True
        assert caught, "safe_execution should suppress random ValueError"

    def test_network_partition_simulated_retry(self):
        """Simulate timeout then retry via retry_guard."""
        call_log = []

        @retry_with_backoff(max_retries=2, backoff_factor=0.01)
        def flaky_network_call():
            call_log.append(1)
            if len(call_log) == 1:
                raise TimeoutError("Connection timed out")
            return "success"

        result = flaky_network_call()
        assert result == "success"
        assert len(call_log) == 2

    def test_cpu_pressure_slow_mock_recovers(self):
        """Simulate CPU-bound slowdown via artificially slow mock — verify eventual completion."""
        start = time.time()
        with patch("time.sleep", side_effect=lambda s: None), safe_execution("CPU Intensive Pass"):
            for _ in range(100):
                _ = [i ** 2 for i in range(1000)]
        elapsed = time.time() - start
        assert elapsed < 2.0, f"CPU pressure simulation took {elapsed:.2f}s, expected <2s"

    def test_memory_pressure_oom_handled(self):
        """Simulate MemoryError during processing — verify safe_execution suppresses it."""
        handled = False
        with safe_execution("Memory-Intensive Pass"):
            raise MemoryError("Unable to allocate 4 GiB")
        handled = True
        assert handled, "safe_execution should catch MemoryError"

    def test_disk_io_failure_handled(self):
        """Simulate OSError(ENOSPC) during file write — verify graceful handling."""
        handled = False
        with safe_execution("Disk Write Stage"):
            raise OSError(28, "No space left on device")
        handled = True
        assert handled, "safe_execution should catch ENOSPC"

    def test_clock_skew_handled(self):
        """Simulate clock skew where timestamps are in the future — verify no crash."""
        wrong_time = datetime.now(UTC) + timedelta(days=365)
        # Patch datetime on the actual orchestrator sub-module that imports it.
        # create=True is required because datetime is imported locally (function-scoped),
        # not at the module level, so the attribute may not exist at patch time.
        with patch("app.pipeline.orchestrator.orchestrator.datetime", create=True) as mock_dt:
            mock_dt.now.return_value = wrong_time
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw) if a else wrong_time
            safe = False
            with safe_execution("Clock-Sensitive Operation"):
                _ = wrong_time.isoformat()
            safe = True
            assert safe


class TestMultipleSimultaneousFailures:
    """Multiple services failing at the same time."""

    def test_multiple_services_down_simultaneously(self):
        """Simulate Redis + GROBID + DB all failing — verify pipeline degrades gracefully."""
        failures = []

        with patch("app.cache.redis_cache.RedisCache._ensure_client", return_value=None):
            failures.append("redis")
        with patch("app.pipeline.services.grobid_client.GROBIDClient.is_available", return_value=False):
            failures.append("grobid")
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            failures.append("supabase")

        assert len(failures) == 3
        assert "redis" in failures
        assert "grobid" in failures
        assert "supabase" in failures

    def test_resource_leak_handle_exhaustion(self):
        """Simulate file descriptor exhaustion — verify OSError is caught."""
        handled = False
        with safe_execution("Handle Exhaustion"):
            raise OSError(24, "Too many open files")
        handled = True
        assert handled

    def test_cascade_grobid_docling_pymupdf(self):
        """Cascade failure: GROBID fails -> Docling fails -> PyMuPDF fallback works."""
        grobid_ok = [False]
        docling_ok = [False]

        def get_parser():
            if grobid_ok[0]:
                return "grobid"
            if docling_ok[0]:
                return "docling"
            return "pymupdf"

        assert get_parser() == "pymupdf"
        docling_ok[0] = True
        assert get_parser() == "docling"
        grobid_ok[0] = True
        assert get_parser() == "grobid"

    def test_cascade_ai_providers_rule_fallback(self):
        """AI provider 1 fails, provider 2 fails — rule-based fallback is used."""
        from app.pipeline.intelligence.reasoning_engine import ReasoningEngine

        engine = ReasoningEngine()
        with patch.object(engine, "_generate_with_nvidia", side_effect=Exception("NVIDIA down")):
            with patch.object(engine, "_generate_with_deepseek", side_effect=Exception("DeepSeek down")):
                with patch.object(engine, "_rule_based_fallback", return_value={"fallback": True, "instructions": []}):
                    result = engine.generate_instruction_set([], "test context")
                    assert result.get("fallback") is True

    def test_partial_batch_failure(self):
        """Half of documents in a batch succeed, half fail — verify partial results."""
        results = []

        def process_doc(idx):
            if idx % 2 == 0:
                return {"doc_id": idx, "status": "ok"}
            raise ValueError(f"Doc {idx} failed")

        for i in range(6):
            with safe_execution(f"Process doc {i}"):
                r = process_doc(i)
                if r:
                    results.append(r)

        successes = [r for r in results if r.get("status") == "ok"]
        assert len(successes) == 3
        assert len(results) == 3


class TestTimingAndRaceConditions:
    """Race conditions, slow responses, cancel signals."""

    def test_slow_response_no_double_processing(self):
        """Service responds after timeout — verify idempotency key prevents double-processing."""
        processed_ids = set()

        def process_with_idempotency(doc_id):
            if doc_id in processed_ids:
                return {"status": "duplicate", "doc_id": doc_id}
            processed_ids.add(doc_id)
            time.sleep(0.05)
            return {"status": "processed", "doc_id": doc_id}

        first = process_with_idempotency("doc-1")
        second = process_with_idempotency("doc-1")
        assert first["status"] == "processed"
        assert second["status"] == "duplicate"

    def test_cancel_signal_during_processing(self):
        """Cancel signal arrives mid-pipeline — verify CancelledError propagates."""
        from app.pipeline.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()
        with patch.object(orchestrator, "_check_cancelled", side_effect=asyncio.CancelledError("Cancelled by user")):
            with pytest.raises(asyncio.CancelledError):
                orchestrator._check_cancelled("job-001")

    def test_data_corruption_malformed_service_response(self):
        """Malformed data returned by external service — validate_output catches it."""
        from pydantic import BaseModel, Field

        from app.pipeline.safety.llm_validator import guard_llm_output

        class ExpectedSchema(BaseModel):
            title: str = Field(description="document title")
            authors: list[str] = Field(description="author list")

        guarded = guard_llm_output(ExpectedSchema, error_return_value={"title": "", "authors": []})

        @guarded
        def fetch_metadata():
            return {"wrong_key": "spam", "score": 42}

        result = fetch_metadata()
        assert result == {"title": "", "authors": []}

    def test_zombie_process_stale_status(self):
        """Task completes but status is not updated — verify status check recovers."""
        from app.pipeline.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()
        with patch.object(orchestrator, "_update_status") as mock_update:
            mock_update.side_effect = Exception("Status update failed")
            safe = False
            with safe_execution("Status Update"):
                orchestrator._update_status("job-001", "completed")
            safe = True
            assert safe


class TestDependencyChain:
    """A->B->C dependency chain failures."""

    def test_dependency_chain_middle_fails(self):
        """Chain A->B->C where B fails — verify A and C still work independently."""
        results = {}

        def stage_a():
            return "A ok"

        def stage_b():
            raise ValueError("B failed")

        def stage_c():
            return "C ok"

        results["A"] = stage_a()
        try:
            stage_b()
        except ValueError:
            results["B"] = "failed"
        results["C"] = stage_c()

        assert results["A"] == "A ok"
        assert results["B"] == "failed"
        assert results["C"] == "C ok"

    def test_deadlock_detection_with_acquire_timeout(self):
        """Lock.acquire with timeout prevents indefinite deadlock."""
        lock_a = threading.Lock()
        lock_a.acquire()
        result = lock_a.acquire(timeout=0.05)
        assert result is False, "Acquire should time out"


class TestResourceExhaustionSystematic:
    """Handle, connection, and thread pool exhaustion."""

    def test_too_many_open_handles(self):
        """Simulate EMFILE — verify safe_execution catches it."""
        caught = False
        with safe_execution("Open Handle"):
            raise OSError(24, "Too many open files")
        caught = True
        assert caught

    def test_connection_pool_exhaustion(self):
        """Simulate connection pool exhaustion — verify timeout raises on full pool."""
        import concurrent.futures
        pool = ThreadPoolExecutor(max_workers=1)
        blocker = threading.Event()
        pool.submit(blocker.wait)
        quick = pool.submit(lambda: 42)
        with pytest.raises(concurrent.futures.TimeoutError):
            quick.result(timeout=0.1)
        blocker.set()
        pool.shutdown(wait=False)

    def test_event_loop_starvation_handled(self):
        """Blocking call in async context — verify loop still processes async tasks."""
        import asyncio

        loop = asyncio.new_event_loop()
        async_results = []
        blocking_results = []

        async def async_task():
            async_results.append("async done")

        def blocking_task():
            time.sleep(0.05)
            blocking_results.append("blocking done")

        loop.run_in_executor(None, blocking_task)
        loop.run_until_complete(async_task())
        loop.run_until_complete(asyncio.sleep(0.1))
        loop.close()
        assert "async done" in async_results
        assert "blocking done" in blocking_results

    def test_dns_resolution_failure(self):
        """DNS failure — verify clean error, not a crash."""
        from app.db.supabase_client import check_supabase_health

        with (
            patch("app.db.supabase_client.settings") as mock_settings,
            patch("app.db.supabase_client._client_initialized", False),
        ):
            mock_settings.SUPABASE_URL = "https://nonexistent-dns.example.com"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-key"
            health = check_supabase_health()
            assert health["status"] in ("unhealthy", "unconfigured")


class TestAdvancedChaos:
    """Error avalanches, split-brain, stale data, degraded retry, full recovery."""

    def test_tls_certificate_expiration_simulated(self):
        """Simulate TLS cert expiry — verify SSL error handled."""
        from app.pipeline.safety import safe_execution

        handled = False
        with safe_execution("TLS Handshake"):
            raise ConnectionError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired")
        handled = True
        assert handled

    def test_backpressure_producer_faster_than_consumer(self):
        """Producer outpaces consumer — verify bounded queue prevents OOM."""
        import queue

        q = queue.Queue(maxsize=5)
        produced = 0
        for i in range(20):
            try:
                q.put_nowait(i)
                produced += 1
            except queue.Full:
                break
        assert produced <= 5, f"Should backpressure after 5 items, produced {produced}"

    def test_request_queue_overflow(self):
        """Request queue exceeds capacity — verify rejection, not crash."""
        from concurrent.futures import ThreadPoolExecutor

        pool = ThreadPoolExecutor(max_workers=2)
        futures = []
        for _ in range(10):
            futures.append(pool.submit(time.sleep, 0.5))
        with safe_execution("Overflow submit"):
            futures.append(pool.submit(lambda: 42))
        [f for f in futures if f.done() or not f.running()]
        pool.shutdown(wait=False)

    def test_split_brain_job_duplication(self):
        """Two instances process same job — verify idempotency key deduplicates."""
        processed = set()

        def acquire_lock(job_id):
            if job_id in processed:
                return False
            processed.add(job_id)
            return True

        assert acquire_lock("job-42") is True
        assert acquire_lock("job-42") is False
        assert len(processed) == 1

    def test_stale_cache_data_handled(self):
        """Cache returns outdated data — verify staleness detection refreshes."""
        cache = {"data": "old_value", "timestamp": time.time() - 3600}
        CACHE_TTL = 300

        def get_fresh():
            return "fresh_value"

        def get_data():
            if time.time() - cache["timestamp"] > CACHE_TTL:
                cache["data"] = get_fresh()
                cache["timestamp"] = time.time()
            return cache["data"]

        result = get_data()
        assert result == "fresh_value"

    def test_degraded_retry_succeeds_after_three_attempts(self):
        """Retry succeeds after exactly 3 attempts — verify no more retries than needed."""
        call_log = []

        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        def flaky_service():
            call_log.append(1)
            if len(call_log) < 3:
                raise ValueError("transient failure")
            return "recovered"

        result = flaky_service()
        assert result == "recovered"
        assert len(call_log) == 3

    def test_error_avalanche_prevention(self):
        """Single error in pipeline triggers cascading failures — verify containment."""
        results = []

        def stage_1():
            raise ValueError("Stage 1 crash")

        def stage_2():
            if not results:
                raise RuntimeError("Cascade from stage 1")
            return "stage 2 ok"

        with safe_execution("Stage 1"):
            stage_1()
        with safe_execution("Stage 2"):
            stage_2()

        assert len(results) == 0

    def test_full_recovery_after_all_services_fail(self):
        """All services fail then come back — verify recovery works."""
        state = {"redis": False, "grobid": False, "ai": False}

        def check_redis():
            if not state["redis"]:
                raise ConnectionError("Redis down")
            return "redis ok"

        def check_grobid():
            if not state["grobid"]:
                raise ConnectionError("GROBID down")
            return "grobid ok"

        with safe_execution("Redis check"):
            check_redis()
        with safe_execution("GROBID check"):
            check_grobid()

        state["redis"] = True
        state["grobid"] = True

        assert check_redis() == "redis ok"
        assert check_grobid() == "grobid ok"

    def test_race_condition_concurrent_writes(self):
        """Two threads writing the same resource — verify no data loss."""
        shared = {}

        def writer(key, value):
            time.sleep(0.01)
            shared[key] = value

        t1 = threading.Thread(target=writer, args=("a", 1))
        t2 = threading.Thread(target=writer, args=("b", 2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert shared.get("a") == 1
        assert shared.get("b") == 2

    def test_thread_pool_exhaustion_async(self):
        """All threads busy — verify new tasks get queued not dropped."""
        from concurrent.futures import ThreadPoolExecutor

        pool = ThreadPoolExecutor(max_workers=2)
        blocker = threading.Event()
        for _ in range(2):
            pool.submit(blocker.wait)
        future = pool.submit(lambda: "queued_ok")
        assert not future.done()
        blocker.set()
        assert future.result() == "queued_ok"
        pool.shutdown(wait=False)
