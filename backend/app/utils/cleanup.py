# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import asyncio
import logging
import os
import time

from app.config.settings import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
RETENTION_DAYS = int(settings.RETENTION_DAYS)


async def cleanup_old_uploads():
    """
    Background task that periodically scans the upload directory
    and deletes files older than RETENTION_DAYS.
    """
    while True:
        try:
            logger.info(f"Running cleanup task. Scanning for files older than {RETENTION_DAYS} days...")

            if not os.path.exists(UPLOAD_DIR):
                logger.warning(f"Upload directory '{UPLOAD_DIR}' does not exist. Skipping cleanup.")
                await asyncio.sleep(3600)  # Check again in an hour
                continue

            now = time.time()
            cutoff = now - (RETENTION_DAYS * 86400)
            deleted_count = 0
            reclaimed_bytes = 0

            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)

                # Skip if it's not a file
                if not os.path.isfile(file_path):
                    continue

                # Check modification time
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime < cutoff:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        reclaimed_bytes += file_size
                        logger.debug(f"Deleted old file: {filename} ({file_size / 1024:.2f} KB)")
                except OSError as e:
                    logger.error(f"Error accessing/deleting {filename}: {e}")

            if deleted_count > 0:
                logger.info(
                    f"Cleanup complete. Deleted {deleted_count} files. Reclaimed {reclaimed_bytes / 1024 / 1024:.2f} MB."
                )
            else:
                logger.info("Cleanup complete. No old files found.")

        except Exception as e:
            logger.error(f"Unexpected error in cleanup task: {e}")

        # specific Wait for 24 hours before next run
        # We start the loop immediately implies it runs on startup,
        # then waits 24h.
        await asyncio.sleep(24 * 60 * 60)
