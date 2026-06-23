# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
import time

from app.tasks import celery_tasks
from app.tasks.cleanup import cleanup_stranded_uploads


def test_cleanup_stranded_uploads_removes_old_files(tmp_path):
    upload_dir = tmp_path / "uploads"
    nested_dir = upload_dir / "synthesis" / "session-1"
    nested_dir.mkdir(parents=True, exist_ok=True)

    old_file = nested_dir / "old.docx"
    new_file = nested_dir / "new.docx"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    cutoff_seconds = 3 * 86400
    now = time.time()
    os.utime(old_file, (now - cutoff_seconds, now - cutoff_seconds))
    os.utime(new_file, (now, now))

    result = cleanup_stranded_uploads(str(upload_dir), retention_days=1)
    assert result["deleted_files"] >= 1
    assert not old_file.exists()
    assert new_file.exists()


def test_celery_cleanup_task_uses_recursive_cleanup(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    old_file = upload_dir / "old.tmp"
    old_file.write_text("x", encoding="utf-8")

    old_epoch = time.time() - (2 * 86400)
    os.utime(old_file, (old_epoch, old_epoch))

    result = celery_tasks.cleanup_uploads_task(upload_dir=str(upload_dir), retention_days=1)
    assert result["deleted"] >= 1


def test_celery_beat_has_daily_cleanup_schedule():
    beat_schedule = celery_tasks.celery_app.conf.beat_schedule or {}
    assert "cleanup-stranded-uploads-daily" in beat_schedule
    assert beat_schedule["cleanup-stranded-uploads-daily"]["task"] == "batch.cleanup_uploads"
