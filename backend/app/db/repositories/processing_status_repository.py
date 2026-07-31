from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from postgrest import APIError

from app.db.repositories.base import BaseRepository, execute_with_transient_retry, is_valid_uuid
from app.exceptions import DatabaseUnavailableError
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)


class ProcessingStatusRepository(BaseRepository):
    TABLE_NAME = "processing_status"

    async def get_statuses(self, doc_id: str) -> List[Dict[str, Any]]:
        doc_id = str(doc_id)
        if not is_valid_uuid(doc_id):
            return []
        sb = self._get_client()

        def run_query():
            client = self._get_client()
            return client.table("processing_status").select("*").eq("document_id", str(doc_id)).execute()

        try:
            result = await execute_with_transient_retry(
                "get_processing_statuses",
                run_query,
                job_id=doc_id,
            )
            return result.data or []
        except APIError as e:
            logger.error("get_processing_statuses(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get processing statuses: {e}") from e
        except Exception as e:
            logger.error("get_processing_statuses(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get processing statuses: {e}") from e

    async def upsert(
        self,
        doc_id: str,
        phase: str,
        status: str,
        progress_percentage: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        doc_id = str(doc_id)
        sb = self._get_client()

        def run_upsert():
            client = self._get_client()
            payload: Dict[str, Any] = {
                "document_id": str(doc_id),
                "phase": phase,
                "status": status,
            }
            if progress_percentage is not None:
                payload["progress_percentage"] = progress_percentage
            if message is not None:
                payload["message"] = message
            return client.table("processing_status").upsert(payload, on_conflict="document_id,phase").execute()

        try:
            await asyncio.to_thread(run_upsert)
        except APIError as e:
            logger.error(
                "upsert_processing_status(%s, %s) failed: %s",
                doc_id,
                phase,
                e,
                extra=log_extra(job_id=doc_id),
            )
            raise DatabaseUnavailableError(f"Failed to upsert processing status: {e}") from e
        except Exception as e:
            logger.error(
                "upsert_processing_status(%s, %s) failed: %s",
                doc_id,
                phase,
                e,
                extra=log_extra(job_id=doc_id),
            )
            raise DatabaseUnavailableError(f"Failed to upsert processing status: {e}") from e
