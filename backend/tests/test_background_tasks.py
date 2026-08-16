from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


class TestBackgroundTasks:
    def test_with_timeout_async_success(self):
        from app.utils.background_tasks import with_timeout

        @with_timeout(timeout_seconds=300)
        async def my_task():
            return "ok"

        result = asyncio_run(my_task())
        assert result == "ok"

    def test_with_timeout_sync_success(self):
        from app.utils.background_tasks import with_timeout

        @with_timeout(timeout_seconds=300)
        def sync_task():
            return "done"

        assert sync_task() == "done"

    def test_with_timeout_async_mark_job_failed_on_timeout(self):
        from app.utils.background_tasks import with_timeout

        with patch("app.utils.background_tasks._mark_job_as_failed"):

            @with_timeout(timeout_seconds=0.001)
            async def slow_task():
                import asyncio

                await asyncio.sleep(100)

            with pytest.raises(Exception):
                asyncio_run(slow_task())

    def test_run_pipeline_with_timeout_success(self):
        from app.utils.background_tasks import run_pipeline_with_timeout

        mock_orch = MagicMock()
        mock_orch.run_pipeline = MagicMock()
        with patch("app.utils.background_tasks._mark_job_as_failed"):
            asyncio_run(run_pipeline_with_timeout(mock_orch, "input.docx", "job1", "ieee"))
            mock_orch.run_pipeline.assert_called_once()

    def test_run_pipeline_with_timeout_exception(self):
        from app.utils.background_tasks import run_pipeline_with_timeout

        mock_orch = MagicMock()
        mock_orch.run_pipeline = MagicMock(side_effect=ValueError("fail"))
        with patch("app.utils.background_tasks._mark_job_as_failed") as mock_mark:
            asyncio_run(run_pipeline_with_timeout(mock_orch, "input.docx", "job1", "ieee"))
            mock_mark.assert_called_once()

    def test_mark_job_as_failed_success(self):
        from app.utils.background_tasks import _mark_job_as_failed

        with patch("app.services.document_service.DocumentService.mark_document_failed") as mock_md:
            _mark_job_as_failed("job1", "error msg")
            mock_md.assert_called_once_with("job1", "error msg")

    def test_mark_job_as_failed_exception(self):
        from app.utils.background_tasks import _mark_job_as_failed

        with patch(
            "app.services.document_service.DocumentService.mark_document_failed", side_effect=Exception("db fail")
        ):
            _mark_job_as_failed("job1", "error")

    def test_with_timeout_sync_mark_job_failed_on_timeout(self):
        from app.utils.background_tasks import with_timeout

        with patch("app.utils.background_tasks._mark_job_as_failed"):
            with patch("app.utils.background_tasks.asyncio.wait_for", side_effect=asyncio.TimeoutError):

                @with_timeout(timeout_seconds=300)
                def sync_task():
                    return "ok"

                with pytest.raises(asyncio.TimeoutError):
                    sync_task()

    def test_run_pipeline_with_timeout_timeout(self):
        from app.utils.background_tasks import run_pipeline_with_timeout

        mock_orch = MagicMock()
        import asyncio

        async def slow(*a, **kw):
            await asyncio.sleep(100)

        mock_orch.run_pipeline = slow
        with patch("app.utils.background_tasks._mark_job_as_failed") as mock_mark:
            with patch("app.utils.background_tasks.asyncio.wait_for", side_effect=asyncio.TimeoutError):
                asyncio_run(run_pipeline_with_timeout(mock_orch, "input.docx", "job1", "ieee"))
                mock_mark.assert_called_once()

    def test_async_wrapper_general_exception(self):
        from app.utils.background_tasks import with_timeout

        @with_timeout(timeout_seconds=300)
        async def failing_task():
            raise ValueError("oops")

        with pytest.raises(ValueError):
            asyncio_run(failing_task())


def asyncio_run(coro):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)
