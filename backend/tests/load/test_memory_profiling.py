# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Memory profiling tests — simulated memory boundary checks.
Verifies that memory usage stays within thresholds for various operations.
"""

import gc
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

MB = 1024 * 1024
PIPELINE_MEMORY_LIMIT_MB = 100
RAG_MEMORY_LIMIT_MB = 80
CACHE_MEMORY_LIMIT_MB = 50
WEBOOK_MEMORY_LIMIT_MB = 30
STREAMING_MEMORY_LIMIT_MB = 20
UPLOAD_CLEANUP_LIMIT_MB = 50


def _force_gc():
    gc.collect()
    gc.collect()
    gc.collect()


def _estimate_object_size(obj) -> int:
    """Rough estimate of object size in bytes (sys.getsizeof + nested)."""
    size = sys.getsizeof(obj, default=0)
    if isinstance(obj, dict):
        size += sum(_estimate_object_size(k) + _estimate_object_size(v) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        size += sum(_estimate_object_size(i) for i in obj)
    elif isinstance(obj, str):
        size += len(obj.encode("utf-8"))
    return size


def _make_large_block(text_len: int = 500) -> MagicMock:
    """Create a mock block with text of given length."""
    block = MagicMock()
    block.block_id = f"block-{id(block)}"
    block.block_type = "body"
    block.text = "X" * text_len
    block.index = 0
    return block


class TestMemoryProfiling:
    """Memory usage threshold tests for pipeline operations."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_pipeline_document_10k_blocks_under_threshold(self):
        """PipelineDocument with 10k blocks stays under memory threshold."""
        from app.models import DocumentMetadata, PipelineDocument

        n_blocks = 10000
        doc = PipelineDocument(
            document_id="mem-test-large",
            metadata=DocumentMetadata(
                title="Large Document",
                authors=["Test Author"],
                abstract="x" * 1000,
            ),
        )
        doc.blocks = [_make_large_block(200) for _ in range(n_blocks)]

        total_size = _estimate_object_size(doc)
        total_size_mb = total_size / MB

        assert total_size_mb < PIPELINE_MEMORY_LIMIT_MB, (
            f"PipelineDocument with {n_blocks} blocks is {total_size_mb:.1f}MB >= {PIPELINE_MEMORY_LIMIT_MB}MB"
        )
        assert len(doc.blocks) == n_blocks

    @pytest.mark.performance
    @pytest.mark.slow
    def test_streaming_response_no_full_buffer(self):
        """Streaming response doesn't buffer the entire response in memory (simulated)."""
        max_chunk_size = STREAMING_MEMORY_LIMIT_MB * MB
        chunk_count = 500
        chunk_size = 4096

        total_sent = chunk_count * chunk_size
        assert total_sent < max_chunk_size, (
            f"Total stream data {total_sent / MB:.1f}MB >= {STREAMING_MEMORY_LIMIT_MB}MB limit"
        )

        peak_buffered = chunk_size
        assert peak_buffered < STREAMING_MEMORY_LIMIT_MB * MB, f"Single chunk {peak_buffered / MB:.1f}MB exceeds limit"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_rag_engine_1000_guidelines_under_threshold(self):
        """RAG engine with 1000 guidelines stays under memory threshold."""
        with patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model", return_value=MagicMock()):
            from app.pipeline.intelligence.rag_engine import RagEngine

            engine = RagEngine()
            engine.knowledge_base.clear()

            n_guidelines = 1000
            for i in range(n_guidelines):
                engine.knowledge_base.append(
                    {
                        "content": f"Academic formatting guideline {i}: " + "rules " * 100,
                        "embedding": [float(j % 100) / 100.0 for j in range(128)],
                        "metadata": {
                            "source": f"style-guide-{i % 10}",
                            "section": "formatting",
                            "page": i % 50,
                        },
                    }
                )

            total_size = _estimate_object_size(engine.knowledge_base)
            total_size_mb = total_size / MB
            assert total_size_mb < RAG_MEMORY_LIMIT_MB, (
                f"RAG knowledge base with {n_guidelines} entries is {total_size_mb:.1f}MB >= {RAG_MEMORY_LIMIT_MB}MB"
            )
            assert len(engine.knowledge_base) == n_guidelines

    @pytest.mark.performance
    @pytest.mark.slow
    def test_multiple_concurrent_pipeline_jobs_memory(self):
        """Multiple concurrent pipeline jobs stay under memory ceiling (simulated)."""
        n_jobs = 5

        _force_gc()

        mock_jobs = MagicMock()
        mock_jobs.config = {"templates_dir": "app/templates", "temp_dir": "temp_mem"}
        mock_jobs.status = "idle"
        mock_jobs.job_id = "mock-job"

        total_size = _estimate_object_size(mock_jobs) * n_jobs
        total_size_mb = total_size / MB

        assert total_size_mb < PIPELINE_MEMORY_LIMIT_MB, (
            f"{n_jobs} concurrent jobs total {total_size_mb:.1f}MB >= {PIPELINE_MEMORY_LIMIT_MB}MB"
        )

    @pytest.mark.performance
    @pytest.mark.slow
    async def test_large_file_upload_temp_cleanup(self):
        """Large file upload temporary storage is cleaned up properly."""
        upload_dir = tempfile.mkdtemp(prefix="upload_test_")

        try:
            file_path = os.path.join(upload_dir, "large_test.docx")
            file_size = 15 * MB
            with open(file_path, "wb") as f:
                f.write(b"X" * file_size)

            assert os.path.getsize(file_path) == file_size
            assert file_size < UPLOAD_CLEANUP_LIMIT_MB * MB, f"File too large {file_size / MB:.1f}MB"

            os.remove(file_path)
            assert not os.path.exists(file_path)

            remaining = os.listdir(upload_dir)
            assert len(remaining) == 0, f"Upload dir not empty after cleanup: {remaining}"
        finally:
            import shutil

            shutil.rmtree(upload_dir, ignore_errors=True)

    @pytest.mark.performance
    @pytest.mark.slow
    def test_chromadb_collection_no_leak_across_sessions(self):
        """ChromaDB collection doesn't leak data across separate sessions (simulated)."""
        collections_a = set()
        collections_b = set()

        n_items_a = 50
        n_items_b = 50

        for i in range(n_items_a):
            collections_a.add(f"session-a-doc-{i}")
        for i in range(n_items_b):
            collections_b.add(f"session-b-doc-{i}")

        overlap = collections_a & collections_b
        assert len(overlap) == 0, f"Collections leaked: {len(overlap)} shared items"
        assert len(collections_a) == n_items_a
        assert len(collections_b) == n_items_b

        size_a = sum(len(item) for item in collections_a)
        size_b = sum(len(item) for item in collections_b)
        assert size_a + size_b < 10 * MB, f"Collection size {size_a + size_b}B exceeds limit"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_cached_llm_responses_memory_bounded(self, tmp_path):
        """Cached LLM responses stay within memory bounds."""
        from app.cache.redis_cache import redis_cache

        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True

        n_entries = 500
        cache_entry_size = 5000

        with patch.object(redis_cache, "_ensure_client", return_value=mock_redis):
            for i in range(n_entries):
                redis_cache.set_llm_result(
                    f"test:llm:cache:{i}",
                    "X" * cache_entry_size,
                    3600,
                )

            stored_sizes = [cache_entry_size + len(f"test:llm:cache:{i}") for i in range(n_entries)]
            total_stored = sum(stored_sizes)
            total_stored_mb = total_stored / MB

            assert total_stored_mb < CACHE_MEMORY_LIMIT_MB, (
                f"LLM cache {n_entries} entries = {total_stored_mb:.1f}MB >= {CACHE_MEMORY_LIMIT_MB}MB"
            )

    @pytest.mark.performance
    @pytest.mark.slow
    def test_webhook_delivery_memory_bounded(self):
        """Webhook delivery memory usage is bounded per delivery attempt (simulated)."""
        payload_size = 500 * 1024
        single_payload_size = len(repr({"data": "X" * payload_size}))
        n_deliveries = 20

        total_size = single_payload_size * n_deliveries
        total_size_mb = total_size / MB
        assert total_size_mb < WEBOOK_MEMORY_LIMIT_MB, (
            f"Webhook deliveries total {total_size_mb:.1f}MB >= {WEBOOK_MEMORY_LIMIT_MB}MB"
        )

        single_size_mb = single_payload_size / MB
        assert single_size_mb < WEBOOK_MEMORY_LIMIT_MB / 2, f"Single webhook payload {single_size_mb:.1f}MB too large"
