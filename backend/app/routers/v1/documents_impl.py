# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
FastAPI route implementation module for document operations.

Refactored to delegate business logic, pipeline dispatching, CRUD operations,
and export compilation to dedicated application service classes:
- DocumentPipelineService
- DocumentCrudService
- DocumentExportService
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, Depends, File, Form, Query, Request, UploadFile

import app.services.document_pipeline_service as _ps
from app.config.settings import settings
from app.schemas.user import User
from app.services import (
    DocumentCrudService,
    DocumentExportService,
    DocumentPipelineService,
)
from app.utils.dependencies import get_current_user, get_optional_user

logger = logging.getLogger(__name__)

# Service instances for route delegation
_pipeline_service = DocumentPipelineService()
_crud_service = DocumentCrudService()
_export_service = DocumentExportService()

# Backward-compatible alias: tests and legacy code that reference DocumentService
# on this module will resolve to DocumentCrudService (which absorbed DocumentService).
DocumentService = DocumentCrudService

# Module-level re-exports for backward compatibility
UPLOAD_DIR = _ps.UPLOAD_DIR
ACCEPTED_EXTENSIONS = _ps.ACCEPTED_EXTENSIONS
TEXT_EXTENSIONS = _ps.TEXT_EXTENSIONS
MAGIC_BYTES_MAP = _ps.MAGIC_BYTES_MAP
_READY_FOR_EXPORT_STATUSES = _ps._READY_FOR_EXPORT_STATUSES
_SUPPORTED_EXPORT_FORMATS = _ps._SUPPORTED_EXPORT_FORMATS
MAX_DAILY_UPLOADS = _ps.MAX_DAILY_UPLOADS
_STATUS_CACHE_MISS = _ps._STATUS_CACHE_MISS

# Legacy re-exports: tests patch these symbols on documents_impl directly.
# Importing them here makes `patch("app.routers.v1.documents_impl.X")` work
# even though the actual logic now lives in the service layer.
from app.pipeline.orchestrator import PipelineOrchestrator  # noqa: E402
from app.services.audit_log_service import audit_log_service  # noqa: E402
from app.services.enhancement_manager import enhancement_manager  # noqa: E402
from app.utils.virus_scanner import virus_scanner  # noqa: E402

__all__ = [
    "DocumentService",
    "UPLOAD_DIR",
    "ACCEPTED_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "MAGIC_BYTES_MAP",
    "_READY_FOR_EXPORT_STATUSES",
    "_SUPPORTED_EXPORT_FORMATS",
    "MAX_DAILY_UPLOADS",
    "_STATUS_CACHE_MISS",
    "PipelineOrchestrator",
    "audit_log_service",
    "enhancement_manager",
    "virus_scanner",
]


# Helper functions delegating to service implementations while honouring local module patches (e.g. settings)
def _document_status_ttl_seconds() -> float:
    return _ps._document_status_ttl_seconds(settings_override=settings)


def _get_status_cache_lock() -> asyncio.Lock:
    return _ps._get_status_cache_lock()


def _status_cache_key(job_id: str, current_user: User | None) -> str:
    return _ps._status_cache_key(job_id, current_user)


def _clone_status_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return _ps._clone_status_payload(payload)


async def _get_cached_status_response(cache_key: str) -> Any:
    return await _ps._get_cached_status_response(cache_key, settings_override=settings)


async def _get_stale_status_response(
    cache_key: str, *, max_stale_seconds: float = _ps._MAX_STALE_STATUS_SECONDS
) -> Any:
    return await _ps._get_stale_status_response(
        cache_key, max_stale_seconds=max_stale_seconds, settings_override=settings
    )


async def _set_cached_status_response(cache_key: str, payload: dict[str, Any]) -> None:
    await _ps._set_cached_status_response(cache_key, payload, settings_override=settings)


def _reset_document_status_cache_for_tests() -> None:
    _ps._reset_document_status_cache_for_tests()


def _require_db() -> None:
    _ps._require_db()


def _compute_sha256(filepath: str) -> str:
    return DocumentExportService.compute_sha256(filepath)


def _enforce_daily_upload_quota(current_user: User | None) -> None:
    _ps._enforce_daily_upload_quota(current_user)


def _record_upload_ack_duration(started_at: float) -> None:
    _ps._record_upload_ack_duration(started_at)


def _normalize_provider_name(value: Any) -> str | None:
    return _ps._normalize_provider_name(value)


def _extract_quality_payload(result: dict[str, Any] | None) -> dict[str, Any]:
    return _ps._extract_quality_payload(result)


def _build_initial_status_payload(job_id: str) -> dict[str, Any]:
    return _ps._build_initial_status_payload(job_id)


async def _scan_uploaded_file(file_path: str) -> dict[str, str | bool]:
    return await _ps._scan_uploaded_file(file_path)


