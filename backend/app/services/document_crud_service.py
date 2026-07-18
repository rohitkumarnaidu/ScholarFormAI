# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document CRUD service — database operations for the `documents`,
`document_results`, and `processing_status` tables.

Extracted from the fat `document_service.py` so the orchestration,
sharing, and CRUD concerns live in separate units. All public methods
are async-safe and delegate to the supabase-py client.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Optional, List, Dict, Any

from postgrest import APIError

from app.db.supabase_client import get_supabase_client
from app.utils.logging_context import log_extra
from app.exceptions import (
    DatabaseUnavailableError,
    DocumentNotFoundError,
)

logger = logging.getLogger(__name__)


class DocumentCrudService:
    """
    CRUD + result/status persistence for documents.

    Shared helpers (`_is_valid_uuid`, `_should_query_document_tables`,
    `_execute_with_transient_retry`, `_is_transient_supabase_error`) are
    reused by the pipeline and share services through module-level
    functions so behaviour is identical across the decomposed services.
    """

    _supports_file_hash: Optional[bool] = None
    _file_hash_warning_logged: bool = False
    _supports_output_hash: Optional[bool] = None
    _output_hash_warning_logged: bool = False
    _TRANSIENT_ERROR_MARKERS = (
        "remoteprotocolerror",
        "server disconnected",
        "connection reset",
        "connection aborted",
        "connection refused",
        "read timed out",
        "connect timeout",
        "timed out",
        "temporarily unavailable",
        "network is unreachable",
    )

    # ── Shared static helpers (re-exported by the facade) ────────────────────

    @staticmethod
    def _is_transient_supabase_error(exc: Exception) -> bool:
        exc_name = type(exc).__name__.lower()
        if exc_name in {"remoteprotocolerror", "connecterror", "readtimeout", "writetimeout"}:
            return True

        message = str(exc).lower()
        return any(marker in message for marker in DocumentCrudService._TRANSIENT_ERROR_MARKERS)

    @staticmethod
    async def _execute_with_transient_retry(
        operation_name: str,
        operation,
        *,
        job_id: Optional[str] = None,
        max_attempts: int = 3,
    ):
        attempt = 0
        while True:
            try:
                return await asyncio.to_thread(operation)
            except Exception as exc:
                attempt += 1
                should_retry = (
                    DocumentCrudService._is_transient_supabase_error(exc)
                    and attempt < max_attempts
                )
                if not should_retry:
                    raise

                delay_seconds = 0.15 * (2 ** (attempt - 1))
                logger.warning(
                    "%s transient Supabase error (attempt %s/%s): %s; retrying in %.2fs",
                    operation_name,
                    attempt,
                    max_attempts,
                    exc,
                    delay_seconds,
                    extra=log_extra(job_id=job_id),
                )
                get_supabase_client(refresh=True)
                await asyncio.sleep(delay_seconds)

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        try:
            uuid.UUID(str(value))
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _should_query_document_tables(doc_id: str, operation_name: str) -> bool:
        if DocumentCrudService._is_valid_uuid(doc_id):
            return True
        logger.info(
            "%s skipped for non-UUID document id: %s",
            operation_name,
            doc_id,
            extra=log_extra(job_id=doc_id),
        )
        return False

    # ── Documents CRUD ───────────────────────────────────────────────────────

    async def get_document(
        self, doc_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        doc_id = str(doc_id)
        if user_id:
            user_id = str(user_id)
        if not self._should_query_document_tables(doc_id, "get_document"):
            return None
        sb = get_supabase_client()
        if sb is None:
            logger.error("get_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            query = client.table("documents").select("*").eq("id", str(doc_id))
            if user_id:
                query = query.eq("user_id", str(user_id))
            return query.maybe_single().execute()

        try:
            result = await self._execute_with_transient_retry(
                "get_document",
                run_query,
                job_id=doc_id,
            )
            return result.data
        except APIError as e:
            logger.error("get_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document: {e}") from e
        except Exception as e:
            logger.error("get_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document: {e}") from e

    async def list_documents(
        self,
        user_id: str,
        status: Optional[str] = None,
        template: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        sb = get_supabase_client()
        user_id = str(user_id)
        if sb is None:
            logger.error("list_documents: Supabase client not available.", extra=log_extra())
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
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

    async def count_documents(
        self,
        user_id: str,
        status: Optional[str] = None,
        template: Optional[str] = None,
    ) -> int:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            query = (
                client.table("documents")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
            )
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
        from datetime import datetime, timedelta, timezone

        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
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

    async def create_document(
        self,
        doc_id: str,
        user_id: Optional[str],
        filename: str,
        template: Optional[str],
        original_file_path: Optional[str] = None,
        formatting_options: Optional[Dict[str, Any]] = None,
        file_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        sb = get_supabase_client()
        doc_id = str(doc_id)
        if user_id:
            user_id = str(user_id)
        if sb is None:
            logger.error("create_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        payload: Dict[str, Any] = {
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
        include_file_hash = (
            bool(file_hash)
            and DocumentCrudService._supports_file_hash is not False
        )
        if include_file_hash:
            payload["file_hash"] = file_hash

        def run_insert(data: Dict[str, Any]):
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return client.table("documents").insert(data).execute()

        try:
            result = await asyncio.to_thread(run_insert, payload)
            if include_file_hash:
                DocumentCrudService._supports_file_hash = True
            return result.data[0] if result.data else None
        except Exception as exc:
            err = str(exc)
            missing_file_hash = (
                "file_hash" in err
                and ("schema cache" in err or "column" in err or "PGRST204" in err)
            )
            if missing_file_hash and "file_hash" in payload:
                try:
                    retry_payload = dict(payload)
                    retry_payload.pop("file_hash", None)
                    DocumentCrudService._supports_file_hash = False
                    if not DocumentCrudService._file_hash_warning_logged:
                        logger.warning(
                            "documents.file_hash not found in Supabase schema; "
                            "upload will continue without file hashing until migration is applied.",
                            extra=log_extra(job_id=doc_id),
                        )
                        DocumentCrudService._file_hash_warning_logged = True
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

    async def update_document(
        self, doc_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        sb = get_supabase_client()
        doc_id = str(doc_id)
        if sb is None:
            logger.error("update_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_update():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("documents")
                .update(updates)
                .eq("id", str(doc_id))
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_update)
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error("update_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to update document: {e}") from e
        except Exception as e:
            logger.error("update_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to update document: {e}") from e

    async def delete_document(
        self, document_id: str, user_id: Optional[str] = None
    ) -> bool:
        sb = get_supabase_client()
        doc_id = str(document_id)
        owner_id = str(user_id) if user_id else None

        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        doc = await self.get_document(doc_id, owner_id)
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
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            client.table("processing_status").delete().eq("document_id", doc_id).execute()
            client.table("document_results").delete().eq("document_id", doc_id).execute()
            client.table("document_versions").delete().eq("document_id", doc_id).execute()

        try:
            await asyncio.to_thread(run_cleanup)
        except Exception as exc:
            logger.warning("Auxiliary cleanup failed for document %s: %s", doc_id, exc, extra=log_extra(job_id=doc_id))

        def run_delete():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
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
            logger.error("delete_document(%s, user=%s) failed: %s", doc_id, owner_id, exc, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to delete document: {exc}") from exc

    async def update_output_hash(self, doc_id: str, output_hash: str) -> bool:
        if not output_hash:
            return False
        if DocumentCrudService._supports_output_hash is False:
            return False

        sb = get_supabase_client()
        if sb is None:
            return False

        def run_update():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return client.table("documents").update({"output_hash": output_hash}).eq("id", str(doc_id)).execute()

        try:
            await asyncio.to_thread(run_update)
            DocumentCrudService._supports_output_hash = True
            return True
        except Exception as exc:
            err = str(exc)
            missing_output_hash = (
                "output_hash" in err
                and ("schema cache" in err or "column" in err or "PGRST204" in err)
            )
            if missing_output_hash:
                DocumentCrudService._supports_output_hash = False
                if not DocumentCrudService._file_hash_warning_logged:
                    logger.warning(
                        "documents.output_hash not found in Supabase schema; "
                        "download integrity checks will be best-effort until migration is applied.",
                        extra=log_extra(job_id=doc_id),
                    )
                    DocumentCrudService._output_hash_warning_logged = True
                return False
            logger.error("update_output_hash(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=doc_id))
            return False

    async def mark_document_failed(self, doc_id: str, error_message: str) -> None:
        sb = get_supabase_client()
        doc_id = str(doc_id)
        if sb is None:
            logger.error("mark_document_failed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        def run_update():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return client.table("documents").update({
                "status": "FAILED",
                "error_message": error_message,
                "progress": 0,
            }).eq("id", str(doc_id)).execute()

        try:
            await asyncio.to_thread(run_update)
        except Exception as exc:
            logger.error("mark_document_failed(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=doc_id))

    async def mark_document_completed(
        self,
        doc_id: str,
        output_path: str,
        raw_text: Optional[str] = None,
    ) -> None:
        sb = get_supabase_client()
        doc_id = str(doc_id)
        if sb is None:
            logger.error("mark_document_completed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        def run_update():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            updates: Dict[str, Any] = {
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

    # ── Document Results ─────────────────────────────────────────────────────

    async def get_document_result(self, doc_id: str) -> Optional[Dict[str, Any]]:
        doc_id = str(doc_id)
        if not self._should_query_document_tables(doc_id, "get_document_result"):
            return None
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("document_results")
                .select("*")
                .eq("document_id", str(doc_id))
                .maybe_single()
                .execute()
            )

        try:
            result = await self._execute_with_transient_retry(
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

    async def upsert_document_result(
        self,
        doc_id: str,
        structured_data: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None,
    ) -> None:
        sb = get_supabase_client()
        doc_id = str(doc_id)
        if sb is None:
            logger.error("upsert_document_result: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_upsert():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            payload: Dict[str, Any] = {"document_id": str(doc_id)}
            if structured_data is not None:
                payload["structured_data"] = structured_data
            if validation_results is not None:
                payload["validation_results"] = validation_results
            return client.table("document_results").upsert(
                payload, on_conflict="document_id"
            ).execute()

        try:
            await asyncio.to_thread(run_upsert)
        except APIError as e:
            logger.error("upsert_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert document result: {e}") from e
        except Exception as e:
            logger.error("upsert_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert document result: {e}") from e

    # ── Processing Status ────────────────────────────────────────────────────

    async def get_processing_statuses(self, doc_id: str) -> List[Dict[str, Any]]:
        doc_id = str(doc_id)
        if not self._should_query_document_tables(doc_id, "get_processing_statuses"):
            return []
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("processing_status")
                .select("*")
                .eq("document_id", str(doc_id))
                .execute()
            )

        try:
            result = await self._execute_with_transient_retry(
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

    async def upsert_processing_status(
        self,
        doc_id: str,
        phase: str,
        status: str,
        progress_percentage: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        sb = get_supabase_client()
        doc_id = str(doc_id)
        if sb is None:
            logger.error("upsert_processing_status: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_upsert():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            payload: Dict[str, Any] = {
                "document_id": str(doc_id),
                "phase": phase,
                "status": status,
            }
            if progress_percentage is not None:
                payload["progress_percentage"] = progress_percentage
            if message is not None:
                payload["message"] = message
            return client.table("processing_status").upsert(
                payload, on_conflict="document_id,phase"
            ).execute()

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
