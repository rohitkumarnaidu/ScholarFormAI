from __future__ import annotations

import asyncio
import builtins
import logging
import os
from datetime import UTC
from typing import Any

from postgrest import APIError

from app.db.repositories.base import (
    BaseRepository,
    execute_with_transient_retry,
    is_valid_uuid,
)
from app.exceptions import DatabaseUnavailableError, DocumentNotFoundError
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository):
    TABLE_NAME = "documents"

    _supports_file_hash: bool | None = None
    _file_hash_warning_logged: bool = False
    _supports_output_hash: bool | None = None
    _output_hash_warning_logged: bool = False

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _should_query(doc_id: str, operation_name: str) -> bool:
        if is_valid_uuid(doc_id):
            return True
        logger.info(
            "%s skipped for non-UUID document id: %s",
            operation_name,
            doc_id,
            extra=log_extra(job_id=doc_id),
        )
        return False

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get(self, doc_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        if user_id:
            user_id = str(user_id)
        if not self._should_query(doc_id, "get_document"):
            return None
        self._get_client()

        def run_query():
            client = self._get_client()
            query = client.table("documents").select("*").eq("id", str(doc_id))
            if user_id:
                query = query.eq("user_id", str(user_id))
            return query.maybe_single().execute()

        try:
            result = await execute_with_transient_retry("get_document", run_query, job_id=doc_id)
            return result.data
        except APIError as e:
            logger.error("get_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document: {e}") from e
        except Exception as e:
            logger.error("get_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document: {e}") from e

    async def list(
        self,
        user_id: str,
        status: str | None = None,
        template: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> builtins.list[dict[str, Any]]:
        user_id = str(user_id)
        self._get_client()

        def run_query():
            client = self._get_client()
            query = (
                client.table("documents")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )
            if status:
                query = query.eq("status", status.upper())
            if template:
                query = query.eq("template", template.upper())
            return query.execute()

        try:
            result = await asyncio.to_thread(run_query)
            return result.data or []
        except APIError as e:
            logger.error("list_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to list documents: {e}") from e
        except Exception as e:
            logger.error("list_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to list documents: {e}") from e

    async def count(
        self,
        user_id: str,
        status: str | None = None,
        template: str | None = None,
    ) -> int:
        self._get_client()

        def run_query():
            client = self._get_client()
            query = client.table("documents").select("id", count="exact").eq("user_id", str(user_id))
            if status:
                query = query.eq("status", status.upper())
            if template:
                query = query.eq("template", template.upper())
            return query.execute()

        try:
            result = await asyncio.to_thread(run_query)
            return result.count or 0
        except APIError as e:
            logger.error("count_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count documents: {e}") from e
        except Exception as e:
            logger.error("count_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count documents: {e}") from e

    async def count_uploads_today(self, user_id: str) -> int:
        from datetime import datetime, timedelta

        self._get_client()

        def run_query():
            client = self._get_client()
            day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            return (
                client.table("documents")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .gte("created_at", day_start.isoformat())
                .lt("created_at", day_end.isoformat())
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_query)
            return int(result.count or 0)
        except APIError as e:
            logger.error("count_uploads_today(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count uploads: {e}") from e
        except Exception as e:
            logger.error("count_uploads_today(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count uploads: {e}") from e

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        doc_id: str,
        user_id: str | None,
        filename: str,
        template: str | None,
        original_file_path: str | None = None,
        formatting_options: dict[str, Any] | None = None,
        file_hash: str | None = None,
    ) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        if user_id:
            user_id = str(user_id)
        self._get_client()

        payload: dict[str, Any] = {
            "id": str(doc_id),
            "filename": filename,
            "status": "PROCESSING",
            "progress": 0,
        }
        if user_id:
            payload["user_id"] = str(user_id)
        if template:
            payload["template"] = template
        if original_file_path:
            payload["original_file_path"] = original_file_path
        if formatting_options:
            payload["formatting_options"] = formatting_options
        include_file_hash = bool(file_hash) and self._supports_file_hash is not False
        if include_file_hash:
            payload["file_hash"] = file_hash

        def run_insert(data: dict[str, Any]):
            client = self._get_client()
            return client.table("documents").insert(data).execute()

        try:
            result = await asyncio.to_thread(run_insert, payload)
            if include_file_hash:
                self._supports_file_hash = True
            return result.data[0] if result.data else None
        except Exception as exc:
            err = str(exc)
            missing_file_hash = "file_hash" in err and ("schema cache" in err or "column" in err or "PGRST204" in err)
            if missing_file_hash and "file_hash" in payload:
                try:
                    retry_payload = dict(payload)
                    retry_payload.pop("file_hash", None)
                    self._supports_file_hash = False
                    if not self._file_hash_warning_logged:
                        logger.warning(
                            "documents.file_hash not found in Supabase schema; "
                            "upload will continue without file hashing until migration is applied.",
                            extra=log_extra(job_id=doc_id),
                        )
                        self._file_hash_warning_logged = True
                    retry_result = await asyncio.to_thread(run_insert, retry_payload)
                    return retry_result.data[0] if retry_result.data else None
                except Exception as retry_exc:
                    logger.error(
                        "create_document(%s) retry without file_hash failed: %s",
                        doc_id,
                        retry_exc,
                        extra=log_extra(job_id=doc_id),
                    )
                    raise DatabaseUnavailableError(f"Failed to create document: {retry_exc}") from retry_exc
            logger.error("create_document(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to create document: {exc}") from exc

    async def update(self, doc_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        self._get_client()

        def run_update():
            client = self._get_client()
            return client.table("documents").update(updates).eq("id", str(doc_id)).execute()

        try:
            result = await asyncio.to_thread(run_update)
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error("update_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to update document: {e}") from e
        except Exception as e:
            logger.error("update_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to update document: {e}") from e

    def update_sync(self, doc_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        try:
            client = self._get_client()
            result = client.table("documents").update(updates).eq("id", str(doc_id)).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("update_sync(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            return None

    async def delete(self, document_id: str, user_id: str | None = None) -> bool:
        doc_id = str(document_id)
        owner_id = str(user_id) if user_id else None

        self._get_client()

        doc = await self.get(doc_id, owner_id)
        if not doc:
            raise DocumentNotFoundError(doc_id)

        for key in ("output_path", "original_file_path"):
            candidate = doc.get(key)
            if candidate and os.path.isfile(candidate):
                try:
                    os.remove(candidate)
                except OSError as exc:
                    logger.warning(
                        "Failed to remove file %s for document %s: %s",
                        candidate,
                        doc_id,
                        exc,
                        extra=log_extra(job_id=doc_id),
                    )

        def run_cleanup():
            client = self._get_client()
            client.table("processing_status").delete().eq("document_id", doc_id).execute()
            client.table("document_results").delete().eq("document_id", doc_id).execute()
            client.table("document_versions").delete().eq("document_id", doc_id).execute()

        try:
            await asyncio.to_thread(run_cleanup)
        except Exception as exc:
            logger.warning("Auxiliary cleanup failed for document %s: %s", doc_id, exc, extra=log_extra(job_id=doc_id))

        def run_delete():
            client = self._get_client()
            query = client.table("documents").delete().eq("id", doc_id)
            if owner_id:
                query = query.eq("user_id", owner_id)
            return query.execute()

        try:
            result = await asyncio.to_thread(run_delete)
            if result.data is not None and len(result.data) == 0:
                raise ValueError("Document delete affected 0 rows")
            return True
        except Exception as exc:
            logger.error(
                "delete_document(%s, user=%s) failed: %s", doc_id, owner_id, exc, extra=log_extra(job_id=doc_id)
            )
            raise DatabaseUnavailableError(f"Failed to delete document: {exc}") from exc

    # ── Status mutations ──────────────────────────────────────────────────────

    async def mark_failed(self, doc_id: str, error_message: str) -> None:
        doc_id = str(doc_id)
        if not self._is_available():
            logger.error("mark_document_failed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        def run_update():
            client = self._get_client()
            return (
                client.table("documents")
                .update(
                    {
                        "status": "FAILED",
                        "error_message": error_message,
                        "progress": 0,
                    }
                )
                .eq("id", str(doc_id))
                .execute()
            )

        try:
            await asyncio.to_thread(run_update)
        except Exception as exc:
            logger.error("mark_document_failed(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=doc_id))

    async def mark_completed(
        self,
        doc_id: str,
        output_path: str,
        raw_text: str | None = None,
    ) -> None:
        doc_id = str(doc_id)
        if not self._is_available():
            logger.error("mark_document_completed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        def run_update():
            client = self._get_client()
            updates: dict[str, Any] = {
                "status": "COMPLETED",
                "output_path": output_path,
                "progress": 100,
                "current_stage": "DONE",
            }
            if raw_text is not None:
                updates["raw_text"] = raw_text
            return client.table("documents").update(updates).eq("id", str(doc_id)).execute()

        try:
            await asyncio.to_thread(run_update)
        except Exception as exc:
            logger.error("mark_document_completed(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=doc_id))

    async def update_output_hash(self, doc_id: str, output_hash: str) -> bool:
        if not output_hash:
            return False
        if self._supports_output_hash is False:
            return False

        self._get_client()

        def run_update():
            client = self._get_client()
            return client.table("documents").update({"output_hash": output_hash}).eq("id", str(doc_id)).execute()

        try:
            await asyncio.to_thread(run_update)
            self._supports_output_hash = True
            return True
        except Exception as exc:
            err = str(exc)
            missing_output_hash = "output_hash" in err and (
                "schema cache" in err or "column" in err or "PGRST204" in err
            )
            if missing_output_hash:
                self._supports_output_hash = False
                if not self._output_hash_warning_logged:
                    logger.warning(
                        "documents.output_hash not found in Supabase schema; "
                        "download integrity checks will be best-effort until migration is applied.",
                        extra=log_extra(job_id=doc_id),
                    )
                    self._output_hash_warning_logged = True
                return False
            logger.error("update_output_hash(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=doc_id))
            return False
