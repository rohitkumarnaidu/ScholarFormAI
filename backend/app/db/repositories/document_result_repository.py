from __future__ import annotations

import asyncio
import logging
from typing import Any

from postgrest import APIError

from app.db.repositories.base import BaseRepository, execute_with_transient_retry, is_valid_uuid
from app.exceptions import DatabaseUnavailableError
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)


class DocumentResultRepository(BaseRepository):
    TABLE_NAME = "document_results"

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        if not is_valid_uuid(doc_id):
            return None
        self._get_client()

        def run_query():
            client = self._get_client()
            return client.table("document_results").select("*").eq("document_id", str(doc_id)).maybe_single().execute()

        try:
            result = await execute_with_transient_retry(
                "get_document_result",
                run_query,
                job_id=doc_id,
            )
            if result is None:
                return None
            if isinstance(result, dict):
                return result.get("data")
            return getattr(result, "data", None)
        except APIError as e:
            logger.error("get_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document result: {e}") from e
        except Exception as e:
            logger.error("get_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document result: {e}") from e

    async def upsert(
        self,
        doc_id: str,
        structured_data: dict[str, Any] | None = None,
        validation_results: dict[str, Any] | None = None,
    ) -> None:
        doc_id = str(doc_id)
        self._get_client()

        def run_upsert():
            client = self._get_client()
            payload: dict[str, Any] = {"document_id": str(doc_id)}
            if structured_data is not None:
                payload["structured_data"] = structured_data
            if validation_results is not None:
                payload["validation_results"] = validation_results
            return client.table("document_results").upsert(payload, on_conflict="document_id").execute()

        try:
            await asyncio.to_thread(run_upsert)
        except APIError as e:
            logger.error("upsert_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert document result: {e}") from e
        except Exception as e:
            logger.error("upsert_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert document result: {e}") from e
