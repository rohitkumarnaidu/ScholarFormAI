# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document Service — enterprise service and unified facade.

Provides full backward compatibility for both class-level and instance-level
invocations across tests and API routers, while integrating cleanly with
decomposed services (DocumentCrudService, DocumentPipelineService, DocumentShareService).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import Request
from postgrest import APIError

from app.db.supabase_client import get_supabase_client
from app.exceptions import (
    DatabaseUnavailableError,
    DocumentNotFoundError,
)
from app.schemas.user import User
from app.services.document_crud_service import DocumentCrudService
from app.services.document_share_service import DocumentShareService
from app.utils.logging_context import log_extra

logger = logging.getLogger(__name__)


class DocumentService:
    """Enterprise document service with complete backward compatibility."""

    _instance: DocumentService | None = None
    _supports_file_hash: bool | None = None
    _file_hash_warning_logged: bool = False
    _supports_output_hash: bool | None = None
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

    def __init__(
        self,
        crud: DocumentCrudService | None = None,
        pipeline: Any | None = None,
        share: DocumentShareService | None = None,
    ) -> None:
        self._crud = crud or DocumentCrudService()
        if pipeline is None:
            from app.services.document_pipeline_service import DocumentPipelineService

            self._pipeline = DocumentPipelineService(crud=self._crud)
        else:
            self._pipeline = pipeline
        self._share = share or DocumentShareService()

    @classmethod
    def _get_instance(cls) -> DocumentService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Shared static helpers ────────────────────────────────────────────────

    @staticmethod
    def _is_transient_supabase_error(exc: Exception) -> bool:
        exc_name = type(exc).__name__.lower()
        if exc_name in {"remoteprotocolerror", "connecterror", "readtimeout", "writetimeout"}:
            return True
        message = str(exc).lower()
        return any(marker in message for marker in DocumentService._TRANSIENT_ERROR_MARKERS)

    @classmethod
    async def _execute_with_transient_retry(
        cls,
        operation_name: str,
        operation,
        *,
        job_id: str | None = None,
        max_attempts: int = 3,
    ):
        attempt = 0
        while True:
            try:
                return await asyncio.to_thread(operation)
            except Exception as exc:
                attempt += 1
                should_retry = cls._is_transient_supabase_error(exc) and attempt < max_attempts
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

    @classmethod
    def _should_query_document_tables(cls, doc_id: str, operation_name: str) -> bool:
        if cls._is_valid_uuid(doc_id):
            return True
        logger.info(
            "%s skipped for non-UUID document id: %s",
            operation_name,
            doc_id,
            extra=log_extra(job_id=doc_id),
        )
        return False

    # ── Signed URL helpers ───────────────────────────────────────────────────

    @staticmethod
    def generate_signed_download_url(
        *,
        file_url: str,
        file_path: str,
        secret: str,
        expires_in_seconds: int = 3600,
        download_format: str = "docx",
    ) -> dict[str, Any]:
        if not secret:
            raise ValueError("SIGNED_URL_SECRET is required")
        expires = int(time.time()) + int(expires_in_seconds)
        signature = hmac.new(
            secret.encode("utf-8"),
            DocumentService._build_signed_download_scope(
                file_path=file_path,
                download_format=download_format,
                expires=expires,
            ).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        parsed = urlparse(file_url)
        query = dict(parse_qsl(parsed.query))
        query.update({"token": signature, "expires": str(expires)})
        signed_url = urlunparse(parsed._replace(query=urlencode(query)))
        return {"url": signed_url, "expires": expires}

    @staticmethod
    def verify_signed_download(
        *,
        file_path: str,
        token: str,
        expires: int,
        secret: str,
        download_format: str = "docx",
    ) -> bool:
        if not secret or not token or not expires:
            return False
        try:
            expires_int = int(expires)
        except (TypeError, ValueError):
            return False
        if expires_int < int(time.time()):
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            DocumentService._build_signed_download_scope(
                file_path=file_path,
                download_format=download_format,
                expires=expires_int,
            ).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, token)

    @staticmethod
    def _build_signed_download_scope(
        *,
        file_path: str,
        download_format: str,
        expires: int,
    ) -> str:
        normalized_format = str(download_format or "docx").strip().lower()
        return f"{file_path}|{normalized_format}|{int(expires)}"

    # ── CRUD Operations ──────────────────────────────────────────────────────

    @classmethod
    async def get_document(cls, doc_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        if user_id:
            user_id = str(user_id)
        if not cls._should_query_document_tables(doc_id, "get_document"):
            return None
        sb = get_supabase_client()
        if sb is None:
            logger.error("get_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            query = client.table("documents").select("*").eq("id", str(doc_id))
            if user_id:
                query = query.eq("user_id", str(user_id))
            return query.maybe_single().execute()

        try:
            result = await cls._execute_with_transient_retry("get_document", run_query, job_id=doc_id)
            if hasattr(result, "data"):
                return result.data
            if isinstance(result, dict) and "data" in result:
                return result["data"]
            return result
        except APIError as e:
            logger.error("get_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document: {e}") from e
        except Exception as e:
            logger.error("get_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document: {e}") from e

    @classmethod
    async def list_documents(
        cls,
        user_id: str,
        status: str | None = None,
        template: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        user_id = str(user_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("list_documents: Supabase client not available.", extra=log_extra())
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
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
            if result is None:
                return []
            data = (
                result.data if hasattr(result, "data") else (result.get("data") if isinstance(result, dict) else result)
            )
            return data or []
        except APIError as e:
            logger.error("list_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to list documents: {e}") from e
        except Exception as e:
            logger.error("list_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to list documents: {e}") from e

    @classmethod
    async def count_documents(
        cls,
        user_id: str,
        status: str | None = None,
        template: str | None = None,
    ) -> int:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            query = client.table("documents").select("id", count="exact").eq("user_id", str(user_id))
            if status:
                query = query.eq("status", status.upper())
            if template:
                query = query.eq("template", template.upper())
            return query.execute()

        try:
            result = await asyncio.to_thread(run_query)
            count = getattr(result, "count", None)
            if count is None and isinstance(result, dict):
                count = result.get("count")
            return count or 0
        except APIError as e:
            logger.error("count_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count documents: {e}") from e
        except Exception as e:
            logger.error("count_documents(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count documents: {e}") from e

    @classmethod
    async def count_uploads_today(cls, user_id: str) -> int:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_iso = today_start.isoformat()

        def run_query():
            client = get_supabase_client()
            return (
                client.table("documents")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .gte("created_at", today_iso)
                .lt("created_at", datetime.now(UTC).isoformat())
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_query)
            count = getattr(result, "count", None)
            if count is None and isinstance(result, dict):
                count = result.get("count")
            return count or 0
        except APIError as e:
            logger.error("count_uploads_today(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count daily uploads: {e}") from e
        except Exception as e:
            logger.error("count_uploads_today(user=%s) failed: %s", user_id, e, extra=log_extra())
            raise DatabaseUnavailableError(f"Failed to count daily uploads: {e}") from e

    @classmethod
    async def create_document(
        cls,
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
        sb = get_supabase_client()
        if sb is None:
            logger.error("create_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        payload: dict[str, Any] = {
            "id": doc_id,
            "filename": filename,
            "template": (template or "ieee").upper(),
            "status": "PROCESSING",
            "progress": 0,
            "current_stage": "INITIALIZING",
        }
        if user_id:
            payload["user_id"] = str(user_id)
        if original_file_path:
            payload["original_file_path"] = original_file_path
        if formatting_options:
            payload["formatting_options"] = formatting_options

        supports_file_hash = cls._supports_file_hash is not False
        if file_hash and supports_file_hash:
            payload["file_hash"] = file_hash

        def run_insert(data):
            client = get_supabase_client()
            return client.table("documents").insert(data).execute()

        try:
            result = await asyncio.to_thread(run_insert, payload)
        except Exception as exc:
            message = str(exc).lower()
            missing_column = "file_hash" in message and (
                "not exist" in message or "pgrst204" in message or "schema" in message
            )
            if file_hash and supports_file_hash and missing_column:
                if not cls._file_hash_warning_logged:
                    logger.warning(
                        "documents table does not support file_hash column; proceeding without it: %s",
                        exc,
                        extra=log_extra(job_id=doc_id),
                    )
                    cls._file_hash_warning_logged = True
                cls._supports_file_hash = False
                payload.pop("file_hash", None)
                try:
                    result = await asyncio.to_thread(run_insert, payload)
                except Exception as retry_exc:
                    logger.error(
                        "create_document(%s) failed on retry: %s", doc_id, retry_exc, extra=log_extra(job_id=doc_id)
                    )
                    raise DatabaseUnavailableError(f"Failed to create document: {retry_exc}") from retry_exc
            else:
                logger.error("create_document(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=doc_id))
                raise DatabaseUnavailableError(f"Failed to create document: {exc}") from exc

        data = result.data if hasattr(result, "data") else (result.get("data") if isinstance(result, dict) else result)
        if data and len(data) > 0:
            return data[0]
        return None

    @classmethod
    async def update_document(cls, doc_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("update_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_update():
            client = get_supabase_client()
            return client.table("documents").update(updates).eq("id", str(doc_id)).execute()

        try:
            result = await asyncio.to_thread(run_update)
            data = (
                result.data if hasattr(result, "data") else (result.get("data") if isinstance(result, dict) else result)
            )
            if data and len(data) > 0:
                return data[0]
            return None
        except APIError as e:
            logger.error("update_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to update document: {e}") from e
        except Exception as e:
            logger.error("update_document(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to update document: {e}") from e

    @classmethod
    async def delete_document(cls, document_id: str, user_id: str | None = None) -> bool:
        doc_id = str(document_id)
        doc = await cls.get_document(doc_id, user_id)
        if not doc:
            raise DocumentNotFoundError(f"Document {doc_id} not found")

        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        for path_key in ("output_path", "original_file_path"):
            path = doc.get(path_key)
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError as exc:
                    logger.warning("Could not remove file %s: %s", path, exc, extra=log_extra(job_id=doc_id))

        query = sb.table("documents").delete().eq("id", str(doc_id))
        if user_id:
            query = query.eq("user_id", str(user_id))
        result = query.execute()

        data = result.data if hasattr(result, "data") else (result.get("data") if isinstance(result, dict) else result)
        if not data:
            raise DatabaseUnavailableError(f"Failed to delete document {doc_id}")
        return True

    @classmethod
    async def update_output_hash(cls, doc_id: str, output_hash: str) -> bool:
        if not output_hash:
            return False
        if cls._supports_output_hash is False:
            return False

        sb = get_supabase_client()
        if sb is None:
            return False

        def run_update():
            client = get_supabase_client()
            return client.table("documents").update({"output_hash": output_hash}).eq("id", str(doc_id)).execute()

        try:
            await asyncio.to_thread(run_update)
            cls._supports_output_hash = True
            return True
        except Exception as exc:
            message = str(exc).lower()
            missing_column = "output_hash" in message and (
                "not exist" in message or "pgrst204" in message or "schema" in message
            )
            if missing_column:
                if not cls._output_hash_warning_logged:
                    logger.warning(
                        "documents table does not support output_hash column: %s",
                        exc,
                        extra=log_extra(job_id=str(doc_id)),
                    )
                    cls._output_hash_warning_logged = True
                cls._supports_output_hash = False
            else:
                logger.error("update_output_hash(%s) failed: %s", doc_id, exc, extra=log_extra(job_id=str(doc_id)))
            return False

    @classmethod
    async def mark_document_failed(cls, doc_id: str, error_message: str) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("mark_document_failed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        def run_update():
            client = get_supabase_client()
            return (
                client.table("documents")
                .update(
                    {
                        "status": "FAILED",
                        "error_message": error_message,
                        "completed_at": datetime.now(UTC).isoformat(),
                    }
                )
                .eq("id", str(doc_id))
                .execute()
            )

        try:
            await asyncio.to_thread(run_update)
        except Exception as e:
            logger.error("mark_document_failed(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))

    @classmethod
    async def mark_document_completed(
        cls,
        doc_id: str,
        output_path: str,
        raw_text: str | None = None,
    ) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("mark_document_completed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        updates: dict[str, Any] = {
            "status": "COMPLETED",
            "progress": 100,
            "current_stage": "COMPLETE",
            "output_path": output_path,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        if raw_text is not None:
            updates["raw_text"] = raw_text

        def run_update():
            client = get_supabase_client()
            return client.table("documents").update(updates).eq("id", str(doc_id)).execute()

        try:
            await asyncio.to_thread(run_update)
        except Exception as e:
            logger.error("mark_document_completed(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))

    @classmethod
    async def get_document_result(cls, doc_id: str) -> dict[str, Any] | None:
        doc_id = str(doc_id)
        if not cls._should_query_document_tables(doc_id, "get_document_result"):
            return None
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            return client.table("document_results").select("*").eq("document_id", str(doc_id)).maybe_single().execute()

        try:
            result = await cls._execute_with_transient_retry("get_document_result", run_query, job_id=doc_id)
            if result is None:
                return None
            data = getattr(result, "data", None)
            if data is None and isinstance(result, dict):
                data = result.get("data")
            return data
        except APIError as e:
            logger.error("get_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document result: {e}") from e
        except Exception as e:
            logger.error("get_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get document result: {e}") from e

    @classmethod
    async def upsert_document_result(
        cls,
        doc_id: str,
        structured_data: dict[str, Any] | None = None,
        validation_results: dict[str, Any] | None = None,
    ) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("upsert_document_result: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        payload: dict[str, Any] = {"document_id": doc_id}
        if structured_data is not None:
            payload["structured_data"] = structured_data
        if validation_results is not None:
            payload["validation_results"] = validation_results

        def run_upsert():
            client = get_supabase_client()
            return client.table("document_results").upsert(payload).execute()

        try:
            await asyncio.to_thread(run_upsert)
        except APIError as e:
            logger.error("upsert_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert document result: {e}") from e
        except Exception as e:
            logger.error("upsert_document_result(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert document result: {e}") from e

    @classmethod
    async def get_processing_statuses(cls, doc_id: str) -> list[dict[str, Any]]:
        doc_id = str(doc_id)
        if not cls._should_query_document_tables(doc_id, "get_processing_statuses"):
            return []
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            return (
                client.table("processing_status")
                .select("*")
                .eq("document_id", str(doc_id))
                .order("created_at", desc=False)
                .execute()
            )

        try:
            result = await cls._execute_with_transient_retry("get_processing_statuses", run_query, job_id=doc_id)
            if result is None:
                return []
            data = getattr(result, "data", None)
            if data is None and isinstance(result, dict):
                data = result.get("data")
            return data or []
        except APIError as e:
            logger.error("get_processing_statuses(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get processing statuses: {e}") from e
        except Exception as e:
            logger.error("get_processing_statuses(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to get processing statuses: {e}") from e

    @classmethod
    async def upsert_processing_status(
        cls,
        doc_id: str,
        phase: str,
        status: str,
        progress_percentage: int | None = None,
        message: str | None = None,
    ) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("upsert_processing_status: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        payload: dict[str, Any] = {
            "document_id": doc_id,
            "phase": phase,
            "status": status,
        }
        if progress_percentage is not None:
            payload["progress_percentage"] = progress_percentage
        if message is not None:
            payload["message"] = message

        def run_upsert():
            client = get_supabase_client()
            return client.table("processing_status").upsert(payload).execute()

        try:
            await asyncio.to_thread(run_upsert)
        except APIError as e:
            logger.error("upsert_processing_status(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert processing status: {e}") from e
        except Exception as e:
            logger.error("upsert_processing_status(%s) failed: %s", doc_id, e, extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError(f"Failed to upsert processing status: {e}") from e

    # ── Advanced Operations (Pagination, Batch, Export) ──────────────────────

    @classmethod
    async def list_documents_paginated(
        cls,
        current_user: User,
        request: Request,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
        template: str | None = None,
        sort_by: str = "created_at",
        sort_direction: str = "desc",
    ) -> dict[str, Any]:
        return await cls._get_instance()._crud.list_documents_paginated(
            current_user, request, page, page_size, search, status, template, sort_by, sort_direction
        )

    @classmethod
    async def delete_document_with_cleanup(
        cls,
        document_id: str,
        user_id: str | None = None,
    ) -> bool:
        return await cls._get_instance()._crud.delete_document_with_cleanup(document_id, user_id)

    @classmethod
    async def export_documents_analytics(
        cls,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        return await cls._get_instance()._crud.export_documents_analytics(user_id, start_date, end_date)

    @classmethod
    async def batch_archive_documents(
        cls,
        user_id: str,
        document_ids: list[str],
    ) -> dict[str, Any]:
        return await cls._get_instance()._crud.batch_archive_documents(user_id, document_ids)

    @classmethod
    async def batch_restore_documents(
        cls,
        user_id: str,
        document_ids: list[str],
    ) -> dict[str, Any]:
        return await cls._get_instance()._crud.batch_restore_documents(user_id, document_ids)

    @classmethod
    async def export_user_data(
        cls,
        user_id: str,
    ) -> dict[str, Any]:
        return await cls._get_instance()._crud.export_user_data(user_id)

    # ── Pipeline delegation → DocumentPipelineService ────────────────────────

    @classmethod
    async def start_processing(cls, doc_id: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        return await cls._get_instance()._pipeline.start_processing(doc_id, options)

    @classmethod
    async def get_processing_status(cls, doc_id: str) -> list[dict[str, Any]]:
        return await cls._get_instance()._pipeline.get_processing_status(doc_id)

    @classmethod
    async def cancel_processing(cls, doc_id: str) -> dict[str, Any]:
        return await cls._get_instance()._pipeline.cancel_processing(doc_id)

    @classmethod
    async def get_result(cls, doc_id: str) -> dict[str, Any] | None:
        return await cls._get_instance()._pipeline.get_result(doc_id)

    # ── Share delegation → DocumentShareService ───────────────────────────────

    @classmethod
    async def share_document(
        cls,
        document_id: str,
        shared_with_user_id: str,
        permission: str,
        shared_by_user_id: str,
    ) -> dict[str, Any]:
        return await cls._get_instance()._share.share_document(
            document_id,
            shared_with_user_id,
            permission,
            shared_by_user_id,
        )

    @classmethod
    async def get_shared_documents(cls, user_id: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        return await cls._get_instance()._share.get_shared_documents(user_id, limit, offset)

    @classmethod
    async def remove_sharing(cls, document_id: str, shared_with_user_id: str) -> bool:
        return await cls._get_instance()._share.remove_sharing(document_id, shared_with_user_id)

    @classmethod
    async def check_document_access(cls, document_id: str, user_id: str) -> bool:
        return await cls._get_instance()._share.check_document_access(document_id, user_id)

    @classmethod
    async def unshare_document(cls, document_id: str, user_id: str) -> bool:
        return await cls._get_instance()._share.unshare_document(document_id, user_id)

    @classmethod
    async def get_shared_users(cls, document_id: str) -> list[dict[str, Any]]:
        return await cls._get_instance()._share.get_shared_users(document_id)

    @classmethod
    async def check_permission(cls, document_id: str, user_id: str) -> bool:
        return await cls._get_instance()._share.check_permission(document_id, user_id)