async def _validate_magic_bytes(
    file: UploadFile,
    *,
    content: bytes | None = None,
    file_ext: str | None = None,
) -> bytes:
    return await _ps._validate_magic_bytes(file, content=content, file_ext=file_ext)


# ── Route Handlers (Delegating to Application Services) ────────────────────────


async def upload_document_chunked(
    request: Request,
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file: UploadFile = File(...),
    template: str = Form(settings.DEFAULT_TEMPLATE),
    add_page_numbers: bool = Form(True),
    add_borders: bool = Form(False),
    add_cover_page: bool = Form(False),
    generate_toc: bool = Form(False),
    add_line_numbers: bool = Form(False),
    line_spacing: float | None = Form(None),
    page_size: str = Form("Letter"),
    fast_mode: bool = Form(False),
    current_user: User = Depends(get_current_user),
):
    """FEAT 42: Chunked file upload for large documents."""
    return await _pipeline_service.upload_document_chunked(
        request=request,
        background_tasks=background_tasks,
        file_id=file_id,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        file=file,
        template=template,
        add_page_numbers=add_page_numbers,
        add_borders=add_borders,
        add_cover_page=add_cover_page,
        generate_toc=generate_toc,
        add_line_numbers=add_line_numbers,
        line_spacing=line_spacing,
        page_size=page_size,
        fast_mode=fast_mode,
        current_user=current_user,
    )


async def list_documents(
    status: str | None = Query(None, description="Filter by status (PROCESSING, COMPLETED, FAILED)"),
    template: str | None = Query(None, description="Filter by template (IEEE, Springer, APA)"),
    start_date: datetime | None = Query(None, description="Filter by created_at >= start_date"),
    end_date: datetime | None = Query(None, description="Filter by created_at <= end_date"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User | None = Depends(get_optional_user),
):
    """List documents for the current user with optional filtering and pagination."""
    return await _crud_service.list_documents_paginated(
        current_user=current_user,
        status=status,
        template=template,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    template: str = Form(settings.DEFAULT_TEMPLATE),
    add_page_numbers: bool = Form(True),
    add_borders: bool = Form(False),
    add_cover_page: bool = Form(False),
    generate_toc: bool = Form(False),
    add_line_numbers: bool = Form(False),
    line_spacing: float | None = Form(None),
    page_size: str = Form("Letter"),
    fast_mode: bool = Form(False),
    current_user: User | None = Depends(get_optional_user),
):
    """Handle document upload and trigger async background processing."""
    return await _pipeline_service.upload_document(
        request=request,
        background_tasks=background_tasks,
        file=file,
        template=template,
        add_page_numbers=add_page_numbers,
        add_borders=add_borders,
        add_cover_page=add_cover_page,
        generate_toc=generate_toc,
        add_line_numbers=add_line_numbers,
        line_spacing=line_spacing,
        page_size=page_size,
        fast_mode=fast_mode,
        current_user=current_user,
    )


async def get_status(
    job_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get the detailed processing status of a document."""
    return await _pipeline_service.get_status(job_id=job_id, current_user=current_user)


async def get_document_summary(
    job_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Lightweight job summary for URL-based page hydration."""
    return await _pipeline_service.get_document_summary(job_id=job_id, current_user=current_user)


async def edit_document(
    request: Request,
    job_id: str,
    data: dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User | None = Depends(get_optional_user),
):
    """Handle user edits and trigger non-destructive re-formatting."""
    return await _pipeline_service.edit_document(
        request=request,
        job_id=job_id,
        data=data,
        background_tasks=background_tasks,
        current_user=current_user,
    )


async def get_preview(
    job_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get the structured preview data for a document."""
    return await _pipeline_service.get_preview(job_id=job_id, current_user=current_user)


async def get_comparison_data(
    job_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get data for side-by-side comparison with HTML diff."""
    return await _export_service.get_comparison_data(job_id=job_id, current_user=current_user)


async def download_document(
    request: Request,
    job_id: str,
    format: str = "docx",
    token: str | None = Query(None),
    expires: int | None = Query(None),
    current_user: User | None = Depends(get_optional_user),
):
    """Download the processed document in DOCX, PDF, or TeX format."""
    return await _export_service.download_document(
        request=request,
        job_id=job_id,
        format=format,
        token=token,
        expires=expires,
        current_user=current_user,
    )


async def delete_document(
    request: Request,
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its associated output files."""
    return await _crud_service.delete_document_with_cleanup(
        request=request,
        job_id=job_id,
        current_user=current_user,
    )


async def batch_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    template: str = Form("none"),
    current_user: User = Depends(get_current_user),
):
    """Upload multiple documents at once."""
    return await _pipeline_service.batch_upload(
        request=request,
        background_tasks=background_tasks,
        files=files,
        template=template,
        current_user=current_user,
    )
