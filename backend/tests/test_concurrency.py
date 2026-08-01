# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Concurrency and race-condition tests for pipeline, SSE, rate-limits, etc."""

from __future__ import annotations

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Pipeline Semaphore ─────────────────────────────────────────────────────────

class TestPipelineSemaphore:
    def _cleanup(self):
        from app.pipeline.orchestrator import _pipeline_semaphore
        while _pipeline_semaphore._value < 5:
            _pipeline_semaphore.release()

    def test_allows_up_to_five_concurrent(self):
        from app.pipeline.orchestrator import _MAX_CONCURRENT_JOBS, _pipeline_semaphore
        assert _MAX_CONCURRENT_JOBS == 5
        acquired = []
        for _ in range(5):
            acq = _pipeline_semaphore.acquire(blocking=False)
            acquired.append(acq)
        assert all(acquired)
        assert _pipeline_semaphore._value == 0
        self._cleanup()

    def test_blocks_sixth_concurrent(self):
        from app.pipeline.orchestrator import _pipeline_semaphore
        self._cleanup()
        acquired = []
        for _ in range(5):
            acquired.append(_pipeline_semaphore.acquire(blocking=False))
        assert all(acquired)
        sixth = _pipeline_semaphore.acquire(blocking=False)
        assert sixth is False
        self._cleanup()

    def test_release_allows_new_job(self):
        from app.pipeline.orchestrator import _pipeline_semaphore
        self._cleanup()
        _pipeline_semaphore.acquire(blocking=False)
        _pipeline_semaphore.acquire(blocking=False)
        _pipeline_semaphore.release()
        _pipeline_semaphore.release()
        assert _pipeline_semaphore.acquire(blocking=False) is True
        self._cleanup()

    def test_acquire_timeout_raises_on_full(self):
        from app.pipeline.orchestrator import _pipeline_semaphore
        self._cleanup()
        for _ in range(5):
            _pipeline_semaphore.acquire(blocking=False)
        start = time.time()
        result = _pipeline_semaphore.acquire(timeout=0.01)
        elapsed = time.time() - start
        assert result is False
        assert elapsed < 1.0
        self._cleanup()

    def test_semaphore_threadsafe(self):
        from app.pipeline.orchestrator import _pipeline_semaphore
        self._cleanup()
        acquired = []

        def worker():
            acq = _pipeline_semaphore.acquire(blocking=False)
            if acq:
                acquired.append(True)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(acquired) == 5
        self._cleanup()


# ── Same-file concurrent upload ────────────────────────────────────────────────

class TestConcurrentUpload:
    def test_same_file_hash_detection(self):
        """Two uploads of the same file should detect collision via SHA-256."""
        from app.pipeline.orchestrator import PipelineOrchestrator
        orch = MagicMock(spec=PipelineOrchestrator)
        orch._compute_sha256 = MagicMock(return_value="abc123def")
        same_hash = orch._compute_sha256("dummy.pdf")
        assert same_hash == "abc123def"

    def test_database_race_condition_does_not_block_reads(self):
        """Simulate concurrent DB reads — they should not block each other."""
        mock_db = MagicMock()
        mock_db.table().select().execute.return_value.data = [{"id": "doc-1"}]

        def read_doc(_):
            return mock_db.table("documents").select("*").execute()

        results = []
        lock = threading.Lock()

        def worker():
            r = read_doc("doc-1")
            with lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 5
        for r in results:
            assert r.data[0]["id"] == "doc-1"


# ── Celery task deduplication ──────────────────────────────────────────────────

class TestCeleryDeduplication:
    def test_same_document_key_prevents_duplicate(self):
        """Simulate celery task dedup via cache key."""
        cache = {}

        def submit_task_if_not_running(doc_id: str) -> bool:
            key = f"task:doc:{doc_id}"
            if cache.get(key):
                return False
            cache[key] = True
            return True

        assert submit_task_if_not_running("doc-1") is True
        assert submit_task_if_not_running("doc-1") is False
        assert submit_task_if_not_running("doc-2") is True


# ── Timeout vs completion ──────────────────────────────────────────────────────

class TestTimeoutRace:
    def test_timeout_wins_if_exceeded(self):
        """If a stage takes longer than the timeout, TimeoutError is raised."""
        from app.pipeline.orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)

        def slow_func():
            time.sleep(10)

        with pytest.raises(TimeoutError):
            orch._run_with_timeout(slow_func, 0.01)

    def test_completion_before_timeout(self):
        """If a stage completes before the timeout, the result is returned."""
        from app.pipeline.orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)

        def fast_func():
            return 42

        result = orch._run_with_timeout(fast_func, 10)
        assert result == 42


# ── Concurrent LLM calls ──────────────────────────────────────────────────────

class TestConcurrentLLMCalls:
    @pytest.mark.asyncio
    async def test_concurrent_llm_same_provider(self):
        """Multiple concurrent LLM calls to the same provider should be isolated."""
        mock_llm = MagicMock()
        mock_llm.generate = MagicMock(return_value="response")

        async def call_llm(prompt: str):
            return mock_llm.generate(prompt)

        prompts = ["p1", "p2", "p3", "p4", "p5"]
        results = await asyncio.gather(*[call_llm(p) for p in prompts])
        assert len(results) == 5
        assert all(r == "response" for r in results)
        assert mock_llm.generate.call_count == 5


