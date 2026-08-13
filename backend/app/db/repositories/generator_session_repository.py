from __future__ import annotations

import logging
from typing import Any

from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class GeneratorSessionRepository(BaseRepository):
    TABLE_NAME = "generator_sessions"

    def get_session(self, job_id: str) -> dict[str, Any] | None:
        """Fetch a generator session by ID."""
        if not self._is_available():
            return None
        try:
            result = self._table().select("*").eq("id", str(job_id)).maybe_single().execute()
            if result and result.data:
                return result.data
            return None
        except Exception as exc:
            logger.error("Failed to fetch generator session %s: %s", job_id, exc)
            return None

    def insert_session(self, payload: dict[str, Any]) -> bool:
        """Insert a new generator session."""
        if not self._is_available():
            return False
        try:
            self._table().insert(payload).execute()
            return True
        except Exception as exc:
            logger.error("Failed to insert generator session %s: %s", payload.get("id"), exc)
            return False

    def update_session(self, job_id: str, updates: dict[str, Any]) -> bool:
        """Update a generator session."""
        if not self._is_available():
            return False
        try:
            self._table().update(updates).eq("id", str(job_id)).execute()
            return True
        except Exception as exc:
            logger.error("Failed to update generator session %s: %s", job_id, exc)
            return False
