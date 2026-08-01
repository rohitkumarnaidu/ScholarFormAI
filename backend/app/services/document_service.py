# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document Service — thin facade over the decomposed services.

All public method signatures are preserved for backward compatibility.
The actual implementation now lives in:

  - :class:`DocumentCrudService`      — CRUD + result/status persistence
  - :class:`DocumentPipelineService`  — orchestration / dispatch
  - :class:`DocumentShareService`     — sharing + permission checks
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.services.document_crud_service import DocumentCrudService
from app.services.document_share_service import DocumentShareService

logger = logging.getLogger(__name__)


class DocumentService:
    """Thin facade that delegates to the decomposed document services."""

    _instance: DocumentService | None = None

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

    # ── Static helpers (backward compat — also on DocumentCrudService) ─────

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        return DocumentCrudService._is_valid_uuid(value)

    @staticmethod
    def _should_query_document_tables(doc_id: str, operation_name: str) -> bool:
        return DocumentCrudService._should_query_document_tables(doc_id, operation_name)

    # ── Signed URL helpers (self-contained, kept on the facade) ────────────

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

    # ═══════════════════════════════════════════════════════════════════════
    # CRUD delegation → DocumentCrudService
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    async def get_document(cls, doc_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        return await cls._get_instance()._crud.get_document(doc_id, user_id)

    @classmethod
    async def list_documents(
        cls,
        user_id: str,
        status: str | None = None,
        template: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await cls._get_instance()._crud.list_documents(user_id, status, template, limit, offset)

    @classmethod
    async def count_documents(
        cls,
        user_id: str,
        status: str | None = None,
        template: str | None = None,
    ) -> int:
        return await cls._get_instance()._crud.count_documents(user_id, status, template)

    @classmethod
    async def count_uploads_today(cls, user_id: str) -> int:
        return await cls._get_instance()._crud.count_uploads_today(user_id)

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
        return await cls._get_instance()._crud.create_document(
            doc_id,
            user_id,
            filename,
            template,
            original_file_path,
            formatting_options,
            file_hash,
        )

    @classmethod
    async def update_document(cls, doc_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        return await cls._get_instance()._crud.update_document(doc_id, updates)

    @classmethod
    async def delete_document(cls, document_id: str, user_id: str | None = None) -> bool:
        return await cls._get_instance()._crud.delete_document(document_id, user_id)

    @classmethod
    async def update_output_hash(cls, doc_id: str, output_hash: str) -> bool:
        return await cls._get_instance()._crud.update_output_hash(doc_id, output_hash)

    @classmethod
    async def mark_document_failed(cls, doc_id: str, error_message: str) -> None:
        return await cls._get_instance()._crud.mark_document_failed(doc_id, error_message)

    @classmethod
    async def mark_document_completed(
        cls,
        doc_id: str,
        output_path: str,
        raw_text: str | None = None,
    ) -> None:
        return await cls._get_instance()._crud.mark_document_completed(doc_id, output_path, raw_text)

    @classmethod
    async def get_document_result(cls, doc_id: str) -> dict[str, Any] | None:
        return await cls._get_instance()._crud.get_document_result(doc_id)

    @classmethod
    async def upsert_document_result(
        cls,
        doc_id: str,
        structured_data: dict[str, Any] | None = None,
        validation_results: dict[str, Any] | None = None,
    ) -> None:
        return await cls._get_instance()._crud.upsert_document_result(doc_id, structured_data, validation_results)

    @classmethod
    async def get_processing_statuses(cls, doc_id: str) -> list[dict[str, Any]]:
        return await cls._get_instance()._crud.get_processing_statuses(doc_id)

    @classmethod
    async def upsert_processing_status(
        cls,
        doc_id: str,
        phase: str,
        status: str,
        progress_percentage: int | None = None,
        message: str | None = None,
    ) -> None:
        return await cls._get_instance()._crud.upsert_processing_status(
            doc_id,
            phase,
            status,
            progress_percentage,
            message,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Pipeline delegation → DocumentPipelineService
    # ═══════════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════════
    # Share delegation → DocumentShareService
    # ═══════════════════════════════════════════════════════════════════════

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
