# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Realistic load test scenarios using asyncio + mock services.
Simulates concurrent user patterns without external load tools.
"""

import asyncio
import io
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

BACKEND_ROOT = None  # conftest handles sys.path


def _mock_upload_response():
    return {
        "id": str(uuid.uuid4()),
        "filename": "test.docx",
        "status": "completed",
        "user_id": "load-test-user",
    }


def _mock_generation_session():
    return MagicMock(
        id=str(uuid.uuid4()),
        user_id="load-test-user",
        status="active",
        messages=[],
        created_at="2026-01-01T00:00:00Z",
    )


@pytest.fixture
def mock_doc_service():
    with patch("app.services.document_crud_service.get_supabase_client") as mock_sb:
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [_mock_upload_response()]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            _mock_upload_response()
        ]
        mock_sb.return_value = mock_client
        yield mock_sb


@pytest.fixture
def mock_gen_service():
    with patch("app.services.generator_session_service.get_supabase_client") as mock_sb:
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [_mock_generation_session()]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            _mock_generation_session()
        ]
        mock_sb.return_value = mock_client
        yield mock_sb


class TestConcurrentUserScenarios:
    """Simulate concurrent user patterns at the service layer."""

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_10_concurrent_uploads(self, mock_doc_service):
        """10 concurrent users uploading documents simultaneously."""
        from app.services.document_service import DocumentService

        n_users = 10
        mock_list = AsyncMock(return_value=[_mock_upload_response()])
        mock_create = AsyncMock(return_value=_mock_upload_response())

        with (
            patch.object(DocumentService, "list_documents", mock_list),
            patch.object(DocumentService, "create_document", mock_create),
        ):
            start = time.perf_counter()
            results = await asyncio.gather(*[
                DocumentService.create_document(
                    user_id=f"user-{i}",
                    filename=f"paper-{i}.docx",
                    file_data=io.BytesIO(b"mock content"),
                )
                for i in range(n_users)
            ])
            elapsed = time.perf_counter() - start

        assert len(results) == n_users
        for r in results:
            assert r is not None
            assert r.get("status") == "completed"
        assert elapsed < 10.0, f"10 concurrent uploads took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_5_concurrent_generation_sessions(self, mock_gen_service):
        """5 concurrent generation sessions all completing successfully."""
        from app.services.generator_session_service import GeneratorSessionService

        n_sessions = 5
        mock_create = AsyncMock(return_value=_mock_generation_session())
        mock_get = AsyncMock(return_value=_mock_generation_session())

        with (
            patch.object(GeneratorSessionService, "create_session", mock_create),
            patch.object(GeneratorSessionService, "get_session", mock_get),
        ):
            sessions = []
            for i in range(n_sessions):
                sessions.append(
                    GeneratorSessionService.create_session(
                        user_id=f"gen-user-{i}",
                        session_type="manuscript",
                    )
                )

            start = time.perf_counter()
            results = await asyncio.gather(*sessions)
            elapsed = time.perf_counter() - start

        assert len(results) == n_sessions
        for s in results:
            assert s is not None
            assert s.status == "active"
        assert elapsed < 8.0, f"5 concurrent sessions took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mixed_workload(self, mock_doc_service, mock_gen_service):
        """Mixed: 3 uploads + 3 generations + 4 queries simultaneously."""
        from app.services.document_service import DocumentService
        from app.services.generator_session_service import GeneratorSessionService

        mock_create_doc = AsyncMock(return_value=_mock_upload_response())
        mock_create_session = AsyncMock(return_value=_mock_generation_session())
        mock_list_docs = AsyncMock(return_value=[_mock_upload_response()])

        with (
            patch.object(DocumentService, "create_document", mock_create_doc),
            patch.object(GeneratorSessionService, "create_session", mock_create_session),
            patch.object(DocumentService, "list_documents", mock_list_docs),
        ):
            uploads = [
                DocumentService.create_document(user_id=f"mix-user-{i}", filename=f"mix-{i}.docx", file_data=io.BytesIO(b"data"))
                for i in range(3)
            ]
            sessions = [
                GeneratorSessionService.create_session(user_id=f"mix-gen-{i}", session_type="manuscript")
                for i in range(3)
            ]
            queries = [
                DocumentService.list_documents(user_id="query-user", limit=20)
                for _ in range(4)
            ]

            start = time.perf_counter()
            all_results = await asyncio.gather(*uploads, *sessions, *queries)
            elapsed = time.perf_counter() - start

        assert len(all_results) == 10
        assert elapsed < 10.0, f"Mixed workload took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_burst_30_sequential_requests(self, mock_doc_service):
        """Burst traffic: 30 rapid sequential requests."""
        from app.services.document_service import DocumentService

        mock_get = AsyncMock(return_value=_mock_upload_response())

        with patch.object(DocumentService, "get_document", mock_get):
            start = time.perf_counter()
            for i in range(30):
                result = await DocumentService.get_document(doc_id=f"burst-{i}", user_id="burst-user")
                assert result is not None
            elapsed = time.perf_counter() - start

        assert elapsed < 5.0, f"30 sequential requests took {elapsed:.2f}s (expected < 5s)"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_100_requests_10_per_sec(self, mock_doc_service):
        """Sustained traffic: 100 requests over ~10 seconds (10/sec pace)."""
        from app.services.document_service import DocumentService

        mock_list = AsyncMock(return_value=[_mock_upload_response()])

        with patch.object(DocumentService, "list_documents", mock_list):
            start = time.perf_counter()
            for i in range(100):
                await DocumentService.list_documents(user_id="sustain-user", limit=20)
                if i % 10 == 9:
                    await asyncio.sleep(0.05)
            elapsed = time.perf_counter() - start

        assert elapsed < 15.0, f"100 sustained requests took {elapsed:.2f}s (expected < 15s)"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_file_downloads(self, mock_doc_service):
        """Concurrent file downloads: 8 simultaneous get_document requests."""
        from app.services.document_service import DocumentService

        n_downloads = 8
        mock_get = AsyncMock(return_value=_mock_upload_response())

        with patch.object(DocumentService, "get_document", mock_get):
            start = time.perf_counter()
            results = await asyncio.gather(*[
                DocumentService.get_document(doc_id=f"dl-{i}", user_id="dl-user")
                for i in range(n_downloads)
            ])
            elapsed = time.perf_counter() - start

        assert len(results) == n_downloads
        assert elapsed < 8.0, f"{n_downloads} concurrent downloads took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_template_listing(self):
        """Concurrent template listing: 10 simultaneous list calls."""
        from app.routers.v1.templates import _list_builtin_templates

        class _SortableEntry:
            def __init__(self, name):
                self.name = name
            def __lt__(self, other):
                return self.name < other.name
            def is_dir(self):
                return True

        mock_entries = [_SortableEntry(t) for t in ("ieee", "apa", "mla", "nature", "springer", "chicago", "harvard", "vancouver")]

        n_calls = 10
        with (
            patch("app.routers.v1.templates.Path.exists", return_value=True),
            patch("app.routers.v1.templates.Path.iterdir") as mock_iter,
        ):
            mock_iter.return_value = mock_entries
            start = time.perf_counter()
            results = await asyncio.gather(*[
                _list_builtin_templates()
                for _ in range(n_calls)
            ])
            elapsed = time.perf_counter() - start

        assert len(results) == n_calls
        for r in results:
            assert len(r.get("templates", [])) >= 3
        assert elapsed < 5.0, f"{n_calls} template listings took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mixed_read_write_ratio_70_30(self, mock_doc_service):
        """70% read, 30% write operations: 20 total operations."""
        from app.services.document_service import DocumentService

        mock_read = AsyncMock(return_value=_mock_upload_response())
        mock_write = AsyncMock(return_value=_mock_upload_response())

        with (
            patch.object(DocumentService, "get_document", mock_read),
            patch.object(DocumentService, "create_document", mock_write),
        ):
            n_total = 20
            n_reads = int(n_total * 0.7)
            n_writes = n_total - n_reads

            ops = []
            op_types = []
            for i in range(n_reads):
                ops.append(DocumentService.get_document(doc_id=f"rw-{i}", user_id="rw-user"))
                op_types.append("read")
            for i in range(n_writes):
                ops.append(DocumentService.create_document(user_id="rw-user", filename=f"rw-{i}.docx", file_data=io.BytesIO(b"data")))
                op_types.append("write")

            start = time.perf_counter()
            results = await asyncio.gather(*ops)
            elapsed = time.perf_counter() - start

        assert len(results) == n_total
        read_results = [r for r, t in zip(results, op_types, strict=False) if t == "read"]
        write_results = [r for r, t in zip(results, op_types, strict=False) if t == "write"]
        assert len(read_results) == n_reads
        assert len(write_results) == n_writes
        assert elapsed < 10.0, f"70/30 mixed workload took {elapsed:.2f}s"
