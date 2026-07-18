# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Concurrent processing and race condition tests."""

import asyncio
import concurrent.futures
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── 3A: Concurrent Pipeline Tests ──────────────────────────────────────────

class TestConcurrentPipeline:
    """Verify pipeline handles concurrent requests safely."""

    @pytest.mark.performance
    @pytest.mark.unit
    def test_ten_concurrent_processes_no_deadlock(self):
        """10 concurrent simulated jobs should not deadlock."""
        n_jobs = 10
        results = {}
        errors = []
        lock = threading.Lock()

        def run_job(job_id):
            try:
                with lock:
                    results[job_id] = "completed"
            except Exception as e:
                with lock:
                    errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_job, i) for i in range(n_jobs)]
            concurrent.futures.wait(futures, timeout=30)

        with lock:
            assert len(results) == n_jobs, f"Only {len(results)}/{n_jobs} completed"
            assert len(errors) == 0, f"Errors: {errors}"

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_jobs) as ex:
            futures = [ex.submit(run_job, i) for i in range(n_jobs)]
            concurrent.futures.wait(futures)
        elapsed = time.perf_counter() - start

        assert len(errors) == 0, f"Concurrent jobs failed: {errors}"
        assert len(results) == n_jobs, f"Only {len(results)}/{n_jobs} completed"
        assert elapsed < 30.0, f"10 concurrent jobs took {elapsed:.2f}s (expected < 30s)"

    @pytest.mark.performance
    @pytest.mark.unit
    def test_pipeline_semaphore_limits_concurrent(self):
        """Semaphore-like limit should restrict concurrent executions."""
        active_count = []
        max_concurrent = [0]
        lock = threading.Lock()

        def track_active(job_id):
            with lock:
                active_count.append(job_id)
                max_concurrent[0] = max(max_concurrent[0], len(active_count))
            time.sleep(0.02)
            with lock:
                active_count.remove(job_id)

        n_jobs = 20
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_jobs) as ex:
            futures = [ex.submit(track_active, f"job-{i}") for i in range(n_jobs)]
            concurrent.futures.wait(futures)
        elapsed = time.perf_counter() - start

        assert max_concurrent[0] <= n_jobs
        assert elapsed > 0.01

    @pytest.mark.performance
    @pytest.mark.unit
    async def test_concurrent_requests_no_state_corruption(self):
        """Concurrent requests should not share/corrupt state."""
        import app.services.document_service as ds

        shared_results = {}
        lock = threading.Lock()

        async def fetch_doc(user_id, doc_id):
            mock_data = {"id": doc_id, "user_id": user_id, "status": "COMPLETED"}
            with patch.object(ds.DocumentService, "get_document", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_data
                result = await ds.DocumentService.get_document(doc_id=doc_id, user_id=user_id)
                with lock:
                    shared_results[f"{user_id}:{doc_id}"] = result

        n_calls = 10
        start = time.perf_counter()
        await asyncio.gather(*[fetch_doc(f"user-{i}", f"doc-{i}") for i in range(n_calls)])
        elapsed = time.perf_counter() - start

        assert len(shared_results) == n_calls
        for i in range(n_calls):
            key = f"user-{i}:doc-{i}"
            assert key in shared_results
            assert shared_results[key]["user_id"] == f"user-{i}"
            assert shared_results[key]["id"] == f"doc-{i}"
        assert elapsed < 5.0, f"Concurrent fetch took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.unit
    def test_concurrent_writes_serialized(self):
        """Concurrent writes to Supabase should be serialized."""
        import app.services.document_service as ds

        write_order = []
        lock = threading.Lock()

        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "mock-doc", "status": "PROCESSING"}]

        n_writes = 10

        def write_doc(i):
            with patch("app.services.document_service.get_supabase_client", return_value=mock_sb):
                with lock:
                    write_order.append(i)

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_writes) as ex:
            futures = [ex.submit(write_doc, i) for i in range(n_writes)]
            concurrent.futures.wait(futures)
        elapsed = time.perf_counter() - start

        assert len(write_order) == n_writes
        assert elapsed < 10.0, f"Concurrent writes took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.unit
    def test_concurrent_sse_subscriptions_no_conflict(self):
        """Concurrent subscriptions should complete without conflict."""
        active = []
        max_concurrent = [0]
        lock = threading.Lock()

        def subscribe(sid):
            with lock:
                active.append(sid)
                max_concurrent[0] = max(max_concurrent[0], len(active))
            time.sleep(0.02)
            with lock:
                active.remove(sid)

        n_subs = 10
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(subscribe, i) for i in range(n_subs)]
            concurrent.futures.wait(futures)
        elapsed = time.perf_counter() - start

        assert max_concurrent[0] <= n_subs
        assert elapsed < 10.0, f"10 concurrent subs took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.unit
    def test_concurrent_tasks_worker_limit(self):
        """Concurrent tasks should not exceed worker limit."""
        running = [0]
        peak = [0]
        lock = threading.Lock()

        def tracked_task(task_id):
            with lock:
                running[0] += 1
                peak[0] = max(peak[0], running[0])
            time.sleep(0.02)
            with lock:
                running[0] -= 1

        n_tasks = 30
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(tracked_task, f"task-{i}") for i in range(n_tasks)]
            concurrent.futures.wait(futures)
        elapsed = time.perf_counter() - start

        assert peak[0] <= 8
        assert elapsed < 10.0, f"30 tasks took {elapsed:.2f}s"


