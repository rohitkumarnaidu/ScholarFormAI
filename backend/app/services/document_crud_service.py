# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document CRUD service — database operations for the `documents`,
`document_results`, and `processing_status` tables.

Extracted from the fat `document_service.py` so the orchestration,
sharing, and CRUD concerns live in separate units. All public methods
are async-safe and delegate to the supabase-py client.

Internally delegates to proper Repository classes under
``app.db.repositories`` for maintainability.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional, List, Dict, Any

from app.db.supabase_client import get_supabase_client
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.document_result_repository import DocumentResultRepository
from app.db.repositories.processing_status_repository import ProcessingStatusRepository
from app.utils.logging_context import log_extra
from app.exceptions import (
    DatabaseUnavailableError,
    DocumentNotFoundError,
)

logger = logging.getLogger(__name__)


class DocumentCrudService:
    """
    CRUD + result/status persistence for documents.

    Internally delegates to ``DocumentRepository``, ``DocumentResultRepository``,
    and ``ProcessingStatusRepository``.

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

    def __init__(self) -> None:
        self._documents = DocumentRepository()
        self._results = DocumentResultRepository()
        self._statuses = ProcessingStatusRepository()

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

        return await self._documents.get(doc_id, user_id)

    async def list_documents(
        self,
        user_id: str,
        status: Optional[str] = None,
        template: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        user_id = str(user_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("list_documents: Supabase client not available.", extra=log_extra())
            raise DatabaseUnavailableError("Supabase client is not configured.")

        return await self._documents.list(user_id, status, template, limit, offset)

    async def count_documents(
        self,
        user_id: str,
        status: Optional[str] = None,
        template: Optional[str] = None,
    ) -> int:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        return await self._documents.count(user_id, status, template)

    async def count_uploads_today(self, user_id: str) -> int:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        return await self._documents.count_uploads_today(user_id)

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
        doc_id = str(doc_id)
        if user_id:
            user_id = str(user_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("create_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        # Sync class-level schema-probing state into the repository instance so
        # that repeated create calls within the same process honour the probe.
        self._documents._supports_file_hash = self._supports_file_hash
        self._documents._file_hash_warning_logged = self._file_hash_warning_logged

        result = await self._documents.create(
            doc_id, user_id, filename, template,
            original_file_path, formatting_options, file_hash,
        )

        # Reflect repository state back onto the service class.
        self._supports_file_hash = self._documents._supports_file_hash
        self._file_hash_warning_logged = self._documents._file_hash_warning_logged

        return result

    async def update_document(
        self, doc_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("update_document: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        return await self._documents.update(doc_id, updates)

    async def delete_document(
        self, document_id: str, user_id: Optional[str] = None
    ) -> bool:
        doc_id = str(document_id)
        owner_id = str(user_id) if user_id else None
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        return await self._documents.delete(document_id, user_id)

    async def update_output_hash(self, doc_id: str, output_hash: str) -> bool:
        if not output_hash:
            return False
        if DocumentCrudService._supports_output_hash is False:
            return False

        sb = get_supabase_client()
        if sb is None:
            return False

        # Sync class-level schema-probing state into the repository instance.
        self._documents._supports_output_hash = self._supports_output_hash
        self._documents._output_hash_warning_logged = self._output_hash_warning_logged

        result = await self._documents.update_output_hash(doc_id, output_hash)

        # Reflect repository state back onto the service class.
        self._supports_output_hash = self._documents._supports_output_hash
        self._output_hash_warning_logged = self._documents._output_hash_warning_logged

        return result

    async def mark_document_failed(self, doc_id: str, error_message: str) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("mark_document_failed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        await self._documents.mark_failed(doc_id, error_message)

    async def mark_document_completed(
        self,
        doc_id: str,
        output_path: str,
        raw_text: Optional[str] = None,
    ) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("mark_document_completed: Supabase client not available.", extra=log_extra(job_id=doc_id))
            return

        await self._documents.mark_completed(doc_id, output_path, raw_text)

    # ── Document Results ─────────────────────────────────────────────────────

    async def get_document_result(self, doc_id: str) -> Optional[Dict[str, Any]]:
        doc_id = str(doc_id)
        if not self._should_query_document_tables(doc_id, "get_document_result"):
            return None
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        return await self._results.get(doc_id)

    async def upsert_document_result(
        self,
        doc_id: str,
        structured_data: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None,
    ) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("upsert_document_result: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        await self._results.upsert(doc_id, structured_data, validation_results)

    # ── Processing Status ────────────────────────────────────────────────────

    async def get_processing_statuses(self, doc_id: str) -> List[Dict[str, Any]]:
        doc_id = str(doc_id)
        if not self._should_query_document_tables(doc_id, "get_processing_statuses"):
            return []
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        return await self._statuses.get_statuses(doc_id)

    async def upsert_processing_status(
        self,
        doc_id: str,
        phase: str,
        status: str,
        progress_percentage: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        doc_id = str(doc_id)
        sb = get_supabase_client()
        if sb is None:
            logger.error("upsert_processing_status: Supabase client not available.", extra=log_extra(job_id=doc_id))
            raise DatabaseUnavailableError("Supabase client is not configured.")

        await self._statuses.upsert(doc_id, phase, status, progress_percentage, message)