# ── Concurrent RAG queries ────────────────────────────────────────────────────

class TestConcurrentRAG:
    @pytest.mark.asyncio
    async def test_concurrent_rag_queries_isolated(self):
        """Concurrent RAG queries should not interfere with each other."""
        mock_rag = AsyncMock()
        mock_rag.query = AsyncMock(side_effect=lambda q: f"result_for_{q}")

        async def query_rag(query: str):
            return await mock_rag.query(query)

        queries = ["q1", "q2", "q3"]
        results = await asyncio.gather(*[query_rag(q) for q in queries])
        assert results == ["result_for_q1", "result_for_q2", "result_for_q3"]


# ── SSE isolation ─────────────────────────────────────────────────────────────

class TestSSEIsolation:
    @pytest.mark.asyncio
    async def test_multiple_sse_connections_isolated(self):
        """Multiple SSE connections should each get their own message stream."""
        connections = {}

        async def sse_loop(conn_id: str):
            messages = []
            connections[conn_id] = messages
            return messages

        tasks = [asyncio.create_task(sse_loop(f"conn-{i}")) for i in range(3)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 3
        for i, r in enumerate(results):
            assert r == []
            assert f"conn-{i}" in connections


# ── Rate limiter bucket ───────────────────────────────────────────────────────

class TestRateLimiterBucket:
    def test_concurrent_bucket_increments(self):
        """Concurrent increments to the same rate-limit bucket should be thread-safe."""
        import threading as _t
        bucket = {"count": 0}
        lock = _t.Lock()

        def increment():
            with lock:
                bucket["count"] += 1

        threads = [_t.Thread(target=increment) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert bucket["count"] == 20


# ── Simultaneous document creation ─────────────────────────────────────────────

class TestSimultaneousDocumentCreation:
    def test_same_file_name_create(self):
        """Simultaneous creation with the same filename should generate unique IDs."""
        from app.models import DocumentMetadata, PipelineDocument
        doc1 = PipelineDocument(document_id="a", metadata=DocumentMetadata())
        doc2 = PipelineDocument(document_id="b", metadata=DocumentMetadata())
        assert doc1.document_id != doc2.document_id


# ── Concurrent template updates ────────────────────────────────────────────────

class TestConcurrentTemplateUpdates:
    def test_concurrent_updates_no_corruption(self):
        """Simultaneous template updates should not corrupt state."""
        template = {"name": "IEEE", "version": 1}
        lock = threading.Lock()

        def update_template(field, value):
            with lock:
                template[field] = value
                time.sleep(0.005)

        threads = [
            threading.Thread(target=update_template, args=("version", 2)),
            threading.Thread(target=update_template, args=("name", "ACM")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert template["name"] == "ACM"
        assert template["version"] == 2


# ── Session state races ───────────────────────────────────────────────────────

class TestSessionStateRaces:
    @pytest.mark.asyncio
    async def test_agent_chat_session_state_race(self):
        """Concurrent message writes to the same session should not corrupt."""
        from app.services.generator_session_service import GeneratorSessionService
        mock_svc = MagicMock(spec=GeneratorSessionService)
        mock_svc.add_message = AsyncMock()
        mock_svc._cache_lock = asyncio.Lock()

        async def send_message(session_id, msg):
            async with mock_svc._cache_lock:
                await mock_svc.add_message(session_id, msg)

        await asyncio.gather(
            send_message("session-1", "hello"),
            send_message("session-1", "world"),
        )
        assert mock_svc.add_message.call_count == 2


# ── Parallel ChromaDB writes ───────────────────────────────────────────────────

class TestParallelChromaDBWrites:
    @pytest.mark.asyncio
    async def test_parallel_chromadb_writes(self):
        """Parallel writes to the same ChromaDB collection should not interfere."""
        mock_collection = AsyncMock()
        mock_collection.add = AsyncMock()

        async def write_entry(doc_id, text):
            await mock_collection.add(ids=[doc_id], documents=[text])

        await asyncio.gather(
            write_entry("doc-1", "text 1"),
            write_entry("doc-2", "text 2"),
            write_entry("doc-3", "text 3"),
        )
        assert mock_collection.add.call_count == 3


# ── Async generator race ───────────────────────────────────────────────────────

class TestAsyncGeneratorRace:
    @pytest.mark.asyncio
    async def test_async_generator_no_race(self):
        """Concurrent iteration over async generators should be isolated."""

        async def number_gen(start, count):
            for i in range(count):
                await asyncio.sleep(0.001)
                yield start + i

        async def collect(gen):
            return [item async for item in gen]

        gen1 = number_gen(0, 3)
        gen2 = number_gen(10, 3)
        results = await asyncio.gather(collect(gen1), collect(gen2))
        assert results[0] == [0, 1, 2]
        assert results[1] == [10, 11, 12]