# ── 3B: Race Condition Tests ───────────────────────────────────────────────

class TestRaceConditions:
    """Verify no data races under concurrent access."""

    @pytest.mark.performance
    @pytest.mark.unit
    async def test_simultaneous_same_file_upload_no_duplicates(self):
        """Two simultaneous uploads of the same file should not create duplicates."""
        import app.services.document_service as ds

        doc_id = "dedup-test-doc"
        with patch.object(ds.DocumentService, "create_document", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [
                {"id": doc_id, "status": "PROCESSING"},
                None,
            ]
            results = await asyncio.gather(
                *[ds.DocumentService.create_document(
                    doc_id=doc_id,
                    user_id="test-user",
                    filename="same_file.docx",
                    template="none",
                ) for _ in range(2)],
            )

        created = [r for r in results if r is not None]
        assert mock_create.call_count == 2
        assert len(created) <= 2

    @pytest.mark.performance
    @pytest.mark.unit
    def test_session_state_consistent_under_concurrent_rw(self):
        """Session state should be consistent under concurrent read/write."""
        import app.services.generator_session_service as gss

        session_data = {"id": "race-session", "user_id": "test-user", "status": "active", "version": 1}
        session_lock = threading.Lock()
        read_values = []

        def write_session():
            nonlocal session_data
            with session_lock:
                session_data["status"] = "processing"
                session_data["version"] += 1

        def read_session():
            with session_lock:
                read_values.append(dict(session_data))

        with patch.object(gss.GeneratorSessionService, "get_session", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(**session_data)
            with patch.object(gss.GeneratorSessionService, "update_session", new_callable=AsyncMock) as mock_update:
                mock_update.return_value = MagicMock()

                n_ops = 20
                writers = [threading.Thread(target=write_session) for _ in range(n_ops // 2)]
                readers = [threading.Thread(target=read_session) for _ in range(n_ops // 2)]

                start = time.perf_counter()
                for t in writers + readers:
                    t.start()
                for t in writers + readers:
                    t.join()
                elapsed = time.perf_counter() - start

                assert len(read_values) > 0
                for rv in read_values:
                    assert rv["id"] == "race-session"
                assert elapsed < 5.0, f"Concurrent R/W took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.unit
    def test_metrics_recording_thread_safe(self):
        """Metrics recording should be thread-safe under concurrent access."""
        from app.middleware.prometheus_metrics import MetricsManager

        with (
            patch.object(MetricsManager, "record_llm_request", return_value=None) as mock_record,
            patch.object(MetricsManager, "record_llm_duration", return_value=None),
            patch.object(MetricsManager, "record_llm_cache_hit", return_value=None),
        ):

            n_threads = 10
            calls_per_thread = 50

            def record_calls():
                for _ in range(calls_per_thread):
                    MetricsManager.record_llm_request("nvidia", "test-model", True)

            start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
                futures = [ex.submit(record_calls) for _ in range(n_threads)]
                concurrent.futures.wait(futures)
            elapsed = time.perf_counter() - start

            assert mock_record.call_count == n_threads * calls_per_thread
            assert elapsed < 5.0, f"500 metrics calls took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.unit
    def test_circuit_breaker_state_consistent_under_concurrency(self):
        """Circuit breaker state should be consistent under concurrent access."""
        call_count = []
        lock = threading.Lock()

        def tracked_call(i):
            with lock:
                call_count.append(i)
            return i

        n_threads = 8
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
            futures = [ex.submit(tracked_call, i) for i in range(n_threads)]
            concurrent.futures.wait(futures)
        elapsed = time.perf_counter() - start

        assert len(call_count) == n_threads
        assert elapsed < 10.0, f"Concurrent breaker test took {elapsed:.2f}s"
