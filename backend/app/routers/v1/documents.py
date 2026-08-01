# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    Request,
    UploadFile,
)

from app.config.settings import settings
from app.routers.v1 import documents_impl
from app.utils.logging_context import bind_request_context
from app.schemas.user import User
from app.utils.dependencies import get_current_user, get_optional_user

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.post("/upload/chunked")
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
    line_spacing: Optional[float] = Form(None),
    page_size: str = Form("Letter"),
    fast_mode: bool = Form(False),
    current_user: User = Depends(get_current_user),
):
    async def operation():
        return await documents_impl.upload_document_chunked(
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

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_UPLOAD_REQUEST",
            413: "DOCUMENT_TOO_LARGE",
            422: "DOCUMENT_VALIDATION_FAILED",
            429: "UPLOAD_LIMIT_REACHED",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="chunked document upload",
    )


@router.get("")
async def list_documents(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status (PROCESSING, COMPLETED, FAILED)"),
    template: Optional[str] = Query(None, description="Filter by template (IEEE, Springer, APA)"),
    start_date: Optional[datetime] = Query(None, description="Filter by created_at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter by created_at <= end_date"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.list_documents(
            status=status,
            template=template,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            current_user=current_user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="document list",
    )


@router.post("/upload")
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
    line_spacing: Optional[float] = Form(None),
    page_size: str = Form("Letter"),
    fast_mode: bool = Form(False),
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.upload_document(
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

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_UPLOAD_REQUEST",
            413: "DOCUMENT_TOO_LARGE",
            422: "DOCUMENT_VALIDATION_FAILED",
            429: "UPLOAD_LIMIT_REACHED",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="document upload",
    )


@router.get("/{jobId}/status")
async def get_status(
    request: Request,
    jobId: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.get_status(job_id=jobId, current_user=current_user)

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "DOCUMENT_ACCESS_DENIED",
            404: "DOCUMENT_NOT_FOUND",
        },
        logger=logger,
        operation_name="document status",
    )


@router.get("/{jobId}/summary")
async def get_document_summary(
    request: Request,
    jobId: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.get_document_summary(job_id=jobId, current_user=current_user)

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "DOCUMENT_ACCESS_DENIED",
            404: "DOCUMENT_NOT_FOUND",
        },
        logger=logger,
        operation_name="document summary",
    )


@router.post("/{jobId}/edit")
async def edit_document(
    request: Request,
    jobId: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.edit_document(
            request=request,
            job_id=jobId,
            data=data,
            background_tasks=background_tasks,
            current_user=current_user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_EDIT_REQUEST",
            403: "DOCUMENT_ACCESS_DENIED",
            404: "DOCUMENT_NOT_FOUND",
        },
        logger=logger,
        operation_name="document edit",
    )


@router.get("/{jobId}/preview")
async def get_preview(
    request: Request,
    jobId: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.get_preview(job_id=jobId, current_user=current_user)

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "DOCUMENT_ACCESS_DENIED",
            404: "DOCUMENT_NOT_FOUND",
        },
        logger=logger,
        operation_name="document preview",
    )


@router.get("/{jobId}/compare")
async def get_comparison_data(
    request: Request,
    jobId: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.get_comparison_data(job_id=jobId, current_user=current_user)

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "DOCUMENT_NOT_READY",
            403: "DOCUMENT_ACCESS_DENIED",
            404: "DOCUMENT_NOT_FOUND",
        },
        logger=logger,
        operation_name="document comparison",
    )


@router.get("/{jobId}/download")
async def download_document(
    request: Request,
    jobId: str,
    format: str = Query("docx"),
    token: Optional[str] = Query(None),
    expires: Optional[int] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
):
    async def operation():
        return await documents_impl.download_document(
            request=request,
            job_id=jobId,
            format=(format or "").strip().lower(),
            token=token,
            expires=expires,
            current_user=current_user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_EXPORT_FORMAT",
            403: "DOCUMENT_ACCESS_DENIED",
            404: "DOCUMENT_NOT_FOUND",
        },
        logger=logger,
        operation_name="document download",
    )


@router.delete("/{jobId}")
async def delete_document(
    request: Request,
    jobId: str,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        return await documents_impl.delete_document(request=request, job_id=jobId, current_user=current_user)

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "DOCUMENT_ACCESS_DENIED",
            404: "DOCUMENT_NOT_FOUND",
        },
        logger=logger,
        operation_name="document delete",
    )


@router.post("/batch-upload")
async def batch_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    template: str = Form("none"),
    current_user: User = Depends(get_current_user),
):
    async def operation():
        return await documents_impl.batch_upload(
            request=request,
            background_tasks=background_tasks,
            files=files,
            template=template,
            current_user=current_user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_BATCH_UPLOAD",
            429: "UPLOAD_LIMIT_REACHED",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="batch upload",
    )
