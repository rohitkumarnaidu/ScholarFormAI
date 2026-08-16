from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_no_upload_dir(self):
        from app.utils.cleanup import cleanup_old_uploads

        with patch("app.utils.cleanup.os.path.exists", return_value=False):
            with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                task = asyncio.create_task(cleanup_old_uploads())
                await asyncio.sleep(0)
                task.cancel()

    @pytest.mark.asyncio
    async def test_cleanup_deletes_old_files(self):
        from app.utils.cleanup import cleanup_old_uploads

        with patch("app.utils.cleanup.os.path.exists", return_value=True):
            with patch("app.utils.cleanup.os.listdir", return_value=["old.docx"]):
                with patch("app.utils.cleanup.os.path.isfile", return_value=True):
                    with patch("app.utils.cleanup.os.path.getmtime", return_value=100):
                        with patch("app.utils.cleanup.time.time", return_value=1e9):
                            with patch("app.utils.cleanup.os.path.getsize", return_value=1024):
                                with patch("app.utils.cleanup.os.remove") as mock_remove:
                                    with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                                        task = asyncio.create_task(cleanup_old_uploads())
                                        await asyncio.sleep(0)
                                        task.cancel()
                                        mock_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_skips_current(self):
        from app.utils.cleanup import cleanup_old_uploads

        with patch("app.utils.cleanup.os.path.exists", return_value=True):
            with patch("app.utils.cleanup.os.listdir", return_value=["new.docx"]):
                with patch("app.utils.cleanup.os.path.isfile", return_value=True):
                    with patch("app.utils.cleanup.os.path.getmtime", return_value=1e9):
                        with patch("app.utils.cleanup.time.time", return_value=1000):
                            with patch("app.utils.cleanup.os.remove") as mock_remove:
                                with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                                    task = asyncio.create_task(cleanup_old_uploads())
                                    await asyncio.sleep(0)
                                    task.cancel()
                                    mock_remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_os_error_handled(self):
        from app.utils.cleanup import cleanup_old_uploads

        with patch("app.utils.cleanup.os.path.exists", return_value=True):
            with patch("app.utils.cleanup.os.listdir", return_value=["bad.docx"]):
                with patch("app.utils.cleanup.os.path.isfile", return_value=True):
                    with patch("app.utils.cleanup.os.path.getmtime", side_effect=OSError("permission denied")):
                        with patch("app.utils.cleanup.logger") as mock_log:
                            with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                                task = asyncio.create_task(cleanup_old_uploads())
                                await asyncio.sleep(0)
                                task.cancel()
                                mock_log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_unexpected_exception_caught(self):
        from app.utils.cleanup import cleanup_old_uploads

        with patch("app.utils.cleanup.os.path.exists", side_effect=Exception("boom")):
            with patch("app.utils.cleanup.logger") as mock_log:
                with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                    task = asyncio.create_task(cleanup_old_uploads())
                    await asyncio.sleep(0)
                    task.cancel()
                    mock_log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_skips_directories(self):
        from app.utils.cleanup import cleanup_old_uploads

        with patch("app.utils.cleanup.os.path.exists", return_value=True):
            with patch("app.utils.cleanup.os.listdir", return_value=["subdir"]):
                with patch("app.utils.cleanup.os.path.isfile", return_value=False):
                    with patch("app.utils.cleanup.os.remove") as mock_remove:
                        with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                            task = asyncio.create_task(cleanup_old_uploads())
                            await asyncio.sleep(0)
                            task.cancel()
                            mock_remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_logs_deleted_count(self):
        from app.utils.cleanup import cleanup_old_uploads

        with patch("app.utils.cleanup.os.path.exists", return_value=True):
            with patch("app.utils.cleanup.os.listdir", return_value=["old.docx"]):
                with patch("app.utils.cleanup.os.path.isfile", return_value=True):
                    with patch("app.utils.cleanup.os.path.getmtime", return_value=100):
                        with patch("app.utils.cleanup.time.time", return_value=1e9):
                            with patch("app.utils.cleanup.os.path.getsize", return_value=2048):
                                with patch("app.utils.cleanup.os.remove"):
                                    with patch("app.utils.cleanup.logger") as mock_log:
                                        with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                                            task = asyncio.create_task(cleanup_old_uploads())
                                            await asyncio.sleep(0)
                                            task.cancel()
                                            mock_log.info.assert_any_call(
                                                "Cleanup complete. Deleted 1 files. Reclaimed 0.00 MB."
                                            )
