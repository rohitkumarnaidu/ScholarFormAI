# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
import time
from unittest.mock import patch

from app.tasks.cleanup import cleanup_stranded_uploads


def test_cleanup_nonexistent_directory_returns_zero():
    result = cleanup_stranded_uploads("/nonexistent/path", retention_days=7)
    assert result == {"deleted_files": 0, "removed_dirs": 0, "retention_days": 7}


def test_cleanup_zero_retention_falls_back_to_settings_default(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    result = cleanup_stranded_uploads(str(upload_dir), retention_days=0)
    import app.config.settings as s
    assert result["retention_days"] == int(s.settings.RETENTION_DAYS)


def test_cleanup_negative_retention_defaults_to_one(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    result = cleanup_stranded_uploads(str(upload_dir), retention_days=-5)
    assert result["retention_days"] == 1


def test_cleanup_only_removes_old_files_keeps_recent(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    old_file = upload_dir / "old.docx"
    new_file = upload_dir / "new.docx"
    old_file.write_text("old")
    new_file.write_text("new")
    now = time.time()
    os.utime(old_file, (now - (4 * 86400), now - (4 * 86400)))
    os.utime(new_file, (now, now))
    result = cleanup_stranded_uploads(str(upload_dir), retention_days=3)
    assert result["deleted_files"] == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_cleanup_removes_empty_directories(tmp_path):
    upload_dir = tmp_path / "uploads"
    nested = upload_dir / "empty_subdir"
    nested.mkdir(parents=True, exist_ok=True)
    result = cleanup_stranded_uploads(str(upload_dir), retention_days=1)
    assert result["removed_dirs"] >= 1
    assert not nested.exists()


def test_cleanup_skips_nonempty_directories(tmp_path):
    upload_dir = tmp_path / "uploads"
    subdir = upload_dir / "subdir"
    subdir.mkdir(parents=True, exist_ok=True)
    keep_file = subdir / "keep.txt"
    keep_file.write_text("keep")
    cleanup_stranded_uploads(str(upload_dir), retention_days=1)
    assert subdir.exists()
    assert keep_file.exists()


def test_cleanup_handles_oserror_gracefully(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    broken_file = upload_dir / "broken.docx"
    broken_file.write_text("x")
    with patch("os.path.getmtime", side_effect=OSError("permission denied")):
        result = cleanup_stranded_uploads(str(upload_dir), retention_days=1)
    assert result["deleted_files"] == 0


def test_cleanup_empty_upload_dir_returns_zero(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    result = cleanup_stranded_uploads(str(upload_dir), retention_days=7)
    assert result["deleted_files"] == 0
    assert result["removed_dirs"] == 0


def test_cleanup_all_files_recent_removes_none(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    for i in range(3):
        f = upload_dir / f"file_{i}.txt"
        f.write_text("x")
        os.utime(f, (time.time(), time.time()))
    result = cleanup_stranded_uploads(str(upload_dir), retention_days=30)
    assert result["deleted_files"] == 0
