from __future__ import annotations

import logging
from typing import Any

from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DocumentVersionRepository(BaseRepository):
    TABLE_NAME = "document_versions"

    def insert_sync(self, payload: dict[str, Any]) -> bool:
        client = self._get_client()
        try:
            client.table(self.TABLE_NAME).insert(payload).execute()
            return True
        except Exception as e:
            logger.error("insert_sync failed: %s", e)
            return False

    def select_sync(self, document_id: str, version_number: int) -> dict[str, Any] | None:
        client = self._get_client()
        try:
            result = client.table(self.TABLE_NAME).select("*").eq("document_id", document_id).eq("version_number", version_number).maybe_single().execute()
            return result.data if result and result.data else None
        except Exception as e:
            logger.error("select_sync failed: %s", e)
            return None
