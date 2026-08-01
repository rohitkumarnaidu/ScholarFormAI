# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from app.config.settings import settings

logger = logging.getLogger(__name__)


def cleanup_stranded_uploads(upload_dir: str = "uploads", retention_days: int | None = None) -> dict[str, int]:
    """
    Purge stranded upload artifacts older than retention policy.

    This routine is safe to run from cron/Celery beat and removes:
    - top-level files in uploads/
    - nested synthesis/temp files under uploads/**
    - empty directories after cleanup
    """
    days = int(retention_days or settings.RETENTION_DAYS)
    if days <= 0:
        days = 1
    if not os.path.isdir(upload_dir):
        return {"deleted_files": 0, "removed_dirs": 0, "retention_days": days}

    cutoff_epoch = datetime.now(UTC).timestamp() - (days * 86400)
    deleted_files = 0
    removed_dirs = 0

    for root, dirs, files in os.walk(upload_dir, topdown=False):
        for filename in files:
            path = os.path.join(root, filename)
            try:
                if os.path.getmtime(path) < cutoff_epoch:
                    os.remove(path)
                    deleted_files += 1
            except OSError as exc:
                logger.warning("Cleanup failed for %s: %s", path, exc)

        for dirname in dirs:
            dpath = os.path.join(root, dirname)
            try:
                if not os.listdir(dpath):
                    os.rmdir(dpath)
                    removed_dirs += 1
            except OSError:
                continue

    logger.info(
        "Cleanup complete: removed_files=%d removed_dirs=%d retention_days=%d",
        deleted_files,
        removed_dirs,
        days,
    )
    return {"deleted_files": deleted_files, "removed_dirs": removed_dirs, "retention_days": days}
