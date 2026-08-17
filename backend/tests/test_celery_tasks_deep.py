# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep tests for Celery task configuration and behavior.

Verifies retry policies, timeouts, path validation, and asyncio bridging.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.database]


class TestTimeoutConfig:
    def test_soft_time_limit_configured(self):
        import app.tasks.celery_tasks as ct

        conf = ct.celery_app.conf
        assert conf.task_soft_time_limit == 600

    def test_hard_time_limit_configured(self):
        import app.tasks.celery_tasks as ct

        conf = ct.celery_app.conf
        assert conf.task_time_limit == 900

    def test_acks_late_enabled(self):
        import app.tasks.celery_tasks as ct

        conf = ct.celery_app.conf
        assert conf.task_acks_late is True

    def test_reject_on_worker_lost(self):
        import app.tasks.celery_tasks as ct

        conf = ct.celery_app.conf
        assert conf.task_reject_on_worker_lost is True

    def test_track_started_enabled(self):
        import app.tasks.celery_tasks as ct

        conf = ct.celery_app.conf
        assert conf.task_track_started is True


class TestAsyncIoReplacement:
    def test_run_async_with_running_loop(self):
        import app.tasks.celery_tasks as ct

        mock_coro = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "done"
        mock_loop = MagicMock()
        mock_loop.run_coroutine_threadsafe.return_value = mock_future

        with patch.object(ct, "asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.return_value = mock_loop
            mock_asyncio.run_coroutine_threadsafe.return_value = mock_future
            result = ct._run_async(mock_coro)

        assert result == "done"
        mock_asyncio.run_coroutine_threadsafe.assert_called_once_with(mock_coro, mock_loop)
        mock_future.result.assert_called_once()

    def test_run_async_no_running_loop_fallback(self):
        import app.tasks.celery_tasks as ct

        mock_coro = MagicMock()
        call_count = 0

        def get_running_loop_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("no loop")
            mock_loop = MagicMock()
            mock_future = MagicMock()
            mock_future.result.return_value = "fallback_done"
            mock_loop.run_coroutine_threadsafe.return_value = mock_future
            return mock_loop

        with patch.object(ct, "asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = get_running_loop_side_effect
            mock_asyncio.run_coroutine_threadsafe.return_value = MagicMock()
            mock_asyncio.run_coroutine_threadsafe.return_value.result.return_value = "fallback_done"
            result = ct._run_async(mock_coro)

        assert result == "fallback_done"
        assert call_count == 2


class TestPathValidation:
    def test_validate_path_rejects_traversal(self):
        import os

        from app.tasks.celery_tasks import validate_path_safety

        path = os.path.join("uploads", "subdir", "..", "file")
        with pytest.raises(ValueError, match="Path traversal"):
            validate_path_safety(path)

    def test_validate_path_rejects_empty(self):
        from app.tasks.celery_tasks import validate_path_safety

        with pytest.raises(ValueError, match="Path is empty"):
            validate_path_safety("")

    def test_validate_path_rejects_outside_allowed(self):
        from app.tasks.celery_tasks import validate_path_safety

        with pytest.raises(ValueError, match="not in an allowed directory"):
            validate_path_safety("/tmp/malicious")

    def test_validate_path_accepts_uploads(self):
        from app.tasks.celery_tasks import validate_path_safety

        safe = validate_path_safety("uploads")
        assert "uploads" in safe

    def test_validate_path_accepts_output(self):
        from app.tasks.celery_tasks import validate_path_safety

        safe = validate_path_safety("output")
        assert "output" in safe

    def test_cleanup_accepts_valid_paths(self):
        from app.tasks.celery_tasks import cleanup_uploads_task

        with patch(
            "app.tasks.celery_tasks.cleanup_stranded_uploads", return_value={"deleted_files": 0, "removed_dirs": 0}
        ):
            with patch("app.tasks.celery_tasks.settings.RETENTION_DAYS", 30):
                result = cleanup_uploads_task(upload_dir="uploads", retention_days=7)

        assert result["deleted"] == 0

    def test_cleanup_rejects_traversal_via_task(self):
        import os

        from app.tasks.celery_tasks import cleanup_uploads_task

        path = os.path.join("uploads", "subdir", "..", "file")
        with patch("app.tasks.celery_tasks.cleanup_stranded_uploads"):
            with pytest.raises(ValueError, match="Path traversal"):
                cleanup_uploads_task(upload_dir=path)
